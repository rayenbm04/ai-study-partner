"""These endpoints are deliberately public (no auth) — see
app/api/v1/routes/schools.py's docstring for why: a student needs to search
for (or add) their school during the registration form itself, before an
account/token exists."""


async def test_create_and_search_schools(client):
    await client.post("/api/v1/schools", json={"name": "Lycee Victor Hugo", "country": "FR", "city": "Paris"})
    await client.post("/api/v1/schools", json={"name": "Lycee Carnot", "country": "FR", "city": "Paris"})

    resp = await client.get("/api/v1/schools", params={"q": "victor"})
    assert resp.status_code == 200
    names = [s["name"] for s in resp.json()]
    assert names == ["Lycee Victor Hugo"]


async def test_search_without_query_returns_all(client):
    await client.post("/api/v1/schools", json={"name": "Lycee Victor Hugo", "country": "FR", "city": "Paris"})

    resp = await client.get("/api/v1/schools")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_get_school_by_id(client):
    create_resp = await client.post(
        "/api/v1/schools", json={"name": "Lycee Victor Hugo", "country": "FR", "city": "Paris"}
    )
    school_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/schools/{school_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Lycee Victor Hugo"


async def test_get_unknown_school_404s(client):
    resp = await client.get("/api/v1/schools/does-not-exist")
    assert resp.status_code == 404


async def test_create_and_list_school_classes(client):
    create_resp = await client.post(
        "/api/v1/schools", json={"name": "Lycee Victor Hugo", "country": "FR", "city": "Paris"}
    )
    school_id = create_resp.json()["id"]

    class_resp = await client.post(
        f"/api/v1/schools/{school_id}/classes", json={"level": "Seconde", "label": "Seconde A"}
    )
    assert class_resp.status_code == 201
    assert class_resp.json()["school_id"] == school_id

    list_resp = await client.get(f"/api/v1/schools/{school_id}/classes")
    assert list_resp.status_code == 200
    assert [c["label"] for c in list_resp.json()] == ["Seconde A"]


async def test_list_classes_for_unknown_school_404s(client):
    resp = await client.get("/api/v1/schools/does-not-exist/classes")
    assert resp.status_code == 404
