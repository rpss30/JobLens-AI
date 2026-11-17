from pathlib import Path


WORKFLOW_PATH = Path(".github/workflows/refresh-canada-jobs.yml")


def test_refresh_workflow_skips_cleanly_without_groq_secret() -> None:
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "id: groq_config" in workflow_text
    assert 'echo "configured=false" >> "$GITHUB_OUTPUT"' in workflow_text
    assert "Canada Jobs Refresh Skipped" in workflow_text
    assert "exit 0" in workflow_text


def test_refresh_workflow_gates_refresh_steps_on_groq_secret() -> None:
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    required_guard = "if: steps.groq_config.outputs.configured == 'true'"

    guarded_steps = [
        "Fetch and enrich current Canadian jobs",
        "Validate refreshed snapshot",
        "Run test suite",
        "Detect snapshot changes",
    ]

    for step_name in guarded_steps:
        step_index = workflow_text.index(f"- name: {step_name}")
        next_step_index = workflow_text.find("\n      - name:", step_index + 1)
        step_block = workflow_text[
            step_index : (
                next_step_index
                if next_step_index != -1
                else len(workflow_text)
            )
        ]

        assert required_guard in step_block

    assert (
        "if: steps.groq_config.outputs.configured == 'true' "
        "&& steps.changes.outputs.changed == 'true'"
    ) in workflow_text


def test_refresh_workflow_carries_enrichment_between_runs() -> None:
    """
    Enrichment is the expensive half, and one full run very nearly spends the
    day's Groq allowance. A run that enriched every posting and then failed a
    later gate used to discard all of it with the runner, so the retry paid
    full price and a second attempt the same day could not finish at all.
    """
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")

    restore_index = workflow_text.index(
        "- name: Restore the last enriched candidate"
    )
    enrich_index = workflow_text.index(
        "- name: Fetch and enrich current Canadian jobs"
    )
    save_index = workflow_text.index(
        "- name: Keep the enriched candidate for the next run"
    )

    # Restored before the build runs, or it cannot know what it still owes.
    assert restore_index < enrich_index
    assert enrich_index < save_index

    save_end = workflow_text.find("\n      - name:", save_index + 1)
    save_block = workflow_text[
        save_index : (save_end if save_end != -1 else len(workflow_text))
    ]

    # Saved even when an earlier step failed. The build checkpoints after
    # every posting, so a run that died partway still has work worth keeping.
    assert "if: always()" in save_block

    # The validator has to read the file the build actually wrote.
    assert (
        "--candidate-path /tmp/extraction-cache/canada_jobs_snapshot.csv"
        in workflow_text
    )
    assert "--output-path /tmp/extraction-cache/canada_jobs_snapshot.csv" in (
        workflow_text
    )


def test_refresh_workflow_merges_and_deploys_the_validated_snapshot() -> None:
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")

    # The merge is only defensible because validation and the suite run first.
    validate_index = workflow_text.index("- name: Validate refreshed snapshot")
    tests_index = workflow_text.index("- name: Run test suite")
    merge_index = workflow_text.index("gh pr merge")

    assert validate_index < merge_index
    assert tests_index < merge_index
    assert "--squash --delete-branch" in workflow_text

    # A merge made with GITHUB_TOKEN raises no push event, so the deploy has to
    # be dispatched explicitly or the refreshed snapshot never ships.
    assert "actions: write" in workflow_text
    assert "gh workflow run deploy-production.yml" in workflow_text
    assert merge_index < workflow_text.index("gh workflow run")
