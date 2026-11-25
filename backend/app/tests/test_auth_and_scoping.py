"""Tests for Supabase Auth token validation and user-scoped notebook access."""

from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from app.api.dependencies.auth import AuthenticatedUser
from app.core.config import settings
from app.main import app
from app.repositories.notebook_repository import NotebookRepository
from app.services.notebook_service import get_notebook_repository


@pytest.fixture()
def auth_client(tmp_path):
    repo = NotebookRepository(tmp_path / "auth_notebooks.db")
    app.dependency_overrides[get_notebook_repository] = lambda: repo
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_auth_me_guest_vs_authenticated(auth_client, monkeypatch):
    guest_resp = auth_client.get("/api/v1/auth/me")
    assert guest_resp.status_code == 200
    assert guest_resp.json() == {"authenticated": False, "user": None}

    monkeypatch.setattr(settings, "auth_required", True)
    denied = auth_client.get("/api/v1/auth/me")
    assert denied.status_code == 401
    assert denied.json()["error"]["code"] == "UNAUTHORIZED"

    with patch(
        "app.api.dependencies.auth.verify_supabase_token",
        return_value=AuthenticatedUser(id="user-1", email="alice@example.com"),
    ):
        ok = auth_client.get("/api/v1/auth/me", headers={"Authorization": "Bearer valid-jwt"})
        assert ok.status_code == 200
        assert ok.json() == {
            "authenticated": True,
            "user": {"id": "user-1", "email": "alice@example.com"},
        }


def test_user_scoped_notebook_isolation(auth_client):
    with patch(
        "app.api.dependencies.auth.verify_supabase_token",
        return_value=AuthenticatedUser(id="user-1", email="alice@example.com"),
    ):
        created = auth_client.post(
            "/api/v1/notebooks",
            headers={"Authorization": "Bearer alice-jwt"},
            json={"title": "Alice Private Notebook", "cells": []},
        )
        assert created.status_code == 201
        nb_id = created.json()["id"]

        listed_alice = auth_client.get("/api/v1/notebooks", headers={"Authorization": "Bearer alice-jwt"})
        assert len(listed_alice.json()) == 1

    # Bob cannot access or list Alice's private notebook
    with patch(
        "app.api.dependencies.auth.verify_supabase_token",
        return_value=AuthenticatedUser(id="user-2", email="bob@example.com"),
    ):
        listed_bob = auth_client.get("/api/v1/notebooks", headers={"Authorization": "Bearer bob-jwt"})
        assert listed_bob.json() == []

        forbidden = auth_client.get(f"/api/v1/notebooks/{nb_id}", headers={"Authorization": "Bearer bob-jwt"})
        assert forbidden.status_code == 403
        assert forbidden.json()["error"]["code"] == "FORBIDDEN"

    # Unauthenticated guest list must NOT include Alice's owned notebook
    listed_guest = auth_client.get("/api/v1/notebooks")
    assert listed_guest.status_code == 200
    assert listed_guest.json() == []
