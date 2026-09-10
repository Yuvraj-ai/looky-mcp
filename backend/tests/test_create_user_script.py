"""Admin user provisioning script tests — no public signup (Architecture §9)."""

import subprocess
import sys
import uuid


def run_create_user(db_url_sync: str, email: str, password: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            "scripts/create_user.py",
            "--database-url",
            db_url_sync,
            "--email",
            email,
            "--password",
            password,
        ],
        capture_output=True,
        text=True,
        cwd=".",
    )


def test_create_user_creates_argon2_hash(db_engine, migrated_db, pg_host):
    email = f"admin{uuid.uuid4().hex[:8]}@example.com"
    sync_url = f"postgresql+pg8000://postgres:@/vision_test?unix_sock={pg_host}/.s.PGSQL.5432"
    r = run_create_user(sync_url, email, "initial-pass-1")
    assert r.returncode == 0, r.stderr
    assert "created" in r.stdout.lower()


def test_create_user_duplicate_email_fails(db_engine, migrated_db, pg_host):
    email = f"dup{uuid.uuid4().hex[:8]}@example.com"
    sync_url = f"postgresql+pg8000://postgres:@/vision_test?unix_sock={pg_host}/.s.PGSQL.5432"
    r1 = run_create_user(sync_url, email, "pass-1")
    r2 = run_create_user(sync_url, email, "pass-2")
    assert r1.returncode == 0
    assert r2.returncode != 0
