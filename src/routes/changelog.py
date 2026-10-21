import os
from fastapi import APIRouter, HTTPException, status
from src.llm.client import generate_and_validate_changelog
from src.llm.schema import ChangelogInput, ChangelogOutput, CommitType

router = APIRouter()


@router.post(
    "/changelog",
    response_model=ChangelogOutput,
    status_code=status.HTTP_200_OK,
)
def generate_changelog(payload: ChangelogInput):
    # Stub mode
    if os.environ.get("LLM_STUB") == "1":
        return ChangelogOutput(
            type=CommitType.feat,
            scope="auth",
            summary="Add support for passwordless authentication",
            confidence=0.98,
        )

    try:
        return generate_and_validate_changelog(payload.commit)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )