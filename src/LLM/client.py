import json
import logging
import os
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)
from pydantic import ValidationError
from src.llm.schema import ChangelogOutput

logger = logging.getLogger("uvicorn.error")

PROMPT_FILE = (
    Path(__file__).resolve().parent.parent.parent
    / "prompts"
    / "changelog-v1.md"
)
QUARANTINE_FILE = (
    Path(__file__).resolve().parent.parent.parent / "logs" / "quarantine.jsonl"
)
COST_LOG_FILE = (
    Path(__file__).resolve().parent.parent.parent / "logs" / "cost.jsonl"
)
PROMPT_VERSION = "changelog-v1"


class LLMTimeoutException(Exception):
    """Raised when the LLM client call times out."""


class LLMTransientException(Exception):
    """Raised when a retryable server or rate limit error occurs."""


def get_llm_client() -> OpenAI:
    # Disable internal SDK retries (max_retries=0) so our backoff policy controls retry counts explicitly
    return OpenAI(
        base_url=os.environ.get("LLM_BASE_URL"),
        api_key=os.environ.get("LLM_API_KEY"),
        timeout=30.0,
        max_retries=0,
    )


def load_system_prompt() -> str:
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()


def clean_and_extract_json(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE).strip()

    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")
    if start_idx == -1 or end_idx == -1 or start_idx > end_idx:
        raise ValueError("No JSON object found in model output")

    return json.loads(cleaned[start_idx : end_idx + 1])


def log_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    duration_ms: float,
    needed_repair: bool,
):
    """Appends structured token and performance metrics to logs/cost.jsonl."""
    COST_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "input_tokens": prompt_tokens,
        "output_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "duration_ms": round(duration_ms, 2),
        "needed_repair": needed_repair,
    }
    with open(COST_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def log_quarantine(commit_input: str, raw_output: str, error_message: str):
    QUARANTINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "input": commit_input,
        "raw_output": raw_output,
        "error": error_message,
    }
    with open(QUARANTINE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def execute_call_with_retries(client: OpenAI, model: str, messages: list):
    """Executes a chat completion with exponential backoff + jitter on 429, 5xx, or timeouts."""
    max_retries = 2
    base_delay = 1.0

    for attempt in range(max_retries + 1):
        try:
            return client.chat.completions.create(
                model=model,
                temperature=0.0,
                messages=messages,
            )
        except APITimeoutError as exc:
            if attempt == max_retries:
                raise LLMTimeoutException("Model request timed out after 30s") from exc
        except RateLimitError as exc:
            if attempt == max_retries:
                raise LLMTransientException(f"Rate limit exceeded: {exc}") from exc
        except APIStatusError as exc:
            # Never retry client-side credential/authorization errors (400, 401, 403)
            if exc.status_code in (400, 401, 403):
                raise exc
            # Retry transient server errors (500, 502, 503, 504)
            if attempt == max_retries:
                raise LLMTransientException(f"Server error {exc.status_code}: {exc}") from exc
        except APIConnectionError as exc:
            if attempt == max_retries:
                raise LLMTransientException("Network connection failed") from exc

        # Exponential backoff with random jitter (e.g. 1s + jitter, 2s + jitter)
        delay = (base_delay * (2 ** attempt)) + random.uniform(0.1, 0.5)
        logger.warning(f"Transient error encountered. Retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})...")
        time.sleep(delay)


def generate_and_validate_changelog(commit_message: str) -> ChangelogOutput:
    client = get_llm_client()
    system_prompt = load_system_prompt()
    model = os.environ.get("LLM_MODEL")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": commit_message},
    ]

    start_time = time.time()
    needed_repair = False
    total_prompt_tokens = 0
    total_completion_tokens = 0

    # Attempt 1: Main call
    res = execute_call_with_retries(client, model, messages)
    if res.usage:
        total_prompt_tokens += res.usage.prompt_tokens
        total_completion_tokens += res.usage.completion_tokens

    raw_output = res.choices[0].message.content

    try:
        parsed_dict = clean_and_extract_json(raw_output)
        validated = ChangelogOutput.model_validate(parsed_dict)
        duration_ms = (time.time() - start_time) * 1000
        log_cost(model, total_prompt_tokens, total_completion_tokens, duration_ms, needed_repair)
        return validated
    except (ValueError, json.JSONDecodeError, ValidationError) as exc:
        initial_error = str(exc)
        needed_repair = True

    # Attempt 2: One repair retry
    repair_instruction = (
        f"Your previous answer was rejected for this reason: {initial_error}. "
        "Return only corrected JSON matching the schema."
    )
    repair_messages = list(messages)
    repair_messages.append({"role": "assistant", "content": raw_output})
    repair_messages.append({"role": "user", "content": repair_instruction})

    repair_res = execute_call_with_retries(client, model, repair_messages)
    if repair_res.usage:
        total_prompt_tokens += repair_res.usage.prompt_tokens
        total_completion_tokens += repair_res.usage.completion_tokens

    repair_raw_output = repair_res.choices[0].message.content

    try:
        repaired_dict = clean_and_extract_json(repair_raw_output)
        validated = ChangelogOutput.model_validate(repaired_dict)
        duration_ms = (time.time() - start_time) * 1000
        log_cost(model, total_prompt_tokens, total_completion_tokens, duration_ms, needed_repair)
        return validated
    except (ValueError, json.JSONDecodeError, ValidationError) as exc:
        duration_ms = (time.time() - start_time) * 1000
        log_cost(model, total_prompt_tokens, total_completion_tokens, duration_ms, needed_repair)
        log_quarantine(commit_message, repair_raw_output, f"Repair failed: {str(exc)}")
        raise ValueError("Model response could not be validated against schema after repair attempt") from exc