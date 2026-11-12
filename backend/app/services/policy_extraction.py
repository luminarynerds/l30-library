# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import io
import json

from app.core.config import get_settings

EXTRACTION_PROMPT = """Extract library circulation policy values from the following document text.
Return a JSON object with exactly these fields (use sensible defaults for any not mentioned):

{
  "default_loan_period_days": 21,
  "default_renewal_limit": 2,
  "default_hold_limit": 10,
  "default_overdue_fine_per_day": 0.25,
  "default_max_fine": 10.00,
  "grace_period_days": 0,
  "fine_free_juvenile": false,
  "lost_item_threshold_days": 30
}

Field definitions:
- default_loan_period_days: standard checkout period in days (integer)
- default_renewal_limit: maximum number of renewals per item (integer)
- default_hold_limit: maximum holds a patron may place at once (integer)
- default_overdue_fine_per_day: daily overdue fine amount in dollars (decimal)
- default_max_fine: maximum fine per item in dollars (decimal)
- grace_period_days: days before fines start accruing (integer)
- fine_free_juvenile: true if children/juvenile items have no overdue fines (boolean)
- lost_item_threshold_days: days overdue before item is declared lost (integer)

Return only valid JSON with no extra text. Document text follows:

"""


async def extract_policies_from_document(file_content: bytes, filename: str) -> dict:
    text = _extract_text(file_content, filename)
    if not text.strip():
        raise ValueError("Could not extract text from document")

    settings = get_settings()
    if not settings.ollama_base_url:
        raise ValueError(
            "No local AI provider configured. Set OLLAMA_BASE_URL in your environment."
        )
    # OpenAI path intentionally removed: policy extraction runs only against the
    # local Ollama instance so document text never leaves the box.
    return await _extract_via_ollama(text, settings.ollama_base_url)


def _extract_text(content: bytes, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "txt":
        return content.decode("utf-8", errors="replace")
    elif ext == "pdf":
        import pypdf

        reader = pypdf.PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    elif ext in ("doc", "docx"):
        import docx

        doc = docx.Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs)
    raise ValueError(f"Unsupported format: .{ext}. Use PDF, DOCX, or TXT.")


async def _extract_via_ollama(text: str, base_url: str) -> dict:
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/api/generate",
            json={
                "model": "llama3.1",
                "prompt": EXTRACTION_PROMPT + text[:8000],
                "stream": False,
                "format": "json",
            },
            timeout=60.0,
        )
        response.raise_for_status()
        return json.loads(response.json()["response"])
