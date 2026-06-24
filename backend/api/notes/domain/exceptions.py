"""Domain exceptions. HTTP-agnostic by design: the controller layer maps them
to status codes (see infrastructure/api/controllers.py)."""


class NotesDomainError(Exception):
    """Base class for the notes domain."""


class QuestionNotFoundError(NotesDomainError):
    """The question does not exist (or is not visible to the caller)."""


class NoteNotFoundError(NotesDomainError):
    """The note does not exist."""


class AnswerGenerationError(NotesDomainError):
    """Answer generation failed; carries a machine-readable error code."""

    def __init__(self, error_code: str, message: str = ""):
        self.error_code = error_code
        super().__init__(message or error_code)
