"""Fill in description_formatted on a dataset that was built without it.

The postings were normalized by a version of the cleaner that flattened every
run of whitespace, so the paragraphs and lists the boards wrote are gone from
the stored text. They are still on the boards, and a job id names the board,
the employer and the posting, so each row can be matched back to its source
and given its formatting without anything else about the dataset moving.

Postings that have since closed keep their flattened text: the reader falls
back to the structure the app infers from the wording.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.ingestion.ashby_client import (
    fetch_ashby_postings,
    normalize_ashby_posting,
)
from src.ingestion.greenhouse_client import (
    fetch_greenhouse_jobs,
    normalize_greenhouse_job,
)
from src.ingestion.lever_client import (
    fetch_lever_postings,
    normalize_lever_posting,
)


DEFAULT_PATH = ROOT_DIR / "data" / "processed" / "canada_jobs_snapshot.csv"


def board_of(job_id: str) -> tuple[str, str] | None:
    """Split a job id into the board it came from and the employer's slug."""
    parts = str(job_id).split(":")

    if len(parts) < 3:
        return None

    return parts[0].strip().lower(), parts[1].strip()


def formatted_descriptions(source: str, slug: str) -> dict[str, str]:
    """Fetch one board and return its postings' formatted descriptions."""
    if source == "ashby":
        postings = fetch_ashby_postings(slug)
        rows = [
            normalize_ashby_posting(
                posting,
                company_name=slug,
                job_board_name=slug,
            )
            for posting in postings
        ]
    elif source == "greenhouse":
        rows = [
            normalize_greenhouse_job(job, slug)
            for job in fetch_greenhouse_jobs(slug)
        ]
    elif source == "lever":
        rows = [
            normalize_lever_posting(posting, slug)
            for posting in fetch_lever_postings(slug)
        ]
    else:
        return {}

    return {
        str(row.get("job_id")): str(row.get("description_formatted") or "")
        for row in rows
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be filled in without writing the file.",
    )
    args = parser.parse_args()

    jobs = pd.read_csv(args.path)

    if "job_id" not in jobs.columns:
        print(f"{args.path} has no job_id column to match on.")
        return 1

    boards: dict[tuple[str, str], list[int]] = defaultdict(list)

    for index, job_id in jobs["job_id"].items():
        board = board_of(job_id)

        if board:
            boards[board].append(index)

    formatted = pd.Series("", index=jobs.index, dtype="object")

    if "description_formatted" in jobs.columns:
        formatted = jobs["description_formatted"].fillna("").astype("object")

    matched = 0

    for (source, slug), indexes in sorted(boards.items()):
        try:
            descriptions = formatted_descriptions(source, slug)
        except Exception as error:  # noqa: BLE001 - one board must not stop the rest
            print(f"  {source}:{slug} could not be read ({error})")
            continue

        found = 0

        for index in indexes:
            description = descriptions.get(str(jobs.at[index, "job_id"]), "")

            if description:
                formatted.at[index] = description
                found += 1

        matched += found
        print(f"  {source}:{slug} matched {found}/{len(indexes)}")

    jobs["description_formatted"] = formatted

    print(f"\n{matched}/{len(jobs)} postings now carry a formatted description.")

    if args.dry_run:
        print("Dry run: nothing written.")
        return 0

    jobs.to_csv(args.path, index=False)
    print(f"Wrote {args.path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
