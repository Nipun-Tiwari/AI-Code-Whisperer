from __future__ import annotations

from fastapi import APIRouter, Query

from app.dependencies import DbDep, UserDep
from app.evaluation.fixtures import EVAL_QUERIES
from app.evaluation.harness import ComparisonReport, EvaluationHarness

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.post("/run", response_model=dict)
async def run_evaluation(
    user: UserDep,
    db: DbDep,
    repository_id: str = Query(..., description="Repository ID to run evaluation against"),
) -> dict:
    """
    Run baseline vs. optimized retrieval evaluation and return a comparison report.

    Uses the built-in fixture queries. No LLM calls are made — retrieval only.
    """
    harness = EvaluationHarness(repository_id=repository_id)
    baseline = await harness.run_baseline(EVAL_QUERIES)
    optimized = await harness.run_optimized(EVAL_QUERIES)
    report = harness.compare(baseline, optimized)

    return {
        "summary": report.summary,
        "token_reduction_pct": report.token_reduction_pct,
        "recall_improvement": report.recall_improvement,
        "mrr_improvement": report.mrr_improvement,
        "latency_change_ms": report.latency_change_ms,
        "baseline": {
            "configuration": report.baseline.configuration,
            "total_tokens": report.baseline.total_tokens,
            "recall_at_5": report.baseline.recall_at_5,
            "mrr": report.baseline.mrr,
            "avg_latency_ms": report.baseline.avg_latency_ms,
            "ran_at": report.baseline.ran_at.isoformat(),
        },
        "optimized": {
            "configuration": report.optimized.configuration,
            "total_tokens": report.optimized.total_tokens,
            "recall_at_5": report.optimized.recall_at_5,
            "mrr": report.optimized.mrr,
            "avg_latency_ms": report.optimized.avg_latency_ms,
            "ran_at": report.optimized.ran_at.isoformat(),
        },
    }


@router.get("/results", response_model=dict)
async def list_evaluation_results(user: UserDep, db: DbDep) -> dict:
    """
    List past evaluation runs.

    Currently returns a stub — full persistence of eval results is a future enhancement.
    """
    return {
        "results": [],
        "note": "Evaluation result persistence will be added in a future release. Use POST /run to execute a fresh evaluation.",
    }
