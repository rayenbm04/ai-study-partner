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


class PseudoAlreadyTakenError(DomainError):
    status_code = status.HTTP_409_CONFLICT

    def __init__(self, pseudo: str):
        super().__init__(f"'{pseudo}' is already taken.")


class PasswordMismatchError(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self):
        super().__init__("Password and confirmation don't match.")


class WeakPasswordError(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, reason: str):
        super().__init__(f"That password isn't secure enough: {reason}")


class DuplicateSubjectError(DomainError):
    status_code = status.HTTP_409_CONFLICT

    def __init__(self, name: str):
        super().__init__(f"You already have a subject named '{name}'.")


class AcademicLevelNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, academic_level_id: str):
        super().__init__(f"Academic level '{academic_level_id}' was not found.")


class SectionNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, section_id: str):
        super().__init__(f"Section '{section_id}' was not found.")


class SectionDoesNotBelongToLevelError(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, section_id: str, academic_level_id: str):
        super().__init__(f"Section '{section_id}' does not belong to academic level '{academic_level_id}'.")


class CurriculumPackNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, academic_level_id: str, section_id: str | None):
        where = f"academic level '{academic_level_id}'" + (f", section '{section_id}'" if section_id else "")
        super().__init__(f"No curriculum subjects found for {where}.")


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


class ConversationNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, conversation_id: str):
        super().__init__(f"Conversation '{conversation_id}' was not found.")


class InvalidSummaryTypeError(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, summary_type: str, allowed: tuple[str, ...]):
        super().__init__(f"'{summary_type}' is not a valid summary type. Expected one of: {', '.join(allowed)}.")


class DocumentNotReadyError(DomainError):
    status_code = status.HTTP_409_CONFLICT

    def __init__(self, document_id: str, status_value: str):
        super().__init__(
            f"Document '{document_id}' isn't ready yet (status: '{status_value}'). "
            "Wait for ingestion to finish before generating study material from it."
        )


class SummaryNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, document_id: str, summary_type: str):
        super().__init__(f"No '{summary_type}' summary has been generated yet for document '{document_id}'.")


class FlashcardNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, flashcard_id: str):
        super().__init__(f"Flashcard '{flashcard_id}' was not found.")


class QuizNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, quiz_id: str):
        super().__init__(f"Quiz '{quiz_id}' was not found.")


class QuizQuestionNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, question_id: str):
        super().__init__(f"Quiz question '{question_id}' was not found.")


class QuizAttemptNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, attempt_id: str):
        super().__init__(f"Quiz attempt '{attempt_id}' was not found.")


class QuizAttemptAlreadySubmittedError(DomainError):
    status_code = status.HTTP_409_CONFLICT

    def __init__(self, attempt_id: str):
        super().__init__(f"Quiz attempt '{attempt_id}' has already been submitted.")


class StudyPlanNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, study_plan_id: str):
        super().__init__(f"Study plan '{study_plan_id}' was not found.")


class StudyPlanItemNotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, item_id: str):
        super().__init__(f"Study plan item '{item_id}' was not found.")


class EmptyStudyPlanError(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self):
        super().__init__("Can't generate a study plan: none of the selected subjects have any concepts yet.")


class InvalidStudyPlanItemStatusError(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, status_value: str, allowed: tuple[str, ...]):
        super().__init__(f"'{status_value}' is not a valid study plan item status. Expected one of: {', '.join(allowed)}.")
