import json

import pytest

from scripts.fetch_canada_jobs import load_employer_sources


def test_load_employer_sources_reads_valid_registry(tmp_path):
    source_path = tmp_path / "sources.json"
    source_path.write_text(
        json.dumps(
            [
                {
                    "company": "Example",
                    "source_type": "greenhouse",
                    "source_identifier": "example",
                }
            ]
        ),
        encoding="utf-8",
    )

    sources = load_employer_sources(source_path)

    assert sources[0]["company"] == "Example"


def test_load_employer_sources_rejects_missing_fields(tmp_path):
    source_path = tmp_path / "sources.json"
    source_path.write_text(
        json.dumps([{"company": "Example"}]),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing fields"):
        load_employer_sources(source_path)
