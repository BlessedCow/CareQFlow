from __future__ import annotations

import sqlite3

import pytest

from authstatus_api.security.password_hashing import verify_password
from authstatus_api.security.users import (
    create_user,
    get_user_by_id,
    get_user_by_username,
    list_users,
    update_user,
    update_user_password,
)
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_test_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTHSTATUS_DATABASE_PATH", str(tmp_path / "auth_tracker.db"))
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


def test_create_user_hashes_password_and_normalizes_username():
    user = create_user(" TestUser ", "correct horse battery staple", role="Admin")

    assert user["username"] == "testuser"
    assert user["role"] == "Admin"
    assert user["is_active"] is True
    assert user["password_hash"] != "correct horse battery staple"
    assert (
        verify_password(user["password_hash"], "correct horse battery staple") is True
    )


def test_get_user_by_id_returns_user():
    created = create_user("user@example.com", "password value", role="UR")

    found = get_user_by_id(created["id"])

    assert found is not None
    assert found["id"] == created["id"]
    assert found["username"] == "user@example.com"


def test_get_user_by_username_is_case_insensitive():
    created = create_user("User@Example.com", "password value", role="UR")

    found = get_user_by_username(" USER@example.COM ")

    assert found is not None
    assert found["id"] == created["id"]


def test_list_users_returns_users_ordered_by_username():
    create_user("z-user@example.com", "password value", role="UR")
    create_user("a-user@example.com", "password value", role="Admin")

    users = list_users()

    assert [user["username"] for user in users] == [
        "a-user@example.com",
        "z-user@example.com",
    ]


def test_update_user_updates_role_and_active_status():
    user = create_user("update@example.com", "password value", role="UR")

    updated = update_user(
        user["id"],
        role="Read Only",
        is_active=False,
    )

    assert updated is not None
    assert updated["role"] == "Read Only"
    assert updated["is_active"] is False


def test_update_user_returns_existing_user_for_empty_update():
    user = create_user("empty-update@example.com", "password value", role="UR")

    updated = update_user(user["id"])

    assert updated is not None
    assert updated["id"] == user["id"]
    assert updated["role"] == "UR"


def test_update_user_returns_none_for_missing_user():
    assert update_user(999, role="UR") is None


def test_create_user_can_require_password_change():
    user = create_user(
        "temporary@example.com",
        "temporary password value",
        role="UR",
        must_change_password=True,
    )

    assert user["must_change_password"] is True


def test_update_user_password_sets_forced_change_state():
    user = create_user(
        "reset@example.com",
        "old password value",
        role="UR",
    )

    updated = update_user_password(
        user["id"],
        new_password="temporary password value",
        must_change_password=True,
    )

    assert updated is not None
    assert updated["must_change_password"] is True
    assert (
        verify_password(
            updated["password_hash"],
            "temporary password value",
        )
        is True
    )
    assert (
        verify_password(
            updated["password_hash"],
            "old password value",
        )
        is False
    )


def test_update_user_password_clears_forced_change_state():
    user = create_user(
        "change@example.com",
        "temporary password value",
        role="UR",
        must_change_password=True,
    )

    updated = update_user_password(
        user["id"],
        new_password="permanent password value",
        must_change_password=False,
    )

    assert updated is not None
    assert updated["must_change_password"] is False
    assert (
        verify_password(
            updated["password_hash"],
            "permanent password value",
        )
        is True
    )


def test_update_user_password_returns_none_for_missing_user():
    assert (
        update_user_password(
            999,
            new_password="temporary password value",
            must_change_password=True,
        )
        is None
    )


def test_create_user_rejects_duplicate_username():
    create_user("duplicate@example.com", "password value", role="UR")

    with pytest.raises(sqlite3.IntegrityError):
        create_user("DUPLICATE@example.com", "password value", role="UR")
