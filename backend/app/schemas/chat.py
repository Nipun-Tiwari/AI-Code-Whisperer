from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class ChatQueryRequest(BaseModel):
    repository_id: uuid.UUID
    question: str = Field(..., min_length=3, max_length=2000)


class EvidenceItemSchema(BaseModel):
    chunk_id: str
    file_path: str
    line_start: int
    line_end: int
    text: str
    symbol_name: str | None
    language: str
    chunk_type: str
    score: float
    retrieval_method: str


class ChatQueryResponse(BaseModel):
    answer: str
    evidence: list[EvidenceItemSchema]
    repository_id: uuid.UUID
    question: str
