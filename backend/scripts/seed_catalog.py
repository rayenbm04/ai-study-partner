"""Seeds one sample curriculum tree so upload + document classification can
be demoed end to end: Tunisia -> Tunisian National System -> Bac (sections
Math/Sciences/Economie) and 3eme (no sections) -> a few subjects -> a couple
of chapters each -> a couple of lessons each.

Idempotent: looks up existing rows by name before creating, so it's safe to
re-run (e.g. after adding more entries to SEED_TREE below).

Run from backend/, with DATABASE_URL pointed at a migrated database:
    python -m scripts.seed_catalog
"""
import asyncio
from collections.abc import Awaitable, Callable, Sequence
from typing import TypeVar

from app.infrastructure.db.session import AsyncSessionLocal
from app.repositories.curriculum_repo import SqlAlchemyCurriculumRepository

SEED_TREE = {
    "country": {"name": "Tunisia", "code": "TN"},
    "education_system": "Tunisian National System",
    "levels": [
        {
            "name": "Bac",
            "sections": {
                "Math": {
                    "Mathematiques": {
                        "Suites numeriques": ["Convergence", "Suites arithmetico-geometriques"],
                        "Limites et continuite": ["Limites de fonctions", "Continuite"],
                    },
                    "Physique": {
                        "Mecanique": ["Cinematique", "Dynamique"],
                        "Electricite": ["Circuits RC", "Induction electromagnetique"],
                    },
                },
                "Sciences": {
                    "Sciences de la vie et de la Terre": {
                        "Genetique": ["Transmission des caracteres hereditaires", "Mutations et diversite"],
                    },
                },
                "Economie": {
                    "Economie": {
                        "Marche et prix": ["Offre et demande", "Equilibre de marche"],
                    },
                },
            },
        },
        {
            "name": "3eme",
            "sections": None,
            "subjects": {
                "Mathematiques": {
                    "Theoreme de Thales": ["Configuration de Thales", "Reciproque de Thales"],
                },
            },
        },
    ],
}

_T = TypeVar("_T")


async def _get_or_create(existing: Sequence[_T], name: str, create: Callable[[], Awaitable[_T]]) -> _T:
    for item in existing:
        if item.name == name:
            return item
    return await create()


async def _seed_subjects(
    repo: SqlAlchemyCurriculumRepository, *, academic_level_id: str, section_id: str | None, subjects: dict
) -> None:
    for subject_name, chapters in subjects.items():
        subject = await _get_or_create(
            await repo.list_subjects(academic_level_id, section_id=section_id),
            subject_name,
            lambda subject_name=subject_name: repo.create_subject(
                academic_level_id=academic_level_id, section_id=section_id, name=subject_name
            ),
        )
        for chapter_index, (chapter_name, lesson_names) in enumerate(chapters.items()):
            chapter = await _get_or_create(
                await repo.list_chapters(subject.id),
                chapter_name,
                lambda chapter_name=chapter_name, chapter_index=chapter_index: repo.create_chapter(
                    curriculum_subject_id=subject.id, name=chapter_name, order_index=chapter_index
                ),
            )
            for lesson_index, lesson_name in enumerate(lesson_names):
                await _get_or_create(
                    await repo.list_lessons(chapter.id),
                    lesson_name,
                    lambda lesson_name=lesson_name, lesson_index=lesson_index: repo.create_lesson(
                        chapter_id=chapter.id, name=lesson_name, order_index=lesson_index
                    ),
                )


async def seed(repo: SqlAlchemyCurriculumRepository) -> None:
    country_data = SEED_TREE["country"]
    country = await _get_or_create(
        await repo.list_countries(),
        country_data["name"],
        lambda: repo.create_country(name=country_data["name"], code=country_data["code"]),
    )
    education_system_name = SEED_TREE["education_system"]
    system = await _get_or_create(
        await repo.list_education_systems(country.id),
        education_system_name,
        lambda: repo.create_education_system(country_id=country.id, name=education_system_name),
    )

    for level_index, level_data in enumerate(SEED_TREE["levels"]):
        level_name = level_data["name"]
        level = await _get_or_create(
            await repo.list_academic_levels(system.id),
            level_name,
            lambda level_name=level_name, level_index=level_index: repo.create_academic_level(
                education_system_id=system.id, name=level_name, order_index=level_index
            ),
        )

        sections = level_data.get("sections")
        if sections:
            for section_name, subjects in sections.items():
                section = await _get_or_create(
                    await repo.list_sections(level.id),
                    section_name,
                    lambda section_name=section_name: repo.create_section(academic_level_id=level.id, name=section_name),
                )
                await _seed_subjects(repo, academic_level_id=level.id, section_id=section.id, subjects=subjects)
        else:
            await _seed_subjects(repo, academic_level_id=level.id, section_id=None, subjects=level_data["subjects"])


async def main() -> None:
    async with AsyncSessionLocal() as session:
        await seed(SqlAlchemyCurriculumRepository(session))
        await session.commit()
    print("Curriculum catalog seeded.")


if __name__ == "__main__":
    asyncio.run(main())
