# JobLens frontend

Next.js frontend for JobLens AI. FastAPI remains the source of business logic:
this app renders analysis, matching, ingestion, and validation results but never
recomputes them.

## Stack

| Layer | Choice |
| --- | --- |
| Framework | Next.js (App Router, React Server Components) |
| Language | TypeScript |
| Styling | Tailwind CSS |
| Charts | Recharts, used only where a chart beats a table |

State is React Context plus session storage, data fetching is `fetch` in Server
Components, and forms are native HTML. No query, state-management, table, form,
or component library is used.

## Running locally

Start the API first:

```bash
uvicorn src.api.main:app --reload
```

Then the frontend:

```bash
npm install && npm run dev
```

The app runs at `http://localhost:3000`. Copy `.env.example` to `.env.local` to
point at a non-default API URL:

```bash
cp .env.example .env.local
```

| Variable | Purpose | Default |
| --- | --- | --- |
| `JOBLENS_API_URL` | Base URL of the FastAPI backend, server-side only | `http://127.0.0.1:8000` |

## Architecture

The browser never calls FastAPI directly. Server Components fetch through
`src/lib/api`, dataset mutations run as Server Actions, and the remaining client
calls post to thin route handlers that forward the body unchanged:

```
Server Component  ──►  src/lib/api/endpoints.ts  ──►  FastAPI
Server Action     ──►  src/app/datasets/actions  ──►  FastAPI
Client component  ──►  /proxy/analyze            ──►  FastAPI
                  ──►  /proxy/analysis-runs      ──►  FastAPI
                  ──►  /proxy/reports/candidate  ──►  FastAPI
```

Dataset upload, rename, and delete are Server Actions so they can call
`refresh()` and update the rendered list without a manual reload. The report
route stays a route handler because it streams a file response, which a Server
Action cannot return.

Those handlers sit under `/proxy` rather than the more usual `/api` because in
production Caddy forwards `/api/*` to FastAPI, so a Next.js route handler under
`/api` would be shadowed by the reverse proxy and never receive the request.

This keeps the API base URL on the server and avoids a CORS allowlist change.
One consequence worth knowing: FastAPI's per-client rate limiter sees the Next.js
server address rather than each visitor.

## Pages

| Route | Purpose | Backing endpoint |
| --- | --- | --- |
| `/` | Role fit, skill gaps, and top matches for the current analysis | `POST /analyze` |
| `/analyze` | Profile builder and search scope | `GET /filter-options`, `POST /analyze` |
| `/jobs` | Browse and filter every posting | `GET /jobs` |
| `/skills` | Skill demand, role importance, location and employer concentration | `POST /market-insights` |
| `/history` | Saved analysis runs | `GET /analysis-runs` |
| `/history/[id]` | One saved run | `GET /analysis-runs/{id}` |
| `/datasets` | Upload a jobs CSV, rename or delete saved datasets | `GET`, `POST`, `PATCH`, `DELETE /datasets` |

Markdown and PDF skill-gap reports download from the overview via
`POST /reports/candidate`.

The active dataset lives in the `dataset` search param so Server Components can
read it and filtered views stay shareable.

## Layout

```
src/
  app/             routes, route handlers, loading and error boundaries
  components/
    layout/        shell, navigation, dataset switcher, page headers
    ui/            primitives: card, badge, button, table, states
    domain/        JobLens concepts: job cards, role fit, skill gaps
    charts/        Recharts wrappers
  context/         analysis result shared across pages
  lib/             typed API client, formatting, dataset helpers
```

## Design notes

The palette is deliberately near-monochrome, so meaning is carried by fill
weight rather than hue: matched skills render as solid chips, missing skills as
dashed outlines, and the API status dot is filled when online and hollow when
offline. Because two low-chroma steps would be indistinguishable, charts are
single-series only.

Skill demand is measured across the current snapshot. JobLens does not retain
historical snapshots, so it is a demand ranking, not a trend over time.

## Checks

```bash
npm run build
npm run typecheck
npm run lint
```
