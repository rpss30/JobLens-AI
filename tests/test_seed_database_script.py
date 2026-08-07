import sys
from types import ModuleType, SimpleNamespace

import pandas as pd

from scripts import seed_database


def test_run_database_migrations_upgrades_to_head(monkeypatch, tmp_path) -> None:
    alembic_ini = tmp_path / "alembic.ini"
    alembic_ini.write_text("[alembic]\n", encoding="utf-8")
    calls = []

    class FakeConfig:
        def __init__(self, path: str):
            self.path = path

    def fake_upgrade(config: FakeConfig, revision: str) -> None:
        calls.append((config.path, revision))

    fake_alembic = ModuleType("alembic")
    fake_alembic.command = SimpleNamespace(upgrade=fake_upgrade)

    fake_config_module = ModuleType("alembic.config")
    fake_config_module.Config = FakeConfig

    monkeypatch.setattr(seed_database, "ALEMBIC_INI_PATH", alembic_ini)
    monkeypatch.setitem(sys.modules, "alembic", fake_alembic)
    monkeypatch.setitem(sys.modules, "alembic.config", fake_config_module)

    seed_database.run_database_migrations()

    assert calls == [(str(alembic_ini), "head")]


def test_seed_processed_jobs_accepts_dataset_arguments(monkeypatch, tmp_path) -> None:
    processed_jobs_path = tmp_path / "canada_jobs_snapshot.csv"
    processed_jobs_path.write_text("title\nExample\n", encoding="utf-8")
    dataframe = pd.DataFrame([{"title": "Example"}])
    calls = []

    monkeypatch.setattr(
        seed_database,
        "run_database_migrations",
        lambda: calls.append("migrate"),
    )
    monkeypatch.setattr(seed_database.pd, "read_csv", lambda path: dataframe)

    def fake_seed_processed_jobs_from_dataframe(**kwargs):
        calls.append(kwargs)
        return 1

    monkeypatch.setattr(
        seed_database,
        "seed_processed_jobs_from_dataframe",
        fake_seed_processed_jobs_from_dataframe,
    )

    inserted_count = seed_database.main(
        processed_jobs_path=processed_jobs_path,
        dataset_name="canada_jobs",
        source_type="canada_snapshot",
        replace_existing=False,
    )

    assert inserted_count == 1
    assert calls[0] == "migrate"
    assert calls[1]["df"] is dataframe
    assert calls[1]["dataset_name"] == "canada_jobs"
    assert calls[1]["source_type"] == "canada_snapshot"
    assert calls[1]["replace_existing"] is False
