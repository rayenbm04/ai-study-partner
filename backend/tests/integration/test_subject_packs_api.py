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


async def _seed_bac_math(test_engine):
    sessionmaker = async_sessionmaker(bind=test_engine, expire_on_commit=False, class_=AsyncSession)
    async with sessionmaker() as session:
        repo = SqlAlchemyCurriculumRepository(session)
        country = await repo.create_country(name="Tunisia", code="TN")
        system = await repo.create_education_system(country_id=country.id, name="Tunisian National System")
        level = await repo.create_academic_level(education_system_id=system.id, name="Bac", order_index=0)
        section = await repo.create_section(academic_level_id=level.id, name="Math")
        await repo.create_subject(academic_level_id=level.id, section_id=section.id, name="Mathematiques")
        await repo.create_subject(academic_level_id=level.id, section_id=section.id, name="Physique")
        await session.commit()
    return {"country": country, "system": system, "level": level, "section": section}


async def test_apply_pack_creates_subjects(client, test_engine):
    headers = await _register_and_login(client, "alice@example.com")
    seeded = await _seed_bac_math(test_engine)

    resp = await client.post(
        "/api/v1/subject-packs/apply",
        json={"academic_level_id": seeded["level"].id, "section_id": seeded["section"].id},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert {s["name"] for s in body["created"]} == {"Mathematiques", "Physique"}
    assert body["skipped_duplicate_names"] == []

    subjects_resp = await client.get("/api/v1/subjects", headers=headers)
    assert len(subjects_resp.json()) == 2


async def test_apply_pack_unknown_node_returns_404(client):
    headers = await _register_and_login(client, "alice@example.com")
    resp = await client.post(
        "/api/v1/subject-packs/apply",
        json={"academic_level_id": "does-not-exist", "section_id": None},
        headers=headers,
    )
    assert resp.status_code == 404


async def test_list_and_remove_applied_pack(client, test_engine):
    headers = await _register_and_login(client, "alice@example.com")
    seeded = await _seed_bac_math(test_engine)

    await client.post(
        "/api/v1/subject-packs/apply",
        json={"academic_level_id": seeded["level"].id, "section_id": seeded["section"].id},
        headers=headers,
    )

    list_resp = await client.get("/api/v1/subject-packs", headers=headers)
    assert list_resp.status_code == 200
    packs = list_resp.json()
    assert len(packs) == 1
    assert packs[0]["subject_count"] == 2
    assert packs[0]["country_name"] == "Tunisia"

    remove_resp = await client.post(
        "/api/v1/subject-packs/remove",
        json={"academic_level_id": seeded["level"].id, "section_id": seeded["section"].id},
        headers=headers,
    )
    assert remove_resp.status_code == 200
    assert remove_resp.json()["removed_count"] == 2

    subjects_resp = await client.get("/api/v1/subjects", headers=headers)
    assert subjects_resp.json() == []

    list_after_remove_resp = await client.get("/api/v1/subject-packs", headers=headers)
    assert list_after_remove_resp.json() == []


async def test_packs_are_isolated_between_users(client, test_engine):
    alice_headers = await _register_and_login(client, "alice@example.com")
    bob_headers = await _register_and_login(client, "bob@example.com")
    seeded = await _seed_bac_math(test_engine)

    await client.post(
        "/api/v1/subject-packs/apply",
        json={"academic_level_id": seeded["level"].id, "section_id": seeded["section"].id},
        headers=alice_headers,
    )

    bob_list_resp = await client.get("/api/v1/subject-packs", headers=bob_headers)
    assert bob_list_resp.json() == []
