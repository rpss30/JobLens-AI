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
