from enum import StrEnum


class QuestionStatus(StrEnum):
    """User-facing question status.

    Never stored: derived by the repository — an Answer exists -> SUCCESS;
    the rag-worker's inbox record is FAILED -> FAILED; otherwise PENDING.
    """

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
