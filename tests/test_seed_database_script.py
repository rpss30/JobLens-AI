import sys
from types import ModuleType, SimpleNamespace

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
