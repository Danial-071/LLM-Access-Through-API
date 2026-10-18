import os
from fastapi import FastAPI, HTTPException, APIRouter
from dotenv import load_dotenv
from src.llm.schema import ChangelogInput, ChangelogOutput, CommitType
from src.llm.client import call_llm
load_dotenv()

router = APIRouter()

@router.post("/changelog")
def generate_changelog(payload: ChangelogInput):
    # Stub Mode: skips the model completely if LLM_STUB=1
    if os.environ.get("LLM_STUB") == "1":
        
        return ChangelogOutput(
            type=CommitType.feat,
            scope="auth",
            summary="Add support for passwordless authentication",
            confidence=0.98,
        )

    # Model call logic will be added in Stage 2
    raw_response = call_llm(payload.commit)
    return {"raw_output": raw_response}