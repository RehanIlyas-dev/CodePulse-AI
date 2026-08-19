import asyncio
import json
import logging
import os

from dotenv import load_dotenv
from groq import AsyncGroq, APIError, APIConnectionError, APIStatusError, APITimeoutError, RateLimitError
from pydantic import ValidationError

from app.schemas.scan import AIAnalysisResult

logger = logging.getLogger(__name__)

load_dotenv()
client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"), timeout=30.0)


async def analyze_code_with_llm(code: str, ast_metrics: dict) -> AIAnalysisResult:
    messages = [
        {"role": "system", "content": """
    You are an expert static analysis engine and senior code reviewer.
    Analyze the provided source code along with its calculated AST metrics.

    You MUST respond strictly with a valid JSON object matching this structure:
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
    """},
        {"role": "user", "content": f"""
    Code to Analyze:
    ```
    {code}
    ```

    Calculated AST Metrics:
    {json.dumps(ast_metrics, indent=2)}
    """},
    ]

    last_error = None
    for attempt in range(1, 4):
        try:
            response = await client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            return AIAnalysisResult.model_validate_json(response.choices[0].message.content)
        except (RateLimitError, APIConnectionError, APITimeoutError) as e:
            last_error = e
            logger.warning("Groq error (attempt %d/3): %s", attempt, e)
        except APIError as e:
            last_error = e
            logger.error("Groq error (attempt %d/3): %s", attempt, e)
            if isinstance(e, APIStatusError) and e.status_code < 500:
                break
        except ValidationError as e:
            last_error = e
            logger.warning("Invalid JSON from LLM (attempt %d/3)", attempt)
            messages.append({"role": "system", "content": "Your previous response was not valid JSON. Return ONLY the JSON object."})

        if attempt < 3:
            await asyncio.sleep(2 ** attempt)

    raise RuntimeError(f"AI analysis failed after 3 attempts: {last_error}") from last_error