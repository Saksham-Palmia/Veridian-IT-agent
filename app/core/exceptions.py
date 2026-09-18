"""Custom exception hierarchy for Veridian IT Agent."""


class VeridianBaseError(Exception):
    """Base exception for all Veridian IT Agent errors."""
    status_code: int = 500
    detail: str = "An internal error occurred."

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


class NotFoundError(VeridianBaseError):
    status_code = 404
    detail = "Resource not found."


class AuthenticationError(VeridianBaseError):
    status_code = 401
    detail = "Authentication failed."


class AuthorizationError(VeridianBaseError):
    status_code = 403
    detail = "You do not have permission to perform this action."


class InvalidStateTransitionError(VeridianBaseError):
    status_code = 422
    detail = "Invalid state transition."


class PolicyRetrievalError(VeridianBaseError):
    status_code = 500
    detail = "Failed to retrieve policy."


class LLMUnavailableError(VeridianBaseError):
    status_code = 503
    detail = "LLM service is unavailable."


class ITSMError(VeridianBaseError):
    status_code = 500
    detail = "ITSM operation failed."


class NotificationError(VeridianBaseError):
    status_code = 500
    detail = "Notification delivery failed."

