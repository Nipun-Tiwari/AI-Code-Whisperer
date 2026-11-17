from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from google import genai
from google.genai import types as gtypes
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_session_factory
from app.models import AgentTask, Repository
from app.models.agent_task import TaskStatus
from app.models.repository import RepositoryStatus
from app.retrieval.service import EvidenceItem, RetrievalService

logger = structlog.get_logger(__name__)

_MAX_CONTEXT_CHARS = 6000


async def run_chat_task_background(task_id: uuid.UUID) -> None:
    """Run dedicated chat retrieve+answer in a fresh DB session."""
    factory = get_session_factory()
    try:
        async with factory() as db:
            await _run_chat_task(db, task_id)
    except Exception as exc:
        logger.error(
            "Background chat task failed",
            task_id=str(task_id),
            error=str(exc),
            exc_info=True,
        )


async def _run_chat_task(db: AsyncSession, task_id: uuid.UUID) -> None:
    result_obj = await db.execute(select(AgentTask).where(AgentTask.id == task_id))
    task = result_obj.scalar_one_or_none()
    if not task:
        logger.error("Chat task not found", task_id=str(task_id))
        return

    question = (task.plan or {}).get("user_request", "")
    repository_id = task.repository_id

    task.status = TaskStatus.running
    await db.commit()

    repo_result = await db.execute(select(Repository).where(Repository.id == repository_id))
    repo = repo_result.scalar_one_or_none()
    if not repo:
        task.status = TaskStatus.failed
        task.result = {
            "request_type": "repository_qa",
            "answer": "Repository not found.",
            "evidence": [],
            "repository_id": str(repository_id),
            "question": question,
            "errors": ["repository_not_found"],
        }
        task.completed_at = datetime.now(timezone.utc)
        await db.commit()
        return

    if repo.status not in (RepositoryStatus.indexed, RepositoryStatus.stale):
        task.status = TaskStatus.completed
        task.result = {
            "request_type": "repository_qa",
            "answer": (
                f"The repository '{repo.owner}/{repo.name}' has not been indexed yet. "
                "Please index it first."
            ),
            "evidence": [],
            "repository_id": str(repository_id),
            "question": question,
        }
        task.completed_at = datetime.now(timezone.utc)
        await db.commit()
        return

    try:
        retrieval = RetrievalService(db)
        evidence_items = await retrieval.search(
            query=question,
            repository_id=str(repository_id),
            top_k=8,
        )
        answer = await _generate_answer(
            question=question,
            repo_name=f"{repo.owner}/{repo.name}",
            evidence=evidence_items,
        )
        evidence_payload = [
            {
                "chunk_id": e.chunk_id,
                "file_path": e.file_path,
                "line_start": e.line_start,
                "line_end": e.line_end,
                "text": e.text,
                "symbol_name": e.symbol_name,
                "language": e.language,
                "chunk_type": e.chunk_type,
                "score": e.score,
                "retrieval_method": e.retrieval_method,
            }
            for e in evidence_items
        ]
        failed_answer = answer.startswith("Answer generation failed:")
        task.status = TaskStatus.partial if failed_answer else TaskStatus.completed
        task.result = {
            "request_type": "repository_qa",
            "answer": answer,
            "evidence": evidence_payload,
            "repository_id": str(repository_id),
            "question": question,
            "errors": [answer] if failed_answer else [],
        }
        task.completed_at = datetime.now(timezone.utc)
        await db.commit()
    except Exception as exc:
        logger.error("Chat task execution failed", task_id=str(task_id), error=str(exc))
        task.status = TaskStatus.failed
        task.result = {
            "request_type": "repository_qa",
            "answer": f"Chat query failed: {exc}",
            "evidence": [],
            "repository_id": str(repository_id),
            "question": question,
            "errors": [str(exc)],
        }
        task.completed_at = datetime.now(timezone.utc)
        await db.commit()


async def _generate_answer(
    question: str,
    repo_name: str,
    evidence: list[EvidenceItem],
) -> str:
    if not evidence:
        return (
            "No relevant code was found for your question. "
            "Make sure the repository is indexed and try rephrasing your question."
        )

    context_parts: list[str] = []
    total_chars = 0
    for item in evidence:
        snippet = (
            f"File: {item.file_path} (lines {item.line_start}–{item.line_end})\n"
            f"```\n{item.text}\n```"
        )
        if total_chars + len(snippet) > _MAX_CONTEXT_CHARS:
            break
        context_parts.append(snippet)
        total_chars += len(snippet)

    context = "\n\n".join(context_parts)
    prompt = f"""You are a code assistant helping a developer understand the repository: {repo_name}

The developer asks: {question}

Here is relevant code retrieved from the repository:

{context}

Answer the question based ONLY on the retrieved code above. If the code doesn't contain enough information to answer fully, say so clearly. Always reference specific file names and line numbers when relevant. Do not invent functionality not shown in the code."""

    try:
        settings = get_settings()
        client = genai.Client(api_key=settings.gemini_api_key)
        response = await client.aio.models.generate_content(
            model=settings.gemini_model_fast,
            contents=prompt,
            config=gtypes.GenerateContentConfig(
                max_output_tokens=1024,
                temperature=0.2,
            ),
        )
        return response.text or "Unable to generate an answer."
    except Exception as exc:
        return f"Answer generation failed: {exc}"
