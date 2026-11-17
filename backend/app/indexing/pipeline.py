from __future__ import annotations

import asyncio
import hashlib
import json
import time
import uuid
from datetime import datetime, timezone

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.github_app import get_github_client
from app.db.session import get_session_factory
from app.exceptions import QuotaExhaustedError
from app.indexing.chunker import CodeChunker
from app.indexing.classifier import FileClassifier
from app.indexing.embedder import EmbeddingClient
from app.indexing.languages import (
    JavaScriptAdapter,
    PythonAdapter,
    TextAdapter,
    TypeScriptAdapter,
)
from app.indexing.summarizer import Summarizer
from app.indexing.vector_store import VectorPoint, get_vector_store
from app.models import (
    CodeChunk,
    EmbeddingRecord,
    FileRecord,
    GitHubConnection,
    IndexJob,
    IndexJobStatus,
    ParseStatus,
    Repository,
    RepositoryVersion,
    SymbolKind,
    SymbolRecord,
)
from app.models.repository import RepositoryStatus
from app.retrieval.lexical import ChunkRecord, get_lexical_index, invalidate_index

logger = structlog.get_logger(__name__)

_LANG_ADAPTERS = {
    "python": PythonAdapter(),
    "javascript": JavaScriptAdapter(),
    "typescript": TypeScriptAdapter(),
    "text": TextAdapter(),
}
_CLASSIFIER = FileClassifier()
_CHUNKER = CodeChunker()

# Keep embed batches small for free-tier TPM (~30k tokens/min).
_EMBED_BATCH = 5
_EMBED_TEXT_CHARS = 2000
# Target ~25k TPM with headroom under the 30k free-tier limit.
_EMBED_TARGET_TPM = 25_000


class IndexingPipeline:
    """Full repository indexing pipeline driven by an IndexJob."""

    def __init__(self, job_id: str) -> None:
        self._job_id = job_id
        self._github = get_github_client()
        self._embedder = EmbeddingClient()
        self._vector_store = get_vector_store()
        self._summarizer = Summarizer()

    async def run(self) -> None:
        factory = get_session_factory()
        async with factory() as db:
            try:
                await self._execute(db)
            except QuotaExhaustedError as exc:
                await db.rollback()
                await self._update_job(db, IndexJobStatus.paused, error_category="quota_exhausted")
                logger.warning("Job paused — quota exhausted", job_id=self._job_id, error=str(exc))
            except Exception as exc:
                await db.rollback()
                await self._update_job(db, IndexJobStatus.failed, error_category="pipeline_error")
                logger.error("Job failed", job_id=self._job_id, error=str(exc), exc_info=True)

    async def _execute(self, db: AsyncSession) -> None:
        job = await self._load_job(db)
        if not job:
            logger.error("Job not found", job_id=self._job_id)
            return

        # Load related repository
        repo_result = await db.execute(
            select(Repository).where(Repository.id == job.repository_id)
        )
        repo = repo_result.scalar_one_or_none()
        if not repo:
            await self._update_job(db, IndexJobStatus.failed, error_category="repo_not_found")
            return

        checkpoint = self._parse_checkpoint(job)
        embed_offset = int(checkpoint.get("embed_offset") or 0)
        if (
            checkpoint.get("stage") == "embedding"
            and embed_offset > 0
            and job.version_id is not None
        ):
            await self._resume_embedding(db, job, repo, embed_offset)
            return

        # Mark as started
        job.status = IndexJobStatus.fetching
        job.started_at = datetime.now(timezone.utc)
        job.stage = "fetching"
        await db.commit()

        # Resolve the GitHub App installation for this repository's connection.
        # NOTE: repo.github_connection_id is a UUID FK into github_connections,
        # never a GitHub installation ID — it must never be cast with int().
        conn_result = await db.execute(
            select(GitHubConnection).where(GitHubConnection.id == repo.github_connection_id)
        )
        conn = conn_result.scalar_one_or_none()
        if not conn or not conn.github_app_installation_id:
            await self._update_job(db, IndexJobStatus.failed, error_category="no_installation")
            return

        try:
            install_id = int(conn.github_app_installation_id)
        except (TypeError, ValueError):
            await self._update_job(db, IndexJobStatus.failed, error_category="invalid_installation")
            return

        try:
            install_token = await self._github.get_installation_token(install_id)
        except httpx.HTTPStatusError as exc:
            logger.error(
                "GitHub installation token request failed",
                job_id=self._job_id,
                installation_id=install_id,
                status_code=exc.response.status_code,
            )
            category = (
                "invalid_installation" if exc.response.status_code == 404 else "github_auth_failed"
            )
            await self._update_job(db, IndexJobStatus.failed, error_category=category)
            return
        except httpx.RequestError as exc:
            logger.error(
                "GitHub installation token request errored",
                job_id=self._job_id,
                error=str(exc),
            )
            await self._update_job(db, IndexJobStatus.failed, error_category="github_auth_failed")
            return

        branch = repo.selected_branch

        # ── Stage 1: Fetch repository tree ────────────────────────────────────
        logger.info("Fetching tree", repo=f"{repo.owner}/{repo.name}", branch=branch)
        tree = await self._fetch_tree_with_retry(repo.owner, repo.name, branch, install_token)
        if tree is None:
            await self._update_job(db, IndexJobStatus.failed, error_category="github_fetch_failed")
            return

        # Only blobs (files), not trees (dirs)
        file_entries = [e for e in tree if e.get("type") == "blob"]

        # Create or update RepositoryVersion
        commit_sha = "unknown"
        version_result = await db.execute(
            select(RepositoryVersion)
            .where(RepositoryVersion.repository_id == repo.id)
            .where(RepositoryVersion.branch == branch)
        )
        version = version_result.scalar_one_or_none()
        if not version:
            version = RepositoryVersion(
                repository_id=repo.id,
                branch=branch,
                commit_sha=commit_sha,
                index_version=1,
            )
            db.add(version)
        else:
            version.index_version += 1

        job.version_id = version.id
        await db.commit()

        # ── Stage 2: Classify files ───────────────────────────────────────────
        job.status = IndexJobStatus.classifying
        job.stage = "classifying"
        job.files_total = len(file_entries)
        await db.commit()

        classified: list[tuple[dict, "FileClassification"]] = []  # type: ignore
        skipped = 0
        for entry in file_entries:
            path = entry.get("path", "")
            size = entry.get("size", 0) or 0
            fc = _CLASSIFIER.classify(path, size)
            if fc.should_index:
                classified.append((entry, fc))
            else:
                skipped += 1

        job.files_skipped = skipped
        await db.commit()
        logger.info("Classified files", indexed=len(classified), skipped=skipped)

        # ── Stage 3: Parse files and extract symbols ──────────────────────────
        job.status = IndexJobStatus.parsing
        job.stage = "parsing"
        await db.commit()

        file_records: list[FileRecord] = []
        symbols_by_file: dict[str, list] = {}
        content_by_file: dict[str, bytes] = {}
        failed = 0

        done_paths = set(checkpoint.get("done_paths", []))

        for entry, fc in classified:
            path = entry.get("path", "")
            if path in done_paths:
                continue

            try:
                content = await self._fetch_file_with_retry(
                    repo.owner, repo.name, path, branch, install_token
                )
                if content is None:
                    failed += 1
                    continue

                content_hash = hashlib.sha256(content).hexdigest()[:40]
                adapter = _LANG_ADAPTERS.get(fc.language or "text", _LANG_ADAPTERS["text"])
                symbols = adapter.extract_symbols(content, path)
                parse_status = ParseStatus[adapter.parse_status_on_success] if symbols or fc.language == "text" else ParseStatus.partial

                fr = FileRecord(
                    repository_id=repo.id,
                    version_id=version.id,
                    path=path,
                    language=fc.language,
                    size_bytes=len(content),
                    content_hash=content_hash,
                    parse_status=parse_status,
                )
                db.add(fr)
                file_records.append(fr)
                symbols_by_file[path] = symbols
                content_by_file[path] = content

            except Exception as exc:
                logger.warning("File parse failed", path=path, error=str(exc))
                failed += 1
                job.files_failed = failed

        await db.flush()  # get IDs for file_records

        # Save symbol records
        for fr in file_records:
            path = fr.path
            for sym in symbols_by_file.get(path, []):
                kind_map = {
                    "class": SymbolKind.cls,
                    "function": SymbolKind.function,
                    "method": SymbolKind.method,
                    "import": SymbolKind.import_,
                    "module": SymbolKind.module,
                }
                kind = kind_map.get(sym.kind, SymbolKind.function)
                sr = SymbolRecord(
                    file_id=fr.id,
                    symbol_kind=kind,
                    name=sym.name[:512],
                    qualified_name=sym.qualified_name[:1024],
                    line_start=sym.line_start,
                    line_end=sym.line_end,
                )
                db.add(sr)

        await db.commit()
        logger.info("Parsing complete", files=len(file_records), failed=failed)

        # ── Stage 4: Summarize ────────────────────────────────────────────────
        job.status = IndexJobStatus.summarizing
        job.stage = "summarizing"
        await db.commit()

        all_symbol_names = [
            sym.name
            for syms in symbols_by_file.values()
            for sym in syms
            if sym.kind in ("class", "function")
        ][:50]

        all_paths = [e.get("path", "") for e in file_entries[:200]]
        try:
            repo_summary = await self._summarizer.generate_repository_summary(
                repo_name=f"{repo.owner}/{repo.name}",
                file_tree=all_paths,
                top_symbols=all_symbol_names,
            )
            # Only persist a real summary — never store Gemini error text.
            if repo_summary:
                repo.description = repo_summary[:2000]
                await db.commit()
        except Exception as exc:
            logger.warning("Repo summary failed", error=str(exc))

        # Skip per-file module summaries during indexing. They are not persisted,
        # burn free-tier generate_content RPM (often 5/min), and can hang the job.

        # ── Stage 5: Embed and persist to Qdrant ─────────────────────────────
        chunk_buffer: list[tuple[CodeChunk, str, str, str]] = []  # chunk, text, path, language
        for fr in file_records:
            path = fr.path
            content = content_by_file.get(path)
            if not content:
                continue

            fc_lang = fr.language or "text"
            symbols = symbols_by_file.get(path, [])
            chunks = _CHUNKER.chunk_file(content, symbols, path, fc_lang)

            for chunk_data in chunks:
                cc = CodeChunk(
                    file_id=fr.id,
                    version_id=version.id,
                    content=chunk_data.text[:8000],
                    line_start=chunk_data.line_start,
                    line_end=chunk_data.line_end,
                    chunk_type=chunk_data.chunk_type,
                    symbol_name=chunk_data.symbol_name,
                )
                db.add(cc)
                chunk_buffer.append((cc, chunk_data.text, path, fc_lang))

        await db.flush()  # get chunk IDs

        processed = await self._embed_chunk_buffer(
            db,
            job=job,
            repo=repo,
            version=version,
            chunk_buffer=chunk_buffer,
            embed_offset=0,
        )

        # Rebuild BM25 index
        invalidate_index(str(repo.id))
        # Lazy load will rebuild on next search

        # ── Stage 6: Finalize ─────────────────────────────────────────────────
        await self._finalize_job(db, job, repo, version, branch, processed, failed)

    @staticmethod
    def _parse_checkpoint(job: IndexJob) -> dict:
        if not job.checkpoint:
            return {}
        try:
            data = json.loads(job.checkpoint)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _estimate_embed_tokens(texts: list[str]) -> int:
        return sum(max(1, len(text[:_EMBED_TEXT_CHARS]) // 4) for text in texts)

    async def _resume_embedding(
        self,
        db: AsyncSession,
        job: IndexJob,
        repo: Repository,
        embed_offset: int,
    ) -> None:
        """Resume embedding from checkpoint without re-inserting chunks."""
        version_result = await db.execute(
            select(RepositoryVersion).where(RepositoryVersion.id == job.version_id)
        )
        version = version_result.scalar_one_or_none()
        if not version:
            await self._update_job(db, IndexJobStatus.failed, error_category="version_not_found")
            return

        job.status = IndexJobStatus.embedding
        job.stage = "embedding"
        job.started_at = job.started_at or datetime.now(timezone.utc)
        job.error_category = None
        await db.commit()

        chunk_result = await db.execute(
            select(CodeChunk)
            .where(CodeChunk.version_id == version.id)
            .order_by(CodeChunk.created_at.asc(), CodeChunk.id.asc())
        )
        existing_chunks = list(chunk_result.scalars().all())
        if not existing_chunks:
            await self._update_job(db, IndexJobStatus.failed, error_category="no_chunks_to_resume")
            return

        file_ids = {cc.file_id for cc in existing_chunks}
        file_result = await db.execute(select(FileRecord).where(FileRecord.id.in_(file_ids)))
        files_by_id = {fr.id: fr for fr in file_result.scalars().all()}

        chunk_buffer: list[tuple[CodeChunk, str, str, str]] = []
        for cc in existing_chunks:
            fr = files_by_id.get(cc.file_id)
            path = fr.path if fr else ""
            language = (fr.language if fr else None) or "text"
            text = cc.content or ""
            chunk_buffer.append((cc, text, path, language))

        start = min(embed_offset, len(chunk_buffer))
        logger.info(
            "Resuming embedding from checkpoint",
            job_id=self._job_id,
            embed_offset=start,
            chunks=len(chunk_buffer),
        )
        processed = await self._embed_chunk_buffer(
            db,
            job=job,
            repo=repo,
            version=version,
            chunk_buffer=chunk_buffer,
            embed_offset=start,
        )
        invalidate_index(str(repo.id))
        await self._finalize_job(
            db,
            job,
            repo,
            version,
            repo.selected_branch,
            processed,
            job.files_failed or 0,
        )

    async def _embed_chunk_buffer(
        self,
        db: AsyncSession,
        *,
        job: IndexJob,
        repo: Repository,
        version: RepositoryVersion,
        chunk_buffer: list[tuple[CodeChunk, str, str, str]],
        embed_offset: int,
    ) -> int:
        from app.usage.quota_manager import get_quota_manager

        qm = get_quota_manager()
        if not await qm.check_service_available("gemini_embeddings"):
            job.checkpoint = json.dumps(
                {
                    "stage": "embedding",
                    "embed_offset": embed_offset,
                    "chunks_done": embed_offset,
                }
            )
            await db.commit()
            raise QuotaExhaustedError(
                "Embedding quota exhausted. Indexing paused.",
                service="embedding_provider",
            )

        job.status = IndexJobStatus.embedding
        job.stage = "embedding"
        job.files_total = len(chunk_buffer)
        job.files_processed = embed_offset
        await db.commit()

        await self._vector_store.ensure_collection()

        processed = embed_offset
        for i in range(embed_offset, len(chunk_buffer), _EMBED_BATCH):
            batch = chunk_buffer[i : i + _EMBED_BATCH]
            texts = [text for _, text, _, _ in batch]
            estimated_tokens = self._estimate_embed_tokens(texts)
            batch_started = time.monotonic()

            try:
                vectors = await self._embedder.embed_texts(texts)
            except QuotaExhaustedError:
                job.checkpoint = json.dumps(
                    {
                        "stage": "embedding",
                        "embed_offset": i,
                        "chunks_done": i,
                    }
                )
                await db.commit()
                raise

            vector_points: list[VectorPoint] = []
            for (cc, text, path, language), vector in zip(batch, vectors):
                point_id = str(cc.id)
                cc.qdrant_point_id = point_id
                cc.embedding_model = self._embedder._model

                er = EmbeddingRecord(
                    chunk_id=cc.id,
                    model_name=self._embedder._model,
                    vector_id=point_id,
                )
                db.add(er)

                vector_points.append(
                    VectorPoint(
                        point_id=point_id,
                        vector=vector,
                        repository_id=str(repo.id),
                        version_id=str(version.id),
                        file_id=str(cc.file_id),
                        file_path=path,
                        language=language or "text",
                        chunk_type=cc.chunk_type or "unknown",
                        symbol_name=cc.symbol_name,
                        line_start=cc.line_start or 0,
                        line_end=cc.line_end or 0,
                        text=text[:_EMBED_TEXT_CHARS],
                    )
                )

            await self._vector_store.upsert_chunks(vector_points)
            await db.commit()
            processed = i + len(batch)

            job.files_processed = processed
            job.checkpoint = json.dumps(
                {
                    "stage": "embedding",
                    "embed_offset": processed,
                    "chunks_done": processed,
                }
            )
            await db.commit()

            # Pace under free-tier TPM so 429s stay rare.
            batch_elapsed = time.monotonic() - batch_started
            pace_sleep = max(0.0, estimated_tokens / _EMBED_TARGET_TPM * 60.0 - batch_elapsed)
            if pace_sleep > 0:
                logger.info(
                    "Pacing embeddings for free-tier TPM",
                    sleep_seconds=round(pace_sleep, 2),
                    estimated_tokens=estimated_tokens,
                    chunks_done=processed,
                    chunks_total=len(chunk_buffer),
                )
                await asyncio.sleep(pace_sleep)

        return processed

    async def _finalize_job(
        self,
        db: AsyncSession,
        job: IndexJob,
        repo: Repository,
        version: RepositoryVersion,
        branch: str,
        processed: int,
        failed: int,
    ) -> None:
        job.status = IndexJobStatus.persisting
        job.stage = "persisting"
        await db.commit()

        version.commit_sha = branch  # Will be replaced with actual SHA in a follow-up
        final_status = IndexJobStatus.partial if failed > 0 else IndexJobStatus.completed
        job.status = final_status
        job.stage = None
        job.error_category = None
        job.checkpoint = None
        job.completed_at = datetime.now(timezone.utc)
        job.files_processed = processed
        repo.status = RepositoryStatus.indexed
        await db.commit()

        logger.info(
            "Indexing complete",
            job_id=self._job_id,
            status=final_status,
            chunks=processed,
            failed=failed,
        )

    async def _load_job(self, db: AsyncSession) -> IndexJob | None:
        result = await db.execute(
            select(IndexJob).where(IndexJob.id == uuid.UUID(self._job_id))
        )
        return result.scalar_one_or_none()

    async def _update_job(
        self, db: AsyncSession, status: IndexJobStatus, error_category: str | None = None
    ) -> None:
        result = await db.execute(
            select(IndexJob).where(IndexJob.id == uuid.UUID(self._job_id))
        )
        job = result.scalar_one_or_none()
        if job:
            job.status = status
            if error_category:
                job.error_category = error_category
            job.completed_at = datetime.now(timezone.utc)
            await self._sync_repository_status(db, job.repository_id, status)
            await db.commit()

    async def _sync_repository_status(
        self, db: AsyncSession, repository_id: uuid.UUID, job_status: IndexJobStatus
    ) -> None:
        """Keep Repository.status aligned with a job's terminal status.

        Without this, a repository stays stuck on "indexing" forever once its
        index job fails, is paused, or (via a separate code path) completes.
        """
        repo_result = await db.execute(
            select(Repository).where(Repository.id == repository_id)
        )
        repo = repo_result.scalar_one_or_none()
        if not repo:
            return
        if job_status in (IndexJobStatus.completed, IndexJobStatus.partial):
            repo.status = RepositoryStatus.indexed
        elif job_status == IndexJobStatus.failed:
            repo.status = RepositoryStatus.failed
        # paused: leave repo.status as indexing — the job is resumable.

    async def _fetch_tree_with_retry(
        self, owner: str, repo: str, ref: str, token: str
    ) -> list[dict] | None:
        for attempt in range(3):
            try:
                return await self._github.get_repo_tree(owner, repo, ref, token)
            except Exception as exc:
                if attempt == 2:
                    logger.error("Tree fetch failed after 3 attempts", error=str(exc))
                    return None
                await asyncio.sleep(2 ** attempt)
        return None

    async def _fetch_file_with_retry(
        self, owner: str, repo: str, path: str, ref: str, token: str
    ) -> bytes | None:
        for attempt in range(3):
            try:
                return await self._github.get_file_content(owner, repo, path, ref, token)
            except Exception as exc:
                if attempt == 2:
                    logger.warning("File fetch failed", path=path, error=str(exc))
                    return None
                await asyncio.sleep(1)
        return None
