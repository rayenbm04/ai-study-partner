from pydantic import BaseModel


class SetClasseRequest(BaseModel):
    # Both None clears the student's classe (e.g. they picked wrong and want
    # to redo it) — a section without an academic_level_id doesn't mean
    # anything on its own, enforced in AccountService.set_classe.
    academic_level_id: str | None = None
    section_id: str | None = None
