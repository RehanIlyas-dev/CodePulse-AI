import asyncio
import json
import logging
import os
import re

import httpx
from dotenv import load_dotenv
from pydantic import ValidationError

from app.schemas.scan import AIAnalysisResult

logger = logging.getLogger(__name__)

load_dotenv()

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://opencode.ai/zen/v1").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "nemotron-3.5-lightning-free")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "90"))

client = httpx.AsyncClient(timeout=LLM_TIMEOUT)

SYSTEM_PROMPT = """
You are an expert static analysis engine and senior code reviewer.
Analyze the provided source code along with its calculated AST metrics.

Respond STRICTLY with one valid JSON object and nothing else - no markdown fences,
no commentary. It must match this structure exactly:
{
    "time_complexity": "O(N)",
    "space_complexity": "O(1)",
    "security_score": 85,
    "maintainability_score": 90,
    "issues": [
        {
            "type": "security|performance|bug|style",
            "line_number": 12,
            "description": "Explanation",
            "suggestion": "Fix"
        }
    ],
    "refactored_code": "Cleaned up code string"
}
"""

USER_TEMPLATE = """
Code to Analyze:
```
{code}
```

Calculated AST Metrics:
{ast_metrics}
"""


class LLMStatusError(Exception):
    """Non-retryable upstream error carrying its HTTP status."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        super().__init__(f"LLM HTTP {status_code}: {detail}")


def _extract_json(text: str) -> str:
    """Pull the outermost JSON object out of a model reply (tolerates fences/prose)."""
    cleaned = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text.strip())
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model response")
    return cleaned[start:end + 1]


async def _chat_completion(messages: list) -> str:
    response = await client.post(
        f"{LLM_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"},
        json={"model": LLM_MODEL, "messages": messages, "temperature": 0.2},
    )
    if response.status_code >= 400:
        raise LLMStatusError(response.status_code, response.text[:200])
    data = response.json()
    return data["choices"][0]["message"]["content"]


async def analyze_code_with_llm(code: str, ast_metrics: dict) -> AIAnalysisResult:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_TEMPLATE.format(code=code, ast_metrics=json.dumps(ast_metrics, indent=2))},
    ]

    last_error = None
    for attempt in range(1, 4):
        try:
            content = await _chat_completion(messages)
            return AIAnalysisResult.model_validate_json(_extract_json(content))
        except LLMStatusError as e:
            last_error = e
            logger.error("LLM error (attempt %d/3): %s", attempt, e)
            # Fail fast on client errors unless rate-limited
            if 400 <= e.status_code < 500 and e.status_code != 429:
                break
        except (httpx.HTTPError,) as e:
            last_error = e
            logger.warning("LLM connection error (attempt %d/3): %s", attempt, e)
        except ValidationError as e:
            last_error = e
            logger.warning("Invalid JSON from LLM (attempt %d/3)", attempt)
            messages.append({"role": "system", "content": "Your previous response was not valid JSON. Return ONLY the JSON object."})

        if attempt < 3:
            await asyncio.sleep(2 ** attempt)

    raise RuntimeError(f"AI analysis failed after 3 attempts: {last_error}") from last_error
