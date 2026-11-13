from __future__ import annotations

from fastapi import APIRouter
from google import genai
from google.genai import types as gtypes
from sqlalchemy import select

from app.config import get_settings
from app.dependencies import DbDep, UserDep
from app.exceptions import NotFoundError
from app.models import Repository
from app.models.repository import RepositoryStatus
from app.retrieval.service import EvidenceItem, RetrievalService
from app.schemas.chat import ChatQueryRequest, ChatQueryResponse, EvidenceItemSchema

router = APIRouter(prefix="/chat", tags=["chat"])

_MAX_CONTEXT_CHARS = 6000  # ~1500 tokens for evidence context


@router.post("/query", response_model=ChatQueryResponse)
async def query_repository(
    body: ChatQueryRequest,
    current_user: UserDep,
    db: DbDep,
) -> ChatQueryResponse:
    """Answer a natural-language question about an indexed repository."""
    # Verify repo access
    repo_result = await db.execute(
        select(Repository).where(
            Repository.id == body.repository_id,
            Repository.user_id == current_user.id,
        )
    )
    repo = repo_result.scalar_one_or_none()
    if not repo:
        raise NotFoundError("Repository not found or not accessible.")

    if repo.status not in (RepositoryStatus.indexed, RepositoryStatus.stale):
        return ChatQueryResponse(
            answer=f"The repository '{repo.owner}/{repo.name}' has not been indexed yet. Please index it first.",
            evidence=[],
            repository_id=body.repository_id,
            question=body.question,
        )

    # Retrieve relevant evidence
    retrieval = RetrievalService(db)
    evidence_items = await retrieval.search(
        query=body.question,
        repository_id=str(body.repository_id),
        top_k=8,
    )

    # Build Gemini answer
    answer = await _generate_answer(
        question=body.question,
        repo_name=f"{repo.owner}/{repo.name}",
        evidence=evidence_items,
    )

    evidence_schemas = [
        EvidenceItemSchema(
            chunk_id=e.chunk_id,
            file_path=e.file_path,
            line_start=e.line_start,
            line_end=e.line_end,
            text=e.text,
            symbol_name=e.symbol_name,
            language=e.language,
            chunk_type=e.chunk_type,
            score=e.score,
            retrieval_method=e.retrieval_method,
        )
        for e in evidence_items
    ]

    return ChatQueryResponse(
        answer=answer,
        evidence=evidence_schemas,
        repository_id=body.repository_id,
        question=body.question,
    )


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

    # Build context from evidence
    context_parts: list[str] = []
    total_chars = 0
    for item in evidence:
        snippet = f"File: {item.file_path} (lines {item.line_start}–{item.line_end})\n```\n{item.text}\n```"
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
