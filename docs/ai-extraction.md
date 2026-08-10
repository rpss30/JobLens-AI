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

The repository includes a hand-labeled evaluation dataset of 12 cases:

```text
data/evaluation/skill_extraction_cases.json
```

Each case carries a `rationale` describing what it probes. Labels were written by
reading the description text, never generated from extractor output, because a
dataset labeled by the thing under test can only ever agree with itself.

Four cases are plain skill lists that establish a baseline. The other eight are
written the way postings actually read, and each targets a specific failure mode:
required and preferred sections mixed with benefits, acronym aliases, framework
names carrying version numbers, prose with no list at all, soft skills that are
requirements but not technical skills, language names appearing inside company
and place names, database products sharing a query language, and multi-word
practices with no product name to lean on.

Run the local quality gate:

```bash
python scripts/evaluate_skill_extraction.py \
  --summary-path tmp/skill-extraction-eval.md
```

### Scoring

Recall alone cannot distinguish a careful extractor from one that returns its
whole vocabulary for every posting, since the second scores perfectly. The
harness therefore reports recall, precision, and F1 per case, and names the
skills each case invented as well as the ones it missed.

Measured for the deterministic extractor over the packaged cases:

| Metric | Value | Gate |
| --- | ---: | ---: |
| Average recall | 70.4% | 65% |
| Average precision | 95.0% | 90% |
| Average F1 | 74.6% | not gated |

The gates are floors, not targets. The headroom exists so that adding a
deliberately hard case does not trip the gate, since a new case can legitimately
lower the average. When the extractor changes, re-measure and update both the
gate and the table above in the same commit.

### Known weaknesses this dataset records

The deterministic extractor is the fallback used when Groq is unavailable, and
the harder cases exist to document where it is weak rather than to hide it:

- acronym aliases such as `ML`, `LLM`, and `RAG` are not resolved (20% recall)
- multi-word practices such as infrastructure as code are absent from its
  55-term vocabulary (0% recall)
- framework names carrying version numbers are missed (50% recall)
- `Java` is extracted from the company name "Java Holdings Inc." (50% precision),
  the only false positive in the set

The evaluation uses deterministic extraction as a stable baseline because CI must
not call live LLM APIs. The same harness accepts any callable, so Groq, Gemini,
and future taxonomy approaches can be compared against the same labels using
mocked or recorded responses.
