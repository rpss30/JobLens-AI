from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
COMPOSE_PATH = ROOT_DIR / "docker-compose.prod.yml"
ENV_EXAMPLE_PATH = ROOT_DIR / ".env.production.example"
CADDYFILE_PATH = ROOT_DIR / "deploy" / "caddy" / "Caddyfile"
FRONTEND_DIR = ROOT_DIR / "frontend"


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

    for service_name in ["frontend", "api", "django-ops", "db"]:
        assert "\n    ports:\n" not in service_block(compose_text, service_name)

    caddy_block = service_block(compose_text, "caddy")

    assert '"80:80"' in caddy_block
    assert '"443:443"' in caddy_block
    assert "internal: true" in compose_text


def test_production_compose_uses_production_application_servers():
    compose_text = read_production_compose()

    assert "gunicorn src.api.main:app" in service_block(compose_text, "api")
    assert "uvicorn.workers.UvicornWorker" in service_block(compose_text, "api")
    assert "gunicorn django_ops.config.wsgi:application" in service_block(
        compose_text,
        "django-ops",
    )
    frontend_block = service_block(compose_text, "frontend")

    assert "context: ./frontend" in frontend_block
    assert "JOBLENS_API_URL: ${JOBLENS_API_URL:-http://api:8000}" in frontend_block

    assert "runserver" not in compose_text
    assert "--reload" not in compose_text
    assert "npm run dev" not in compose_text
    assert "streamlit run" not in compose_text


def test_production_compose_has_health_checks_and_persistent_database_volume():
    compose_text = read_production_compose()

    for service_name in ["caddy", "frontend", "api", "django-ops", "db"]:
        assert "healthcheck:" in service_block(compose_text, service_name)

    assert "postgres_data:/var/lib/postgresql/data" in service_block(
        compose_text,
        "db",
    )
    assert "caddy_data:/data" in service_block(compose_text, "caddy")

    # Django validates the Host header, so its healthcheck sends the real domain.
    # Probing localhost instead would need loopback names in
    # DJANGO_ALLOWED_HOSTS, which the secret audit rejects as placeholders.
    django_ops_block = service_block(compose_text, "django-ops")

    assert "JOBLENS_DOMAIN: ${JOBLENS_DOMAIN" in django_ops_block
    assert "Host: $${JOBLENS_DOMAIN}" in django_ops_block
    assert "http://127.0.0.1:8001/health/" in django_ops_block
    assert "http://localhost:8001" not in compose_text


def test_production_env_example_declares_required_runtime_settings():
    env_text = ENV_EXAMPLE_PATH.read_text()

    required_keys = [
        "POSTGRES_DB=",
        "POSTGRES_USER=",
        "POSTGRES_PASSWORD=",
        "DATABASE_URL=",
        "JOBLENS_DOMAIN=",
        "CADDY_ACME_EMAIL=",
        "JOBLENS_CORS_ORIGINS=",
        "JOBLENS_API_ROOT_PATH=/api",
        "JOBLENS_API_URL=http://api:8000",
        "JOBLENS_LOG_LEVEL=INFO",
        "JOBLENS_LOG_FORMAT=json",
        "DJANGO_SECRET_KEY=",
        "DJANGO_ALLOWED_HOSTS=",
        "DJANGO_CSRF_TRUSTED_ORIGINS=",
    ]

    for key in required_keys:
        assert key in env_text

    assert "localhost:5432" not in env_text
    assert "replace-with-a-long-random" in env_text

    # Loopback entries here would fail the secret audit's placeholder check, so
    # the healthcheck has to reach Django by its real hostname instead.
    allowed_hosts_line = next(
        line
        for line in env_text.splitlines()
        if line.startswith("DJANGO_ALLOWED_HOSTS=")
    )

    assert "localhost" not in allowed_hosts_line
    assert "127.0.0.1" not in allowed_hosts_line


def test_caddy_routes_api_ops_and_frontend_paths():
    caddyfile = CADDYFILE_PATH.read_text()

    assert "{$JOBLENS_DOMAIN}" in caddyfile
    assert "handle_path /api/*" in caddyfile
    assert "reverse_proxy api:8000" in caddyfile
    assert "handle /ops*" in caddyfile
    assert "reverse_proxy django-ops:8001" in caddyfile
    assert "reverse_proxy frontend:3000" in caddyfile
    assert "dashboard:8501" not in caddyfile
    assert "Strict-Transport-Security" in caddyfile
    assert "max_size 5MB" in caddyfile


def test_browser_facing_next_routes_stay_clear_of_the_proxied_api_prefix():
    """Caddy forwards /api/* to FastAPI, so a Next.js route handler under /api
    would be shadowed by the reverse proxy and never receive the request."""
    caddyfile = CADDYFILE_PATH.read_text()

    assert "handle_path /api/*" in caddyfile
    assert not (FRONTEND_DIR / "src" / "app" / "api").exists()

    for route_file in (FRONTEND_DIR / "src" / "app" / "proxy").rglob("route.ts"):
        assert route_file.is_file()

    browser_fetch_paths = [
        '"/proxy/analyze"',
        '"/proxy/analysis-runs"',
        "`/proxy/reports/candidate?format=${reportFormat}`",
    ]
    # lib as well as components: a fetch shared by more than one caller lives
    # there, and it is still the browser making it.
    component_text = "\n".join(
        path.read_text()
        for directory in ("components", "lib")
        for pattern in ("*.tsx", "*.ts")
        for path in (FRONTEND_DIR / "src" / directory).rglob(pattern)
    )

    for fetch_path in browser_fetch_paths:
        assert fetch_path in component_text

    assert 'fetch("/api/' not in component_text


def test_frontend_image_serves_a_standalone_production_build():
    next_config = (FRONTEND_DIR / "next.config.ts").read_text()
    dockerfile = (FRONTEND_DIR / "Dockerfile").read_text()
    dockerignore = (FRONTEND_DIR / ".dockerignore").read_text()

    assert 'output: "standalone"' in next_config

    assert "NODE_ENV=production" in dockerfile
    assert "npm ci" in dockerfile
    assert "npm run build" in dockerfile
    assert "/app/.next/standalone ./" in dockerfile
    assert "/app/.next/static ./.next/static" in dockerfile
    # Without this the standalone server binds to localhost and Caddy cannot
    # reach it across the Docker network.
    assert "HOSTNAME=0.0.0.0" in dockerfile
    assert "USER node" in dockerfile
    assert 'CMD ["node", "server.js"]' in dockerfile

    # Local env files must never be baked into the published image.
    assert ".env" in dockerignore
    assert "node_modules" in dockerignore
