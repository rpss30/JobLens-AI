from __future__ import annotations

import os

from flask import Flask, render_template

from ops import services


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)

    if test_config:
        app.config.update(test_config)

    @app.get("/")
    def dashboard():
        return render_template(
            "dashboard.html",
            **services.get_dashboard_context(),
        )

    @app.get("/ingestion-runs")
    def ingestion_runs():
        return render_template(
            "ingestion_runs.html",
            **services.get_ingestion_runs_context(),
        )

    @app.get("/extraction-health")
    def extraction_health():
        return render_template(
            "extraction_health.html",
            **services.get_extraction_health_context(),
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.getenv("OPSLENS_HOST", "0.0.0.0"),
        port=int(os.getenv("OPSLENS_PORT", "5001")),
    )

