from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
COMPOSE_PATH = ROOT_DIR / "docker-compose.prod.yml"
ENV_EXAMPLE_PATH = ROOT_DIR / ".env.production.example"


def read_production_compose() -> str:
    return COMPOSE_PATH.read_text()


def service_block(compose_text: str, service_name: str) -> str:
    lines = compose_text.splitlines()
    marker = f"  {service_name}:"
    start = next(index for index, line in enumerate(lines) if line == marker)
    block_lines: list[str] = []

    for line in lines[start + 1:]:
        if line.startswith("  ") and not line.startswith("    "):
            break

        if line and not line.startswith(" "):
            break

        block_lines.append(line)

    return "\n".join(block_lines)


def test_production_compose_does_not_publish_internal_service_ports():
    compose_text = read_production_compose()

    for service_name in ["dashboard", "api", "django-ops", "db"]:
        assert "\n    ports:\n" not in service_block(compose_text, service_name)

    assert "internal: true" in compose_text


def test_production_compose_uses_production_application_servers():
    compose_text = read_production_compose()

    assert "gunicorn src.api.main:app" in service_block(compose_text, "api")
    assert "uvicorn.workers.UvicornWorker" in service_block(compose_text, "api")
    assert "gunicorn django_ops.config.wsgi:application" in service_block(
        compose_text,
        "django-ops",
    )
    assert "runserver" not in compose_text
    assert "--reload" not in compose_text


def test_production_compose_has_health_checks_and_persistent_database_volume():
    compose_text = read_production_compose()

    for service_name in ["dashboard", "api", "django-ops", "db"]:
        assert "healthcheck:" in service_block(compose_text, service_name)

    assert "postgres_data:/var/lib/postgresql/data" in service_block(
        compose_text,
        "db",
    )


def test_production_env_example_declares_required_runtime_settings():
    env_text = ENV_EXAMPLE_PATH.read_text()

    required_keys = [
        "POSTGRES_DB=",
        "POSTGRES_USER=",
        "POSTGRES_PASSWORD=",
        "DATABASE_URL=",
        "JOBLENS_CORS_ORIGINS=",
        "DJANGO_SECRET_KEY=",
        "DJANGO_ALLOWED_HOSTS=",
        "DJANGO_CSRF_TRUSTED_ORIGINS=",
    ]

    for key in required_keys:
        assert key in env_text

    assert "localhost:5432" not in env_text
    assert "replace-with-a-long-random" in env_text
