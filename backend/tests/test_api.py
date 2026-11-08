import os

os.environ["DATABASE_URL"] = "sqlite:///./test_voicepilot.db"
os.environ["LLM_API_KEY"] = ""

import pytest
from fastapi.testclient import TestClient

from app.database.session import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


client = TestClient(app)
STRONG = "Str0ng!Pass"


def register(email="a@example.com"):
    return client.post("/api/auth/register", json={"full_name": "Ada Lovelace", "email": email, "password": STRONG})


def auth_header(response):
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_register_login_me_refresh_logout():
    reg = register()
    assert reg.status_code == 201
    login = client.post("/api/auth/login", json={"email": "a@example.com", "password": STRONG})
    assert login.status_code == 200
    assert client.get("/api/auth/me", headers=auth_header(login)).json()["email"] == "a@example.com"
    old = login.json()["refresh_token"]
    rotated = client.post("/api/auth/refresh", json={"refresh_token": old})
    assert rotated.status_code == 200
    assert client.post("/api/auth/refresh", json={"refresh_token": old}).status_code == 401
    assert client.post("/api/auth/logout", json={"refresh_token": rotated.json()["refresh_token"]}).status_code == 204


def test_weak_password_and_duplicate_rejected():
    bad = client.post("/api/auth/register", json={"full_name": "Bob", "email": "b@example.com", "password": "weakpass"})
    assert bad.status_code == 422
    register()
    assert register().status_code == 409


def test_lockout_after_failed_attempts():
    register()
    for _ in range(5):
        assert client.post("/api/auth/login", json={"email": "a@example.com", "password": "Wrong!pass1"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "a@example.com", "password": STRONG}).status_code == 429


def test_protected_and_admin_routes():
    assert client.get("/api/conversations").status_code == 401
    headers = auth_header(register())
    assert client.get("/api/admin/users", headers=headers).status_code == 403


def test_oauth_not_configured():
    assert client.get("/api/auth/providers").json() == {"google": False, "github": False, "microsoft": False}
    assert client.get("/api/auth/google", follow_redirects=False).status_code == 503


def test_chat_tools_and_conversations():
    headers = auth_header(register())
    reply = client.post("/api/agent/chat", json={"message": "calculate 12*(3+4)"}, headers=headers)
    assert reply.status_code == 200
    assert "84" in reply.json()["reply"]["content"]
    conversation_id = reply.json()["conversation_id"]
    detail = client.get(f"/api/conversations/{conversation_id}", headers=headers).json()
    assert len(detail["messages"]) == 2
    assert client.post("/api/tools/calculator", json={"expression": "__import__('os')"}, headers=headers).status_code == 400
    assert client.delete(f"/api/conversations/{conversation_id}", headers=headers).status_code == 204


def test_rag_upload_and_answer():
    headers = auth_header(register())
    text = b"Our refund policy allows returns within 30 days of purchase. Shipping takes five business days."
    upload = client.post("/api/documents/upload", files={"file": ("policy.txt", text, "text/plain")}, headers=headers)
    assert upload.status_code == 201
    assert upload.json()["status"] == "completed"
    reply = client.post("/api/agent/chat", json={"message": "What is the refund policy for returns?"}, headers=headers).json()
    assert "policy.txt" in reply["reply"]["sources"]
    bad = client.post("/api/documents/upload", files={"file": ("x.exe", b"MZ", "application/octet-stream")}, headers=headers)
    assert bad.status_code == 400


def test_isolation_between_users():
    first = auth_header(register("one@example.com"))
    second = auth_header(register("two@example.com"))
    conv = client.post("/api/conversations", headers=first).json()
    assert client.get(f"/api/conversations/{conv['id']}", headers=second).status_code == 404

