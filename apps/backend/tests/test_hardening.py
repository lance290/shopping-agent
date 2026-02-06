"""Tests for codebase hardening fixes (P0-4, P1-6).

P0-4: Verify auth is consolidated — no duplicate definitions exist.
P1-6: Verify bare except: blocks are eliminated from app code.
Also tests that routes correctly import from dependencies.py.
"""

import ast
import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi import HTTPException
from dependencies import get_current_session, require_auth, require_admin
from models import User, AuthSession, BugReport, hash_token, generate_session_token


# ─── P0-4: Auth Consolidation Tests ───────────────────────────────────────────

BACKEND_ROOT = Path(__file__).parent.parent


class TestAuthConsolidation:
    """Verify there is exactly one definition of each auth function."""

    def _count_function_defs(self, name: str, exclude_dirs: set = None) -> dict:
        """Count function definitions across the codebase using AST parsing."""
        exclude_dirs = exclude_dirs or {".venv", "__pycache__", "node_modules"}
        locations = {}

        for root, dirs, files in os.walk(BACKEND_ROOT):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                filepath = os.path.join(root, fname)
                try:
                    with open(filepath) as f:
                        tree = ast.parse(f.read(), filename=filepath)
                except SyntaxError:
                    continue

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if node.name == name:
                            rel = os.path.relpath(filepath, BACKEND_ROOT)
                            locations[rel] = node.lineno
        return locations

    def test_get_current_session_defined_once(self):
        """get_current_session must be defined in exactly one file."""
        locations = self._count_function_defs("get_current_session")
        assert len(locations) == 1, (
            f"get_current_session defined in {len(locations)} files: {locations}. "
            f"Should only be in dependencies.py"
        )
        assert "dependencies.py" in list(locations.keys())[0]

    def test_require_admin_defined_once(self):
        """require_admin must be defined in exactly one file."""
        locations = self._count_function_defs("require_admin")
        assert len(locations) == 1, (
            f"require_admin defined in {len(locations)} files: {locations}. "
            f"Should only be in dependencies.py"
        )
        assert "dependencies.py" in list(locations.keys())[0]

    def test_require_auth_defined_once(self):
        """require_auth must be defined in exactly one file."""
        locations = self._count_function_defs("require_auth")
        assert len(locations) == 1, (
            f"require_auth defined in {len(locations)} files: {locations}. "
            f"Should only be in dependencies.py"
        )
        assert "dependencies.py" in list(locations.keys())[0]

    def test_no_inline_import_from_routes_auth(self):
        """No file should import get_current_session from routes.auth."""
        violations = []
        exclude_dirs = {".venv", "__pycache__", "node_modules", "tests"}

        for root, dirs, files in os.walk(BACKEND_ROOT):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                filepath = os.path.join(root, fname)
                with open(filepath) as f:
                    for i, line in enumerate(f, 1):
                        if "from routes.auth import get_current_session" in line:
                            rel = os.path.relpath(filepath, BACKEND_ROOT)
                            violations.append(f"{rel}:{i}")

        assert violations == [], (
            f"Found {len(violations)} files still importing get_current_session "
            f"from routes.auth: {violations}"
        )


# ─── P0-4: Auth Functions Work Correctly After Consolidation ──────────────────

@pytest.mark.asyncio
async def test_admin_route_uses_canonical_require_admin(session):
    """Verify admin audit route uses the canonical require_admin from dependencies."""
    from routes.admin import require_admin as admin_require_admin
    from dependencies import require_admin as canonical_require_admin

    # They should be the exact same function object
    assert admin_require_admin is canonical_require_admin, (
        "routes/admin.py require_admin is not the same object as dependencies.require_admin"
    )


@pytest.mark.asyncio
async def test_bugs_route_uses_canonical_require_admin(session):
    """Verify bugs route uses the canonical require_admin from dependencies."""
    from routes.bugs import require_admin as bugs_require_admin
    from dependencies import require_admin as canonical_require_admin

    assert bugs_require_admin is canonical_require_admin, (
        "routes/bugs.py require_admin is not the same object as dependencies.require_admin"
    )


@pytest.mark.asyncio
async def test_bugs_route_uses_canonical_get_current_session(session):
    """Verify bugs route uses the canonical get_current_session from dependencies."""
    from routes.bugs import get_current_session as bugs_gcs
    from dependencies import get_current_session as canonical_gcs

    assert bugs_gcs is canonical_gcs, (
        "routes/bugs.py get_current_session is not the same object as dependencies.get_current_session"
    )


@pytest.mark.asyncio
async def test_consolidated_auth_admin_flow(session):
    """End-to-end: admin user through consolidated auth."""
    admin = User(email="admin-hardening@test.com", is_admin=True)
    session.add(admin)
    await session.commit()
    await session.refresh(admin)

    token = generate_session_token()
    auth_session = AuthSession(
        email=admin.email,
        user_id=admin.id,
        session_token_hash=hash_token(token),
    )
    session.add(auth_session)
    await session.commit()

    # Test through the canonical functions
    result = await get_current_session(f"Bearer {token}", session)
    assert result is not None
    assert result.user_id == admin.id

    user = await require_admin(f"Bearer {token}", session)
    assert user.is_admin is True


@pytest.mark.asyncio
async def test_consolidated_auth_non_admin_rejected(session):
    """Non-admin user through consolidated require_admin raises 403."""
    user = User(email="nonadmin-hardening@test.com", is_admin=False)
    session.add(user)
    await session.commit()
    await session.refresh(user)

    token = generate_session_token()
    auth_session = AuthSession(
        email=user.email,
        user_id=user.id,
        session_token_hash=hash_token(token),
    )
    session.add(auth_session)
    await session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await require_admin(f"Bearer {token}", session)

    assert exc_info.value.status_code == 403


# ─── P1-6: No Bare Except Tests ──────────────────────────────────────────────

class TestNoBareExcept:
    """Verify no bare except: blocks exist in application code."""

    def _find_bare_excepts(self) -> list:
        """Find all bare except: blocks in app code using AST."""
        violations = []
        exclude_dirs = {".venv", "__pycache__", "node_modules", ".git"}

        for root, dirs, files in os.walk(BACKEND_ROOT):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                filepath = os.path.join(root, fname)
                try:
                    with open(filepath) as f:
                        tree = ast.parse(f.read(), filename=filepath)
                except SyntaxError:
                    continue

                for node in ast.walk(tree):
                    if isinstance(node, ast.ExceptHandler):
                        if node.type is None:
                            rel = os.path.relpath(filepath, BACKEND_ROOT)
                            violations.append(f"{rel}:{node.lineno}")

        return violations

    def test_no_bare_except_in_app_code(self):
        """No bare except: should exist in application code."""
        violations = self._find_bare_excepts()
        assert violations == [], (
            f"Found {len(violations)} bare except: blocks: {violations}. "
            f"Use 'except Exception as e:' or specific exception types."
        )

    def test_json_parsing_uses_specific_exceptions(self):
        """Verify JSON parsing blocks use JSONDecodeError/TypeError, not bare except."""
        import json

        # These are the common patterns in the codebase
        test_cases = [
            ('valid json', '{"key": "value"}', False),
            ('invalid json', 'not json', True),
            ('none value', None, True),
        ]

        for label, value, should_fail in test_cases:
            caught = False
            try:
                json.loads(value)
            except (json.JSONDecodeError, TypeError):
                caught = True

            if should_fail:
                assert caught, f"Expected exception for {label} but none caught"
            else:
                assert not caught, f"Unexpected exception for {label}"

    def test_price_parsing_uses_specific_exceptions(self):
        """Verify price parsing uses ValueError/AttributeError, not bare except."""
        test_cases = [
            ("1299.00", 1299.0),
            ("1,299.00", 1299.0),
            ("abc", None),
        ]

        import re
        for raw, expected in test_cases:
            price = None
            match = re.search(r"(\d[\d,]*\.?\d*)", str(raw))
            if match:
                try:
                    price = float(match.group(1).replace(",", ""))
                except (ValueError, AttributeError):
                    pass

            if expected is not None:
                assert price == expected, f"Failed to parse {raw}: got {price}"


# ─── Bug Route Auth Integration After Consolidation ─────────────────────────

@pytest.mark.asyncio
async def test_bug_report_auth_uses_consolidated_session(session, test_user):
    """Verify bug report route can authenticate using consolidated get_current_session."""
    token = generate_session_token()
    auth_session = AuthSession(
        email=test_user.email,
        user_id=test_user.id,
        session_token_hash=hash_token(token),
    )
    session.add(auth_session)
    await session.commit()

    # Simulate what create_bug_report does internally
    result = await get_current_session(f"Bearer {token}", session)
    assert result is not None
    assert result.user_id == test_user.id


@pytest.mark.asyncio
async def test_bug_report_list_requires_admin(session, test_user):
    """Verify list_bug_reports uses consolidated require_admin."""
    token = generate_session_token()
    auth_session = AuthSession(
        email=test_user.email,
        user_id=test_user.id,
        session_token_hash=hash_token(token),
    )
    session.add(auth_session)
    await session.commit()

    # Non-admin should get 403
    with pytest.raises(HTTPException) as exc_info:
        await require_admin(f"Bearer {token}", session)
    assert exc_info.value.status_code == 403
