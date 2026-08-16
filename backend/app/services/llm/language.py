"""Maps the mobile app's UI language codes to a prompt instruction, so
generated content (chat answers, quizzes, flashcards, summaries) matches
whatever language the student has the app set to, instead of always coming
back in English regardless of UI language. The mobile app sends its current
language as the X-App-Language header on every request (see
lib/api/client.ts) — routes read it via app/api/v1/deps.py's get_language
and pass it down into the relevant service call.
"""

SUPPORTED_LANGUAGES = {"en": "English", "fr": "French", "ar": "Arabic"}
DEFAULT_LANGUAGE = "en"


def normalize_language(code: str | None) -> str:
    if code and code.lower() in SUPPORTED_LANGUAGES:
        return code.lower()
    return DEFAULT_LANGUAGE


def language_instruction(code: str) -> str:
    """A system-prompt sentence to append so generated content comes back in
    the right language — stated explicitly even for English, since an
    otherwise all-English prompt otherwise tends to default to English
    regardless of what's asked for."""
    name = SUPPORTED_LANGUAGES.get(code, SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE])
    return f"Respond in {name}, regardless of what language the source material is in."
