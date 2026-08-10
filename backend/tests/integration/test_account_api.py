from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.curriculum_repo import SqlAlchemyCurriculumRepository

_SAMPLE_TEXT = ("Ohm's law relates voltage, current, and resistance in a circuit. " * 20).encode("utf-8")


async def _register_and_login(client, email):
    pseudo = email.split("@")[0]
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "password123",
            "confirm_password": "password123",
            "firstname": "A",
            "lastname": "B",
            "pseudo": pseudo,
            "date_of_birth": "2005-01-01",
        },
    )
    login_resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_reset_deletes_subjects_and_documents_but_keeps_login(client):
    headers = await _register_and_login(client, "alice@example.com")
    create_resp = await client.post("/api/v1/subjects", json={"name": "Physics"}, headers=headers)
    subject_id = create_resp.json()["id"]
    await client.post(
        f"/api/v1/subjects/{subject_id}/documents",
        headers=headers,
        files={"file": ("notes.txt", _SAMPLE_TEXT, "text/plain")},
    )

    reset_resp = await client.post("/api/v1/account/reset", headers=headers)
    assert reset_resp.status_code == 204

    list_resp = await client.get("/api/v1/subjects", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json() == []

    # the account itself still works — reset clears data, not the login
    login_resp = await client.post(
        "/api/v1/auth/login", json={"email": "alice@example.com", "password": "password123"}
    )
    assert login_resp.status_code == 200


async def test_reset_does_not_affect_other_users(client):
    alice_headers = await _register_and_login(client, "alice@example.com")
    bob_headers = await _register_and_login(client, "bob@example.com")
    await client.post("/api/v1/subjects", json={"name": "Physics"}, headers=alice_headers)
    await client.post("/api/v1/subjects", json={"name": "Chemistry"}, headers=bob_headers)

    await client.post("/api/v1/account/reset", headers=alice_headers)

    bob_subjects = await client.get("/api/v1/subjects", headers=bob_headers)
    assert len(bob_subjects.json()) == 1


async def test_reset_requires_auth(client):
    resp = await client.post("/api/v1/account/reset")
    assert resp.status_code == 403


async def _seed_level_and_section(test_engine):
    sessionmaker = async_sessionmaker(bind=test_engine, expire_on_commit=False, class_=AsyncSession)
    async with sessionmaker() as session:
        repo = SqlAlchemyCurriculumRepository(session)
        country = await repo.create_country(name="Tunisia", code="TN")
        system = await repo.create_education_system(country_id=country.id, name="Tunisian National System")
        level = await repo.create_academic_level(education_system_id=system.id, name="Bac", order_index=0)
        section = await repo.create_section(academic_level_id=level.id, name="Math")
        await session.commit()
    return level, section


async def test_set_classe_updates_profile(client, test_engine):
    headers = await _register_and_login(client, "alice@example.com")
    level, section = await _seed_level_and_section(test_engine)

    resp = await client.patch(
        "/api/v1/account/classe",
        json={"academic_level_id": level.id, "section_id": section.id},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["academic_level_id"] == level.id
    assert body["section_id"] == section.id


async def test_set_classe_clears_when_both_none(client, test_engine):
    headers = await _register_and_login(client, "alice@example.com")
    level, section = await _seed_level_and_section(test_engine)
    await client.patch(
        "/api/v1/account/classe",
        json={"academic_level_id": level.id, "section_id": section.id},
        headers=headers,
    )

    resp = await client.patch("/api/v1/account/classe", json={}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["academic_level_id"] is None
    assert body["section_id"] is None


async def test_set_classe_rejects_unknown_academic_level(client):
    headers = await _register_and_login(client, "alice@example.com")

    resp = await client.patch(
        "/api/v1/account/classe", json={"academic_level_id": "does-not-exist"}, headers=headers
    )
    assert resp.status_code == 404


async def test_set_classe_rejects_section_not_belonging_to_level(client, test_engine):
    headers = await _register_and_login(client, "alice@example.com")
    level, _section = await _seed_level_and_section(test_engine)
    sessionmaker = async_sessionmaker(bind=test_engine, expire_on_commit=False, class_=AsyncSession)
    async with sessionmaker() as session:
        repo = SqlAlchemyCurriculumRepository(session)
        other_level = await repo.create_academic_level(
            education_system_id=level.education_system_id, name="Other", order_index=1
        )
        other_section = await repo.create_section(academic_level_id=other_level.id, name="Other section")
        await session.commit()

    resp = await client.patch(
        "/api/v1/account/classe",
        json={"academic_level_id": level.id, "section_id": other_section.id},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_set_classe_requires_auth(client):
    resp = await client.patch("/api/v1/account/classe", json={})
    assert resp.status_code == 403
