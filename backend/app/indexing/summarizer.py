from __future__ import annotations

import asyncio
import structlog
from google import genai
from google.genai import types as gtypes

from app.config import get_settings

logger = structlog.get_logger(__name__)

_MAX_EXCERPT_CHARS = 3000  # ~750 tokens — keep prompts concise
# Free-tier Flash RPM is very low (often 5/min). Fail fast instead of hanging.
_SUMMARY_TIMEOUT_SECONDS = 20


class Summarizer:
    """Generate repository and module summaries using Gemini."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_model_fast

    async def generate_repository_summary(
        self,
        repo_name: str,
        file_tree: list[str],
        top_symbols: list[str],
    ) -> str:
        """Generate a 3-paragraph technical summary of the repository.

        Returns an empty string on failure so callers never persist error text
        as the repository description.
        """
        # Build a concise representation of the directory structure
        top_level_dirs: set[str] = set()
        ext_counts: dict[str, int] = {}
        for path in file_tree[:500]:  # limit to first 500 paths
            parts = path.split("/")
            if len(parts) > 1:
                top_level_dirs.add(parts[0])
            ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
            if ext:
                ext_counts[ext] = ext_counts.get(ext, 0) + 1

        top_exts = sorted(ext_counts.items(), key=lambda x: -x[1])[:8]
        symbols_sample = top_symbols[:20]

        prompt = f"""You are a technical documentation assistant. Analyze this repository and write a concise technical summary.

Repository: {repo_name}
Top-level directories: {', '.join(sorted(top_level_dirs)[:15]) or 'N/A'}
Most common file types: {', '.join(f'{ext}({n})' for ext, n in top_exts)}
Key symbols (functions/classes): {', '.join(symbols_sample)}

Write exactly 3 short paragraphs (max 300 words total):
1. Purpose: What does this repository do and what problem does it solve?
2. Main components: Key modules, directories and their roles.
3. Key patterns: Notable technical patterns, frameworks or architectural choices visible from the structure.

Be specific and factual. Only state what can be observed from the provided information."""

        try:
            response = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config=gtypes.GenerateContentConfig(
                        max_output_tokens=512,
                        temperature=0.2,
                    ),
                ),
                timeout=_SUMMARY_TIMEOUT_SECONDS,
            )
            return response.text or ""
        except Exception as exc:
            logger.warning("Repository summary generation failed", error=str(exc))
            return ""

    async def generate_module_summary(
        self,
        file_path: str,
        symbols: list[str],
        code_excerpt: str,
    ) -> str:
        """Generate a 2-paragraph summary of a module/file.

        Prefer not calling this during free-tier indexing — module summaries are
        not persisted by the pipeline and burn scarce generate_content quota.
        """
        truncated = code_excerpt[:_MAX_EXCERPT_CHARS]

        prompt = f"""Summarize this code module in exactly 2 short paragraphs (max 150 words total).

File: {file_path}
Defined symbols: {', '.join(symbols[:20]) or 'none'}

Code excerpt:
```
{truncated}
```

Paragraph 1: What this module does and its primary responsibility.
Paragraph 2: Key functions/classes and how they relate to each other.

Be concise and factual. Do not invent functionality not visible in the code."""

        try:
            response = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config=gtypes.GenerateContentConfig(
                        max_output_tokens=256,
                        temperature=0.2,
                    ),
                ),
                timeout=_SUMMARY_TIMEOUT_SECONDS,
            )
            return response.text or ""
        except Exception as exc:
            logger.warning("Module summary generation failed", file=file_path, error=str(exc))
            return ""
