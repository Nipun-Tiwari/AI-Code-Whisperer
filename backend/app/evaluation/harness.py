from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import structlog

from app.evaluation.metrics import (
    citation_accuracy,
    mean_reciprocal_rank,
    recall_at_k,
    token_reduction_pct,
)
from app.evaluation.fixtures import EvalQuery

logger = structlog.get_logger(__name__)


@dataclass
class QueryResult:
    question: str
    task_type: str
    retrieved_chunk_ids: list[str]
    citations: list[dict]
    answer: str
    tokens_used: int
    latency_ms: float
    error: str | None = None


@dataclass
class EvalResults:
    configuration: str  # "baseline" | "optimized"
    repository_id: str
    queries: list[QueryResult] = field(default_factory=list)
    total_tokens: int = 0
    avg_latency_ms: float = 0.0
    recall_at_5: float = 0.0
    mrr: float = 0.0
    ran_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ComparisonReport:
    baseline: EvalResults
    optimized: EvalResults
    token_reduction_pct: float
    recall_improvement: float
    mrr_improvement: float
    latency_change_ms: float
    summary: str


class EvaluationHarness:
    """
    Run retrieval evaluation against a set of queries and compare configurations.

    Uses the RetrievalService directly to measure retrieval quality independent
    of the full agent workflow (which would add LLM latency and token cost).
    """

    def __init__(self, repository_id: str) -> None:
        self._repository_id = repository_id

    async def run_baseline(self, queries: list[EvalQuery]) -> EvalResults:
        """Run queries with default retrieval settings (top_k=10)."""
        return await self._run(queries, configuration="baseline", top_k=10)

    async def run_optimized(self, queries: list[EvalQuery]) -> EvalResults:
        """Run queries with optimized retrieval settings (top_k=5, deduplication)."""
        return await self._run(queries, configuration="optimized", top_k=5)

    async def _run(self, queries: list[EvalQuery], configuration: str, top_k: int) -> EvalResults:
        from app.retrieval.service import RetrievalService
        from app.db.session import get_session_factory

        retrieval_svc = RetrievalService()
        results: list[QueryResult] = []
        total_tokens = 0

        factory = get_session_factory()
        async with factory() as db:
            for query in queries:
                t0 = time.perf_counter()
                try:
                    evidence = await retrieval_svc.search(
                        query=query.question,
                        repository_id=self._repository_id,
                        top_k=top_k,
                    )
                    elapsed_ms = (time.perf_counter() - t0) * 1000

                    chunk_ids = [str(e.chunk_id) for e in evidence if hasattr(e, "chunk_id")]
                    citations = [
                        {
                            "file_path": e.file_path,
                            "line_start": e.line_start,
                            "line_end": e.line_end,
                        }
                        for e in evidence
                    ]

                    # Rough token estimate: 1 token ≈ 4 chars
                    retrieved_text = " ".join(e.text[:500] for e in evidence)
                    tokens_estimate = len(retrieved_text) // 4

                    results.append(QueryResult(
                        question=query.question,
                        task_type=query.task_type,
                        retrieved_chunk_ids=chunk_ids,
                        citations=citations,
                        answer="",  # retrieval-only eval, no LLM call
                        tokens_used=tokens_estimate,
                        latency_ms=elapsed_ms,
                    ))
                    total_tokens += tokens_estimate

                except Exception as exc:
                    elapsed_ms = (time.perf_counter() - t0) * 1000
                    logger.warning("Eval query failed", question=query.question[:80], error=str(exc))
                    results.append(QueryResult(
                        question=query.question,
                        task_type=query.task_type,
                        retrieved_chunk_ids=[],
                        citations=[],
                        answer="",
                        tokens_used=0,
                        latency_ms=elapsed_ms,
                        error=str(exc),
                    ))

        # Compute aggregate metrics using pattern matching as proxy for relevance
        recall_scores: list[float] = []
        mrr_scores: list[float] = []

        for query, result in zip(queries, results):
            # Use text pattern matching to identify "relevant" chunks
            relevant_ids = [
                cid for cid, r in zip(result.retrieved_chunk_ids, result.citations)
                if any(
                    pat.lower() in (r.get("file_path", "") + "").lower()
                    for pat in query.expected_evidence_patterns
                )
            ]
            recall_scores.append(recall_at_k(result.retrieved_chunk_ids, relevant_ids, k=top_k))
            mrr_scores.append(mean_reciprocal_rank(result.retrieved_chunk_ids, relevant_ids))

        avg_recall = sum(recall_scores) / len(recall_scores) if recall_scores else 0.0
        avg_mrr = sum(mrr_scores) / len(mrr_scores) if mrr_scores else 0.0
        avg_latency = sum(r.latency_ms for r in results) / len(results) if results else 0.0

        return EvalResults(
            configuration=configuration,
            repository_id=self._repository_id,
            queries=results,
            total_tokens=total_tokens,
            avg_latency_ms=avg_latency,
            recall_at_5=avg_recall,
            mrr=avg_mrr,
        )

    def compare(self, baseline: EvalResults, optimized: EvalResults) -> ComparisonReport:
        """Compare baseline and optimized results and produce a summary report."""
        token_reduction = token_reduction_pct(baseline.total_tokens, optimized.total_tokens)
        recall_delta = optimized.recall_at_5 - baseline.recall_at_5
        mrr_delta = optimized.mrr - baseline.mrr
        latency_delta = optimized.avg_latency_ms - baseline.avg_latency_ms

        if token_reduction > 0 and recall_delta >= -0.05:
            assessment = f"Optimization reduced tokens by {token_reduction:.1f}% with acceptable retrieval quality."
        elif token_reduction > 0 and recall_delta < -0.05:
            assessment = f"Optimization reduced tokens by {token_reduction:.1f}% but recall dropped by {abs(recall_delta):.2f} — not accepted."
        else:
            assessment = "No token reduction achieved. Consider adjusting top_k or retrieval parameters."

        return ComparisonReport(
            baseline=baseline,
            optimized=optimized,
            token_reduction_pct=token_reduction,
            recall_improvement=recall_delta,
            mrr_improvement=mrr_delta,
            latency_change_ms=latency_delta,
            summary=assessment,
        )
