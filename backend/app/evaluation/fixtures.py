from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EvalQuery:
    question: str
    task_type: str  # repository_qa | investigation | documentation
    expected_evidence_patterns: list[str]  # keywords expected in retrieved chunks
    description: str = ""


# Representative evaluation queries that do not depend on a specific repository.
# These exercise different retrieval and reasoning paths.
EVAL_QUERIES: list[EvalQuery] = [
    EvalQuery(
        question="What are the main entry points of this application?",
        task_type="repository_qa",
        expected_evidence_patterns=["main", "app", "__init__", "router", "startup", "entrypoint"],
        description="Repository Q&A: locate entry points",
    ),
    EvalQuery(
        question="How is authentication implemented in this codebase?",
        task_type="repository_qa",
        expected_evidence_patterns=["auth", "token", "jwt", "session", "user", "login"],
        description="Repository Q&A: authentication mechanism",
    ),
    EvalQuery(
        question="A 500 error is raised when saving data to the database. What could cause this?",
        task_type="investigation",
        expected_evidence_patterns=["exception", "error", "database", "commit", "rollback", "connection"],
        description="Investigation: database 500 error",
    ),
    EvalQuery(
        question="Are there any hardcoded credentials or secrets in the source code?",
        task_type="repository_qa",
        expected_evidence_patterns=["password", "secret", "api_key", "token", "credential", "key"],
        description="Security-adjacent repository Q&A: hardcoded secrets scan",
    ),
    EvalQuery(
        question="Generate a technical overview of the main modules in this repository.",
        task_type="documentation",
        expected_evidence_patterns=["module", "class", "function", "import", "service", "component"],
        description="Documentation: module overview generation",
    ),
]
