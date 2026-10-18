import os
from pathlib import Path
from openai import OpenAI

PROMPT_FILE = Path(__file__).resolve().parent.parent.parent / "prompts" / "changelog-v1.md"

def get_llm_client() -> OpenAI:
    return OpenAI(
        base_url=os.environ.get("LLM_BASE_URL"),
        api_key=os.environ.get("LLM_API_KEY"),
    )

def load_system_prompt() -> str:
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()


def call_llm(commit_message: str) -> str:
    client = get_llm_client()
    system_prompt = load_system_prompt()
    model = os.environ.get("LLM")

    # Keep system instructions and untrusted user input strictly separate
    response = client.chat.completions.create(
        model=model,
        temperature=0.0,  # Low temperature for deterministic outputs
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": commit_message},
        ],
    )
    return response.choices[0].message.content