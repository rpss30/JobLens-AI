# AI Skill Extraction

JobLens AI uses AI extraction during offline dataset refreshes, not at dashboard
runtime. This keeps the demo fast and reproducible while still demonstrating a
real AI engineering workflow.

## Structured output contract

Groq and Gemini both use the shared prompt version:

```text
skill-extraction-v2
```

The requested model response shape is:

```json
{
  "skills": [
    {
      "name": "Python",
      "confidence": 0.95,
      "evidence": "short phrase"
    }
  ]
}
```

The parser also accepts the older `{"skills": ["Python"]}` shape so existing
artifacts and tests remain compatible.

## Normalization

All extracted skills pass through the same taxonomy cleanup:

- trims whitespace and deduplicates skills,
- removes generic non-technical terms,
- normalizes aliases such as `JS` to `javascript`, `Node` to `node.js`,
  `K8s` to `kubernetes`, and `postgres` to `postgresql`,
- keeps explainable skill strings that the matching engine can show back to the
  candidate.

## Fallback behavior

The Canada snapshot builder tries Groq first. If Groq fails or returns no
skills, the pipeline records the provider error and falls back to deterministic
dictionary extraction. This avoids losing the whole refresh because of one
provider failure while still surfacing the fallback in metadata.

The snapshot CSV stores compact metadata:

- `skill_extraction_provider`
- `skill_extraction_model`
- `skill_extraction_prompt_version`
- `skill_extraction_confidence`
- `skill_extraction_error`

When seeded into PostgreSQL, model and prompt metadata are also written to the
`extraction_results` table for auditability.

## Offline evaluation

The repository includes a small labeled evaluation dataset:

```text
data/evaluation/skill_extraction_cases.json
```

Run the local quality gate:

```bash
python scripts/evaluate_skill_extraction.py \
  --minimum-average-recall 0.85 \
  --summary-path tmp/skill-extraction-eval.md
```

The current evaluation uses deterministic extraction as a stable baseline
because CI should not call live LLM APIs. The same harness can be reused later
to compare Groq, Gemini, and future embedding/taxonomy approaches with mocked
or recorded responses.
