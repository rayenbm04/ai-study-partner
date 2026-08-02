"""Domain exceptions.

Services raise these instead of HTTPException so business logic stays
framework-free and testable without FastAPI. A single generic handler in
main.py maps them to HTTP responses using the status_code each carries.
"""
from fastapi import status


class DomainError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class EmailAlreadyRegisteredError(DomainError):
    status_code = status.HTTP_409_CONFLICT

    def __init__(self, email: str):
        super().__init__(f"An account with email '{email}' already exists.")


class InvalidCredentialsError(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED

    def __init__(self):
        super().__init__("Incorrect email or password.")


class InvalidRefreshTokenError(DomainError):
    status_code = status.HTTP_401_UNAUTHORIZED

    def __init__(self):
        super().__init__("Refresh token is invalid, expired, or has already been used.")


class UserNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, user_id: str):
        super().__init__(f"User '{user_id}' was not found.")


class SubjectNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, subject_id: str):
        super().__init__(f"Subject '{subject_id}' was not found.")


class DuplicateSubjectError(DomainError):
    status_code = status.HTTP_409_CONFLICT

    def __init__(self, name: str):
        super().__init__(f"You already have a subject named '{name}'.")


class UnsupportedFileTypeError(DomainError):
    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE

    def __init__(self, filename: str):
        super().__init__(f"'{filename}' is not a supported document type.")


class FileTooLargeError(DomainError):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE

    def __init__(self, max_mb: int):
        super().__init__(f"File exceeds the {max_mb} MB upload limit.")


class DocumentNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, document_id: str):
        super().__init__(f"Document '{document_id}' was not found.")


class ExtractionError(DomainError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

    def __init__(self, filename: str, reason: str):
        super().__init__(f"Could not extract content from '{filename}': {reason}")
