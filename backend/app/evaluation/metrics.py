from __future__ import annotations


def recall_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int) -> float:
    """
    Fraction of relevant items found in the top-k retrieved results.

    Returns 0.0 when relevant_ids is empty.
    """
    if not relevant_ids:
        return 0.0
    top_k = set(retrieved_ids[:k])
    relevant = set(relevant_ids)
    return len(top_k & relevant) / len(relevant)


def mean_reciprocal_rank(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
    """
    MRR: 1 / rank of the first relevant item in retrieved_ids.

    Returns 0.0 when no relevant item appears.
    """
    relevant = set(relevant_ids)
    for rank, item_id in enumerate(retrieved_ids, start=1):
        if item_id in relevant:
            return 1.0 / rank
    return 0.0


def citation_accuracy(citations: list[dict], ground_truth: list[dict]) -> float:
    """
    Fraction of ground-truth citations that are matched by a retrieved citation.

    A match requires the same file_path and an overlapping line range.
    Returns 0.0 when ground_truth is empty.
    """
    if not ground_truth:
        return 0.0

    matched = 0
    for gt in ground_truth:
        gt_path = gt.get("file_path", "")
        gt_start = gt.get("line_start", 0)
        gt_end = gt.get("line_end", gt_start)
        for cit in citations:
            if cit.get("file_path") != gt_path:
                continue
            cit_start = cit.get("line_start", 0)
            cit_end = cit.get("line_end", cit_start)
            # Overlap: not (cit_end < gt_start or cit_start > gt_end)
            if not (cit_end < gt_start or cit_start > gt_end):
                matched += 1
                break
    return matched / len(ground_truth)


def token_reduction_pct(baseline_tokens: int, optimized_tokens: int) -> float:
    """
    Percentage reduction in token usage from baseline to optimized.

    Returns 0.0 if baseline is zero.
    """
    if baseline_tokens <= 0:
        return 0.0
    return ((baseline_tokens - optimized_tokens) / baseline_tokens) * 100.0
