import os
from fastapi import APIRouter, HTTPException, status
from openai import AuthenticationError
from src.llm.client import (
    LLMTimeoutException,
    LLMTransientException,
    generate_and_validate_changelog,
)
from src.llm.schema import ChangelogInput, ChangelogOutput, CommitType

router = APIRouter()


@router.post(
    "/changelog",
    response_model=ChangelogOutput,
    status_code=status.HTTP_200_OK,
)
def generate_changelog(payload: ChangelogInput):
    # 1. Kill Switch Check
    if os.environ.get("LLM_ENABLED", "true").lower() == "false":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service is currently disabled via operational kill switch.",
        )

    # 2. Stub Mode Check
    if os.environ.get("LLM_STUB") == "1":
        return ChangelogOutput(
            type=CommitType.feat,
            scope="auth",
            summary="Add support for passwordless authentication",
            confidence=0.98,
        )

    # 3. Execution with production error boundary
    try:
        return generate_and_validate_changelog(payload.commit)
    except LLMTimeoutException as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(e),
        )
    except AuthenticationError as e:
        # Fails immediately without retrying
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Provider authentication error: {str(e)}",
        )
    except LLMTransientException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )