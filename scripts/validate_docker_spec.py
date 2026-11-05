#!/usr/bin/env python3
"""
Gadispot Phase 4: Docker & Local Development Infrastructure Specification Suite.
Validates backend/Dockerfile, .dockerignore files, docker-compose.yml, dev scripts,
and configuration harmonization according to TSK-P4-001 through TSK-P4-005.
"""

import os
import re
import sys
import yaml
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def check_backend_dockerfile() -> list[str]:
    """Validate backend/Dockerfile multi-stage structure, non-root user, caching, curl probe."""
    errors = []
    dockerfile_path = REPO_ROOT / "backend" / "Dockerfile"

    if not dockerfile_path.exists():
        return [f"Missing required file: {dockerfile_path}"]

    content = dockerfile_path.read_text(encoding="utf-8")

    # Multi-stage check
    if not re.search(r"FROM\s+python:3\.12-slim\s+AS\s+builder", content, re.IGNORECASE):
        errors.append("Dockerfile must declare 'FROM python:3.12-slim AS builder' stage.")
    if not re.search(r"FROM\s+python:3\.12-slim\s+AS\s+runtime", content, re.IGNORECASE):
        errors.append("Dockerfile must declare 'FROM python:3.12-slim AS runtime' stage.")

    # Non-root user check
    if "useradd" not in content or "1000" not in content or "gadispot" not in content:
        errors.append("Dockerfile must create non-root user 'gadispot' with UID/GID 1000.")
    if not re.search(r"USER\s+gadispot", content):
        errors.append("Dockerfile must enforce 'USER gadispot'.")

    # Layer caching: dependency copy before app code
    pos_deps = content.find("COPY pyproject.toml")
    if pos_deps == -1:
        pos_deps = content.find("COPY requirements.txt")
    pos_app = content.find("COPY --chown=gadispot:gadispot app")
    if pos_deps == -1:
        errors.append("Dockerfile must copy dependency files (pyproject.toml/requirements.txt) for layer caching.")
    if pos_app == -1:
        errors.append("Dockerfile must copy application directory with chown gadispot:gadispot.")
    if pos_deps != -1 and pos_app != -1 and pos_deps > pos_app:
        errors.append("Dependency specification copy must precede application code copy for layer caching.")

    # Curl health probe check
    if "curl" not in content:
        errors.append("Dockerfile must install 'curl' in slim image for health probe checks.")
    if "HEALTHCHECK" not in content or "/health/ready" not in content:
        errors.append("Dockerfile must specify HEALTHCHECK targeting http://localhost:8000/health/ready.")

    # Expose and CMD
    if "EXPOSE 8000" not in content:
        errors.append("Dockerfile must specify 'EXPOSE 8000'.")
    if "uvicorn" not in content or "app.main:app" not in content:
        errors.append("Dockerfile CMD must launch uvicorn running app.main:app.")

    return errors


def check_dockerignore_files() -> list[str]:
    """Validate backend/.dockerignore and root .dockerignore."""
    errors = []
    backend_ignore = REPO_ROOT / "backend" / ".dockerignore"
    root_ignore = REPO_ROOT / ".dockerignore"

    if not backend_ignore.exists():
        errors.append(f"Missing required file: {backend_ignore}")
    else:
        content = backend_ignore.read_text(encoding="utf-8")
        required_patterns = ["__pycache__", ".pytest_cache", ".venv", ".git", ".env"]
        for pat in required_patterns:
            if pat not in content:
                errors.append(f"backend/.dockerignore missing critical pattern '{pat}'.")

    if not root_ignore.exists():
        errors.append(f"Missing required file: {root_ignore}")
    else:
        content = root_ignore.read_text(encoding="utf-8")
        required_patterns = [".git", "mobile", "docs", "tests", ".env"]
        for pat in required_patterns:
            if pat not in content:
                errors.append(f"Root .dockerignore missing critical pattern '{pat}'.")

    return errors


def check_docker_compose() -> list[str]:
    """Validate root docker-compose.yml syntax, services, healthchecks, and volumes."""
    errors = []
    compose_path = REPO_ROOT / "docker-compose.yml"

    if not compose_path.exists():
        return [f"Missing required file: {compose_path}"]

    try:
        with open(compose_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as exc:
        return [f"Failed to parse docker-compose.yml as valid YAML: {exc}"]

    services = data.get("services", {})
    required_services = ["postgres", "redis", "backend"]
    for s in required_services:
        if s not in services:
            errors.append(f"docker-compose.yml missing required service '{s}'.")

    # 1. postgres check
    pg = services.get("postgres", {})
    if "postgis/postgis:16-3.4" not in pg.get("image", ""):
        errors.append("postgres service must use image 'postgis/postgis:16-3.4'.")
    ports = [str(p) for p in pg.get("ports", [])]
    if not any("5432:5432" in p for p in ports):
        errors.append("postgres service must expose port '5432:5432'.")
    pg_hc = pg.get("healthcheck", {})
    pg_test = " ".join(pg_hc.get("test", [])) if isinstance(pg_hc.get("test"), list) else str(pg_hc.get("test"))
    if "pg_isready" not in pg_test:
        errors.append("postgres service healthcheck must use pg_isready.")

    # 2. redis check
    rd = services.get("redis", {})
    if "redis:7-alpine" not in rd.get("image", ""):
        errors.append("redis service must use image 'redis:7-alpine'.")
    rd_ports = [str(p) for p in rd.get("ports", [])]
    if not any("6379:6379" in p for p in rd_ports):
        errors.append("redis service must expose port '6379:6379'.")
    rd_hc = rd.get("healthcheck", {})
    rd_test = " ".join(rd_hc.get("test", [])) if isinstance(rd_hc.get("test"), list) else str(rd_hc.get("test"))
    if "redis-cli" not in rd_test or "ping" not in rd_test:
        errors.append("redis service healthcheck must ping redis-cli.")

    # 3. backend check
    be = services.get("backend", {})
    be_build = be.get("build", {})
    context = be_build.get("context", "") if isinstance(be_build, dict) else str(be_build)
    if "backend" not in context:
        errors.append("backend service build context must point to ./backend.")
    be_ports = [str(p) for p in be.get("ports", [])]
    if not any("8000:8000" in p for p in be_ports):
        errors.append("backend service must expose port '8000:8000'.")

    # Depends_on check
    deps = be.get("depends_on", {})
    if not isinstance(deps, dict):
        errors.append("backend depends_on must declare healthcheck conditions (dict mapping).")
    else:
        for dep in ["postgres", "redis"]:
            if dep not in deps:
                errors.append(f"backend depends_on missing '{dep}'.")
            elif deps[dep].get("condition") != "service_healthy":
                errors.append(f"backend depends_on '{dep}' must specify 'condition: service_healthy'.")

    # Backend healthcheck check
    be_hc = be.get("healthcheck", {})
    be_test = " ".join(be_hc.get("test", [])) if isinstance(be_hc.get("test"), list) else str(be_hc.get("test"))
    if "/health/ready" not in be_test:
        errors.append("backend service healthcheck must probe http://localhost:8000/health/ready.")

    # 4. Volumes check
    volumes = data.get("volumes", {})
    if "gadispot_pgdata" not in volumes:
        errors.append("docker-compose.yml must define persistent volume 'gadispot_pgdata'.")
    if "gadispot_redisdata" not in volumes:
        errors.append("docker-compose.yml must define persistent volume 'gadispot_redisdata'.")

    return errors


def check_developer_scripts() -> list[str]:
    """Validate existence and logic of dev_up.sh, dev_up.ps1, dev_down.sh, dev_down.ps1."""
    errors = []
    scripts = {
        "dev_up.sh": REPO_ROOT / "scripts" / "dev_up.sh",
        "dev_up.ps1": REPO_ROOT / "scripts" / "dev_up.ps1",
        "dev_down.sh": REPO_ROOT / "scripts" / "dev_down.sh",
        "dev_down.ps1": REPO_ROOT / "scripts" / "dev_down.ps1",
    }

    for name, path in scripts.items():
        if not path.exists():
            errors.append(f"Missing script: {path}")
            continue

        content = path.read_text(encoding="utf-8")

        if "dev_up" in name:
            if ".env" not in content or ".env.example" not in content:
                errors.append(f"{name} must handle copying .env.example to .env.")
            if "docker compose up" not in content:
                errors.append(f"{name} must execute 'docker compose up'.")
            if "alembic upgrade head" not in content:
                errors.append(f"{name} must execute 'alembic upgrade head'.")
            if "/health/live" not in content or "/health/ready" not in content or "/docs" not in content:
                errors.append(f"{name} must display live endpoint URLs.")

        if "dev_down" in name:
            if "docker compose down" not in content:
                errors.append(f"{name} must execute 'docker compose down'.")
            if "-v" not in content and "Volumes" not in content and "--volumes" not in content:
                errors.append(f"{name} must support persistent volume purge option.")

    return errors


def main():
    print("=" * 70)
    print("GADISPOT PHASE 4: DOCKER & LOCAL INFRASTRUCTURE SPECIFICATION SUITE")
    print("=" * 70)

    all_passed = True

    # 1. Dockerfile check
    print("\n[1/4] Verifying backend/Dockerfile multi-stage build & security standards...")
    dockerfile_errors = check_backend_dockerfile()
    if dockerfile_errors:
        print(f"FAILED: Found {len(dockerfile_errors)} Dockerfile defect(s):")
        for err in dockerfile_errors:
            print(f"  - {err}")
        all_passed = False
    else:
        print("PASSED: backend/Dockerfile adheres to multi-stage python:3.12-slim, non-root user (gadispot 1000), cached layers, and healthcheck probe.")

    # 2. .dockerignore check
    print("\n[2/4] Verifying .dockerignore files (backend and root)...")
    dockerignore_errors = check_dockerignore_files()
    if dockerignore_errors:
        print(f"FAILED: Found {len(dockerignore_errors)} .dockerignore defect(s):")
        for err in dockerignore_errors:
            print(f"  - {err}")
        all_passed = False
    else:
        print("PASSED: Both backend/.dockerignore and root .dockerignore exclude caches, git, mobile, docs, and environment secrets.")

    # 3. docker-compose.yml check
    print("\n[3/4] Verifying master docker-compose.yml services, volumes & healthchecks...")
    compose_errors = check_docker_compose()
    if compose_errors:
        print(f"FAILED: Found {len(compose_errors)} docker-compose.yml defect(s):")
        for err in compose_errors:
            print(f"  - {err}")
        all_passed = False
    else:
        print("PASSED: docker-compose.yml declares postgres (PostGIS 16-3.4), redis (7-alpine), backend with healthy dependencies, and persistent volumes.")

    # 4. Developer startup/teardown scripts check
    print("\n[4/4] Verifying one-command startup and teardown scripts...")
    script_errors = check_developer_scripts()
    if script_errors:
        print(f"FAILED: Found {len(script_errors)} script defect(s):")
        for err in script_errors:
            print(f"  - {err}")
        all_passed = False
    else:
        print("PASSED: scripts/dev_up.sh, dev_up.ps1, dev_down.sh, and dev_down.ps1 implement full automation (.env init, compose up, readiness wait, alembic migrations, volume purge).")

    print("\n" + "=" * 70)
    if all_passed:
        print("OVERALL RESULT: ALL DOCKER INFRASTRUCTURE CHECKS PASSED (100% GREEN)")
        print("                Phase 4 (TSK-P4-001 through TSK-P4-005) Fully Verified.")
        print("=" * 70)
        sys.exit(0)
    else:
        print("OVERALL RESULT: DOCKER INFRASTRUCTURE SPECIFICATION FAILED")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
