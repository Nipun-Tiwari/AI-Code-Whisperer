from __future__ import annotations

import json
import re
from typing import Any

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import WorkflowState
from app.config import get_settings
from app.retrieval.service import RetrievalService

logger = structlog.get_logger(__name__)

_OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"
_MAX_PACKAGES_PER_BATCH = 50

_ECOSYSTEM_MAP = {
    "requirements.txt": "PyPI",
    "pyproject.toml": "PyPI",
    "Pipfile": "PyPI",
    "package.json": "npm",
    "go.mod": "Go",
    "Cargo.toml": "crates.io",
}

_SECRET_PATTERN = re.compile(
    r'(password|secret|api_key|token|passwd|pwd)\s*=\s*["\']([^"\']{4})([^"\']*)["\']',
    re.IGNORECASE,
)
_EVAL_PATTERN = re.compile(r'\beval\s*\(')
_DANGEROUS_HTML_PATTERN = re.compile(r'dangerouslySetInnerHTML')
_SQL_CONCAT_PATTERN = re.compile(r'["\']SELECT[^"\']*["\'\s]*\+|f["\']SELECT')


async def security_agent_node(state: WorkflowState, db: AsyncSession | None = None) -> WorkflowState:
    """Scan for dependency vulnerabilities and insecure code patterns."""
    settings = get_settings()

    dependency_findings: list[dict] = []
    code_findings: list[dict] = []
    manifests_scanned: list[str] = []
    unsupported_manifests: list[str] = []
    scan_incomplete = False

    # Step 1: Retrieve manifest files via search
    manifest_names = ["package.json", "requirements.txt", "pyproject.toml", "Pipfile", "go.mod", "Cargo.toml"]
    manifest_contents: dict[str, str] = {}

    if db is not None:
        retrieval = RetrievalService(db)
        for manifest_name in manifest_names:
            try:
                items = await retrieval.search(
                    query=manifest_name,
                    repository_id=state["repository_id"],
                    top_k=3,
                    filters=None,
                )
                for item in items:
                    fname = item.file_path.split("/")[-1].split("\\")[-1]
                    if fname in manifest_names and fname not in manifest_contents:
                        manifest_contents[fname] = item.text
            except Exception as exc:
                logger.warning("Security agent manifest retrieval failed", manifest=manifest_name, error=str(exc))
                scan_incomplete = True

        # Step 4: Static pattern scan on code chunks
        try:
            code_items = await retrieval.search(
                query="function class import",
                repository_id=state["repository_id"],
                top_k=20,
            )
            for item in code_items:
                code_findings.extend(_scan_code_patterns(item.file_path, item.text, item.line_start))
        except Exception as exc:
            logger.warning("Security agent code scan failed", error=str(exc))
            scan_incomplete = True

    # Step 2 & 3: Parse manifests and check OSV
    all_packages: list[dict] = []
    for fname, content in manifest_contents.items():
        manifests_scanned.append(fname)
        packages = _parse_manifest(fname, content)
        ecosystem = _ECOSYSTEM_MAP.get(fname)
        if ecosystem and packages:
            for pkg in packages:
                pkg["ecosystem"] = ecosystem
                pkg["manifest"] = fname
            all_packages.extend(packages)

    # Check OSV in batches
    if all_packages:
        try:
            osv_findings = await _check_osv_batch(all_packages)
            dependency_findings.extend(osv_findings)
        except Exception as exc:
            logger.warning("OSV batch check failed", error=str(exc))
            scan_incomplete = True

    # Note unsupported manifests
    for fname in manifest_names:
        if fname not in manifest_contents and fname not in unsupported_manifests:
            unsupported_manifests.append(fname)

    result = {
        "scan_summary": {
            "manifests_scanned": len(manifests_scanned),
            "total_findings": len(dependency_findings) + len(code_findings),
            "by_severity": _count_by_severity(dependency_findings + code_findings),
        },
        "dependency_findings": dependency_findings,
        "code_findings": code_findings,
        "scan_incomplete": scan_incomplete,
        "unsupported_manifests": unsupported_manifests,
        "manifests_scanned": manifests_scanned,
    }

    return {
        **state,
        "agent_outputs": {**state.get("agent_outputs", {}), "security_agent": result},
    }


def _parse_manifest(filename: str, content: str) -> list[dict]:
    """Extract package name + version from a manifest file."""
    packages: list[dict] = []

    if filename == "requirements.txt":
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Handle ==, >=, <=, ~=, !=
            m = re.match(r"^([A-Za-z0-9_.\-]+)\s*[=><~!]=\s*([A-Za-z0-9_.\-]+)", line)
            if m:
                packages.append({"name": m.group(1), "version": m.group(2)})

    elif filename == "package.json":
        try:
            data: dict[str, Any] = json.loads(content)
            for section in ("dependencies", "devDependencies"):
                for name, version_spec in data.get(section, {}).items():
                    version = str(version_spec).lstrip("^~>=<")
                    packages.append({"name": name, "version": version.split(" ")[0]})
        except json.JSONDecodeError:
            pass

    elif filename == "pyproject.toml":
        # Simple regex parse for common formats
        for line in content.splitlines():
            m = re.match(r'^\s*["\']?([A-Za-z0-9_.\-]+)["\']?\s*[=><~!]=\s*["\']?([A-Za-z0-9_.\-]+)', line)
            if m and m.group(1) not in ("python", "Python"):
                packages.append({"name": m.group(1), "version": m.group(2)})

    elif filename == "Pipfile":
        in_packages = False
        for line in content.splitlines():
            if line.strip().startswith("[packages]") or line.strip().startswith("[dev-packages]"):
                in_packages = True
                continue
            if line.strip().startswith("[") and in_packages:
                in_packages = False
            if in_packages:
                m = re.match(r'^\s*([A-Za-z0-9_.\-]+)\s*=\s*["\']([^"\']+)["\']', line)
                if m:
                    version = m.group(2).lstrip("^~>=<")
                    packages.append({"name": m.group(1), "version": version})

    return packages


async def _check_osv_batch(packages: list[dict]) -> list[dict]:
    """Query OSV API for known vulnerabilities in a list of packages."""
    findings: list[dict] = []

    # Build queries
    queries = []
    for pkg in packages[:_MAX_PACKAGES_PER_BATCH]:
        queries.append({
            "package": {
                "name": pkg["name"],
                "ecosystem": pkg["ecosystem"],
            },
            "version": pkg.get("version", ""),
        })

    if not queries:
        return []

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.post(_OSV_BATCH_URL, json={"queries": queries})
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("OSV API request failed", error=str(exc))
            return []

    results = data.get("results", [])
    for i, result in enumerate(results):
        if i >= len(packages):
            break
        pkg = packages[i]
        vulns = result.get("vulns", [])
        for vuln in vulns:
            severity = _extract_severity(vuln)
            affected = vuln.get("affected", [])
            fixed_version = _extract_fixed_version(affected, pkg.get("version", ""))
            findings.append({
                "package": pkg["name"],
                "version": pkg.get("version", "unknown"),
                "ecosystem": pkg.get("ecosystem", "unknown"),
                "severity": severity,
                "advisory_id": vuln.get("id", "unknown"),
                "description": vuln.get("summary", vuln.get("details", "No description"))[:300],
                "fixed_version": fixed_version,
                "source": "OSV",
            })

    return findings


def _extract_severity(vuln: dict) -> str:
    """Extract CVSS severity from an OSV advisory."""
    for severity_entry in vuln.get("severity", []):
        score_str = severity_entry.get("score", "")
        # CVSS v3 e.g. "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
        if "CVSS" in score_str:
            if "/C:H" in score_str and "/I:H" in score_str:
                return "critical"
            if "/C:H" in score_str or "/I:H" in score_str or "/A:H" in score_str:
                return "high"
            if "/C:L" in score_str or "/I:L" in score_str:
                return "medium"
            return "low"
    # Fallback: check database_specific
    db_specific = vuln.get("database_specific", {})
    severity = db_specific.get("severity", "").lower()
    if severity in ("critical", "high", "moderate", "medium", "low"):
        return "medium" if severity == "moderate" else severity
    return "unknown"


def _extract_fixed_version(affected: list[dict], current_version: str) -> str | None:
    """Try to find the fixed version from OSV affected ranges."""
    for entry in affected:
        for rng in entry.get("ranges", []):
            for event in rng.get("events", []):
                if "fixed" in event:
                    return event["fixed"]
    return None


def _scan_code_patterns(file_path: str, code: str, line_start: int) -> list[dict]:
    """Run static pattern checks on a code chunk."""
    findings: list[dict] = []
    lines = code.splitlines()

    for i, line in enumerate(lines):
        actual_line = line_start + i

        # Hardcoded secrets
        m = _SECRET_PATTERN.search(line)
        if m:
            masked = f'{m.group(1)} = "{m.group(2)}****"'
            findings.append({
                "rule": "hardcoded_secret",
                "file_path": file_path,
                "line": actual_line,
                "severity": "high",
                "description": f"Potential hardcoded secret found: {m.group(1)}",
                "masked_evidence": masked,
            })

        # eval() usage
        if _EVAL_PATTERN.search(line):
            findings.append({
                "rule": "unsafe_eval",
                "file_path": file_path,
                "line": actual_line,
                "severity": "high",
                "description": "Use of eval() — can execute arbitrary code",
                "masked_evidence": line.strip()[:80],
            })

        # dangerouslySetInnerHTML
        if _DANGEROUS_HTML_PATTERN.search(line):
            findings.append({
                "rule": "dangerous_html",
                "file_path": file_path,
                "line": actual_line,
                "severity": "medium",
                "description": "dangerouslySetInnerHTML usage — potential XSS risk",
                "masked_evidence": line.strip()[:80],
            })

        # SQL concatenation
        if _SQL_CONCAT_PATTERN.search(line):
            findings.append({
                "rule": "sql_injection_risk",
                "file_path": file_path,
                "line": actual_line,
                "severity": "high",
                "description": "SQL query built by string concatenation — potential SQL injection",
                "masked_evidence": line.strip()[:80],
            })

    return findings


def _count_by_severity(findings: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0}
    for f in findings:
        sev = f.get("severity", "unknown")
        counts[sev] = counts.get(sev, 0) + 1
    return counts
