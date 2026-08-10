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


async def _create_subject(client, headers, name="Physics"):
    resp = await client.post("/api/v1/subjects", json={"name": name}, headers=headers)
    return resp.json()["id"]


_SAMPLE_TEXT = ("Ohm's law relates voltage, current, and resistance in a circuit. " * 20).encode("utf-8")


async def test_upload_document_ingests_synchronously_in_tests(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)

    upload_resp = await client.post(
        f"/api/v1/subjects/{subject_id}/documents",
        headers=headers,
        files={"file": ("ohms_law.txt", _SAMPLE_TEXT, "text/plain")},
    )
    assert upload_resp.status_code == 201
    document = upload_resp.json()
    assert document["original_filename"] == "ohms_law.txt"
    assert document["file_type"] == ".txt"

    # httpx's ASGITransport awaits Starlette's BackgroundTasks as part of the
    # same request/response cycle, so ingestion has already run by the time
    # the upload call returns — no polling needed here.
    status_resp = await client.get(f"/api/v1/documents/{document['id']}", headers=headers)
    body = status_resp.json()
    assert body["status"] == "ready"
    assert body["page_count"] is not None
    assert body["error_message"] is None
    # The test fixture's fake LLM response has no "document_type" key, so
    # classification defensively falls back to "other" rather than raising.
    assert body["document_type"] == "other"
    assert body["chapter_id"] is None
    assert body["classified_at"] is not None


async def test_upload_image_ingests_via_vision_fallback(client):
    """Standalone images have no extractable text at all — the entire
    pipeline (upload -> ingestion -> extraction -> chunking -> concept
    tagging) has to go through the vision-model path end to end."""
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)

    upload_resp = await client.post(
        f"/api/v1/subjects/{subject_id}/documents",
        headers=headers,
        files={"file": ("diagram.png", b"\x89PNG\r\n\x1a\nfake-but-not-empty", "image/png")},
    )
    assert upload_resp.status_code == 201
    document_id = upload_resp.json()["id"]

    status_resp = await client.get(f"/api/v1/documents/{document_id}", headers=headers)
    body = status_resp.json()
    assert body["status"] == "ready"
    assert body["error_message"] is None


async def test_upload_empty_document_is_marked_failed_not_ready(client):
    """A file that extracts to zero usable text (empty, scanned-with-no-vision-
    fallback, etc.) must not be left silently marked "ready" with no chunks —
    that used to make every downstream feature (quiz/exam/summary/chat) fail
    with a confusing "isn't ready yet (status: ready)" error. Ingestion should
    instead mark it "failed" with an honest error_message."""
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)

    upload_resp = await client.post(
        f"/api/v1/subjects/{subject_id}/documents",
        headers=headers,
        files={"file": ("blank.txt", b"   \n\n  ", "text/plain")},
    )
    assert upload_resp.status_code == 201
    document_id = upload_resp.json()["id"]

    status_resp = await client.get(f"/api/v1/documents/{document_id}", headers=headers)
    body = status_resp.json()
    assert body["status"] == "failed"
    assert body["error_message"]


async def test_upload_rejects_unsupported_file_type(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)

    resp = await client.post(
        f"/api/v1/subjects/{subject_id}/documents",
        headers=headers,
        files={"file": ("clip.mp4", b"not really a video", "video/mp4")},
    )
    assert resp.status_code == 415


async def test_upload_rejects_other_users_subject(client):
    alice_headers = await _register_and_login(client, "alice@example.com")
    bob_headers = await _register_and_login(client, "bob@example.com")
    subject_id = await _create_subject(client, alice_headers)

    resp = await client.post(
        f"/api/v1/subjects/{subject_id}/documents",
        headers=bob_headers,
        files={"file": ("notes.txt", b"some text", "text/plain")},
    )
    assert resp.status_code == 404


async def test_list_documents_for_subject(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)
    await client.post(
        f"/api/v1/subjects/{subject_id}/documents",
        headers=headers,
        files={"file": ("notes.txt", _SAMPLE_TEXT, "text/plain")},
    )

    list_resp = await client.get(f"/api/v1/subjects/{subject_id}/documents", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


async def test_document_access_isolated_between_users(client):
    alice_headers = await _register_and_login(client, "alice@example.com")
    bob_headers = await _register_and_login(client, "bob@example.com")
    subject_id = await _create_subject(client, alice_headers)
    upload_resp = await client.post(
        f"/api/v1/subjects/{subject_id}/documents",
        headers=alice_headers,
        files={"file": ("notes.txt", _SAMPLE_TEXT, "text/plain")},
    )
    document_id = upload_resp.json()["id"]

    bob_resp = await client.get(f"/api/v1/documents/{document_id}", headers=bob_headers)
    assert bob_resp.status_code == 404


async def test_get_document_content_returns_raw_bytes(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)
    upload_resp = await client.post(
        f"/api/v1/subjects/{subject_id}/documents",
        headers=headers,
        files={"file": ("notes.txt", _SAMPLE_TEXT, "text/plain")},
    )
    document_id = upload_resp.json()["id"]

    resp = await client.get(f"/api/v1/documents/{document_id}/content", headers=headers)
    assert resp.status_code == 200
    assert resp.content == _SAMPLE_TEXT
    assert resp.headers["content-type"].startswith("text/plain")
    assert 'filename="notes.txt"' in resp.headers["content-disposition"]


async def test_get_document_content_accepts_token_query_param(client):
    # A plain browser navigation (window.open, <a href>) can't attach an
    # Authorization header, so this route also accepts the access token via
    # ?token= — see get_current_user_from_header_or_query.
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)
    upload_resp = await client.post(
        f"/api/v1/subjects/{subject_id}/documents",
        headers=headers,
        files={"file": ("notes.txt", _SAMPLE_TEXT, "text/plain")},
    )
    document_id = upload_resp.json()["id"]
    token = headers["Authorization"].removeprefix("Bearer ")

    resp = await client.get(f"/api/v1/documents/{document_id}/content", params={"token": token})
    assert resp.status_code == 200
    assert resp.content == _SAMPLE_TEXT


async def test_get_document_content_requires_auth_header_or_token(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)
    upload_resp = await client.post(
        f"/api/v1/subjects/{subject_id}/documents",
        headers=headers,
        files={"file": ("notes.txt", _SAMPLE_TEXT, "text/plain")},
    )
    document_id = upload_resp.json()["id"]

    resp = await client.get(f"/api/v1/documents/{document_id}/content")
    assert resp.status_code == 401


async def test_get_document_content_requires_ownership(client):
    alice_headers = await _register_and_login(client, "alice@example.com")
    bob_headers = await _register_and_login(client, "bob@example.com")
    subject_id = await _create_subject(client, alice_headers)
    upload_resp = await client.post(
        f"/api/v1/subjects/{subject_id}/documents",
        headers=alice_headers,
        files={"file": ("notes.txt", _SAMPLE_TEXT, "text/plain")},
    )
    document_id = upload_resp.json()["id"]

    resp = await client.get(f"/api/v1/documents/{document_id}/content", headers=bob_headers)
    assert resp.status_code == 404


async def test_delete_document(client):
    headers = await _register_and_login(client, "alice@example.com")
    subject_id = await _create_subject(client, headers)
    upload_resp = await client.post(
        f"/api/v1/subjects/{subject_id}/documents",
        headers=headers,
        files={"file": ("notes.txt", _SAMPLE_TEXT, "text/plain")},
    )
    document_id = upload_resp.json()["id"]

    delete_resp = await client.delete(f"/api/v1/documents/{document_id}", headers=headers)
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/documents/{document_id}", headers=headers)
    assert get_resp.status_code == 404
