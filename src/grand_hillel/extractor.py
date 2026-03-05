"""Phase 1: Claim extraction from source documents.

Reads documents and extracts every factual claim for verification.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from src.models.providers import ModelProvider

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM = """You are a precise fact-extraction agent. Your job is to read a document
and extract every claim that is stated as fact or presented as technically true.

Rules:
- Do NOT extract philosophical claims as factual (e.g. "truth and love" is PHILOSOPHICAL)
- DO extract any claim that names a number, date, person, event, technical spec, or cost
- DO extract any claim about what a model/company/person did or said
- Tag uncertainty: if the source says "approximately" or "estimated," preserve that
- Be exhaustive — miss nothing"""

EXTRACTION_PROMPT = """Read this document and extract every factual claim.

DOCUMENT:
{document_text}

For each claim, output a JSON object. Respond with a JSON array of claims:
[
  {{
    "id": "{doc_prefix}-001",
    "source_file": "{source_file}",
    "source_section": "section name",
    "claim": "the factual claim in plain language",
    "claim_type": "TECHNICAL|HISTORICAL|PHILOSOPHICAL|COST|LEGAL|CURRENT_EVENTS",
    "confidence_needed": "HIGH|MEDIUM|LOW",
    "exact_quote": "the exact sentence from the document"
  }}
]

Respond with ONLY the JSON array. No markdown, no explanation."""


async def extract_claims(
    document_path: str,
    provider: ModelProvider,
    doc_prefix: str = "DOC",
) -> list[dict]:
    """Extract all factual claims from a document."""
    path = Path(document_path)
    text = path.read_text()
    source_file = path.name

    prompt = EXTRACTION_PROMPT.format(
        document_text=text,
        doc_prefix=doc_prefix,
        source_file=source_file,
    )

    response = await provider.generate(prompt, system=EXTRACTION_SYSTEM)
    content = response.content.strip()

    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        content = content.rsplit("```", 1)[0]

    claims = json.loads(content)
    logger.info("Extracted %d claims from %s", len(claims), source_file)
    return claims


async def extract_from_multiple(
    document_paths: list[str],
    provider: ModelProvider,
) -> list[dict]:
    """Extract claims from multiple documents."""
    all_claims = []
    prefixes = {"TEXT_THAT_LIVES.md": "TL", "THE_BEE_SPEC.md": "BS"}

    for doc_path in document_paths:
        name = Path(doc_path).name
        prefix = prefixes.get(name, name[:2].upper())
        claims = await extract_claims(doc_path, provider, prefix)
        all_claims.extend(claims)

    return all_claims
