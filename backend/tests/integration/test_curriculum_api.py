from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.curriculum_repo import SqlAlchemyCurriculumRepository


async def _register_and_login(client, email):
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "firstname": "A", "lastname": "B"},
    )
    login_resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _seed_curriculum(test_engine):
    sessionmaker = async_sessionmaker(bind=test_engine, expire_on_commit=False, class_=AsyncSession)
    async with sessionmaker() as session:
        repo = SqlAlchemyCurriculumRepository(session)
        country = await repo.create_country(name="Tunisia", code="TN")
        system = await repo.create_education_system(country_id=country.id, name="Tunisian National System")
        level = await repo.create_academic_level(education_system_id=system.id, name="Bac", order_index=0)
        section = await repo.create_section(academic_level_id=level.id, name="Math")
        subject = await repo.create_subject(academic_level_id=level.id, section_id=section.id, name="Physique")
        chapter = await repo.create_chapter(curriculum_subject_id=subject.id, name="Mecanique", order_index=0)
        lesson = await repo.create_lesson(chapter_id=chapter.id, name="Cinematique", order_index=0)
        await session.commit()
    return {
        "country": country, "system": system, "level": level, "section": section,
        "subject": subject, "chapter": chapter, "lesson": lesson,
    }


async def test_browse_curriculum_tree(client, test_engine):
    headers = await _register_and_login(client, "alice@example.com")
    seeded = await _seed_curriculum(test_engine)

    countries_resp = await client.get("/api/v1/curriculum/countries", headers=headers)
    assert countries_resp.status_code == 200
    assert any(c["name"] == "Tunisia" for c in countries_resp.json())

    systems_resp = await client.get(
        f"/api/v1/curriculum/countries/{seeded['country'].id}/education-systems", headers=headers
    )
    assert [s["name"] for s in systems_resp.json()] == ["Tunisian National System"]

    levels_resp = await client.get(
        f"/api/v1/curriculum/education-systems/{seeded['system'].id}/academic-levels", headers=headers
    )
    assert [lvl["name"] for lvl in levels_resp.json()] == ["Bac"]

    sections_resp = await client.get(f"/api/v1/curriculum/academic-levels/{seeded['level'].id}/sections", headers=headers)
    assert [s["name"] for s in sections_resp.json()] == ["Math"]

    subjects_resp = await client.get(
        f"/api/v1/curriculum/academic-levels/{seeded['level'].id}/subjects",
        params={"section_id": seeded["section"].id},
        headers=headers,
    )
    assert [s["name"] for s in subjects_resp.json()] == ["Physique"]

    chapters_resp = await client.get(f"/api/v1/curriculum/subjects/{seeded['subject'].id}/chapters", headers=headers)
    assert [c["name"] for c in chapters_resp.json()] == ["Mecanique"]

    lessons_resp = await client.get(f"/api/v1/curriculum/chapters/{seeded['chapter'].id}/lessons", headers=headers)
    assert [lesson["name"] for lesson in lessons_resp.json()] == ["Cinematique"]


async def test_link_subject_to_curriculum_subject(client, test_engine):
    headers = await _register_and_login(client, "alice@example.com")
    seeded = await _seed_curriculum(test_engine)

    create_resp = await client.post("/api/v1/subjects", json={"name": "Physics"}, headers=headers)
    subject_id = create_resp.json()["id"]
    assert create_resp.json()["curriculum_subject_id"] is None

    patch_resp = await client.patch(
        f"/api/v1/subjects/{subject_id}", json={"curriculum_subject_id": seeded["subject"].id}, headers=headers
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["curriculum_subject_id"] == seeded["subject"].id
