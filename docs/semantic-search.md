# Semantic Search

JobLens AI now supports three search modes:

| Mode | Purpose |
| --- | --- |
| `tfidf` | Explainable lexical relevance across titles, skills, companies, locations, and descriptions. |
| `semantic` | Local dense similarity using TF-IDF features projected into SVD embeddings. |
| `hybrid` | Blends lexical TF-IDF relevance with semantic similarity. |

The default remains `tfidf` so existing behavior stays stable and easy to
explain. Semantic and hybrid modes are available in the dashboard and FastAPI
`/analyze` request body through `search_mode`.

## Implementation

The semantic layer lives in:

```text
src/search/semantic_search.py
```

It builds weighted job documents from:

- title
- role category
- extracted skills
- company
- location
- description

Those documents are vectorized with scikit-learn TF-IDF and projected into dense
vectors with `TruncatedSVD`. Query vectors use the same transformation, and
cosine similarity ranks jobs. A small domain synonym layer maps conceptual
queries such as `server-side database APIs` toward explicit job-market terms
like backend services, REST APIs, PostgreSQL, and databases.

## Resume/Profile Similarity

The same module can rank jobs against a candidate profile document assembled
from current skills, target roles, and optional resume text. This is a foundation
for the next resume-analysis phase without storing private resume content.

## Why Not pgvector Yet

`pgvector` is useful when embeddings need to be persisted, indexed, and queried
at scale. JobLens currently uses small committed snapshots and user-uploaded CSVs
that are loaded into memory for analysis. Adding pgvector now would add Docker,
PostgreSQL extension, migration, and deployment complexity before the product
has a workload that needs approximate vector indexes.

The current local approach is the better portfolio tradeoff:

- no external embedding API calls during tests or demos,
- no live model dependency for search,
- deterministic results in CI,
- explainable fallback to TF-IDF,
- easy comparison between lexical, semantic, and hybrid relevance.

If the dataset grows substantially, the next step would be to add an embeddings
table, `pgvector` indexes, and a background job that refreshes vectors whenever
job postings change.
