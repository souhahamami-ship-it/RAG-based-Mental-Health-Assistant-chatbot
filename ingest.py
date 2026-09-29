

from __future__ import annotations

import argparse
import json
import os
from datetime import date

from loader import chunk_text


def infer_topic(filename: str) -> str:
    return os.path.splitext(filename)[0].replace("_", " ")


def ingest(input_dir: str, output_path: str, trust_tier: str, reviewed_by: str | None) -> int:
    records = []
    for filename in sorted(os.listdir(input_dir)):
        if not filename.endswith(".txt"):
            continue
        path = os.path.join(input_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        for i, piece in enumerate(chunk_text(text)):
            records.append(
                {
                    "chunk_id": f"{filename}::{i}",
                    "source_id": filename,
                    "topic": infer_topic(filename),
                    "text": piece,
                    "trust_tier": trust_tier,
                    "reviewed_by": reviewed_by,
                    "last_reviewed": date.today().isoformat() if reviewed_by else None,
                    "citation_url": None,
                }
            )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the knowledge base JSON from raw text sources.")
    parser.add_argument("--input", default="data", help="Folder of raw .txt source files.")
    parser.add_argument("--output", default="data/knowledge.json", help="Path to write the chunked JSON to.")
    parser.add_argument(
        "--trust-tier",
        default="ai_drafted_needs_review",
        help=(
            "e.g. 'reviewed_psychoeducational' once a clinician has signed off, "
            "'public_domain_gov_source', or 'ai_drafted_needs_review' for anything "
            "not yet reviewed. Never ship 'ai_drafted_needs_review' content to real "
            "users without review -- use this tag to make that gap visible and "
            "queryable, not to hide it."
        ),
    )
    parser.add_argument("--reviewed-by", default=None, help="Name/org of clinical reviewer, if reviewed.")
    args = parser.parse_args()

    count = ingest(args.input, args.output, args.trust_tier, args.reviewed_by)
    print(f"Wrote {count} chunks from '{args.input}' to '{args.output}' (trust_tier={args.trust_tier})")


if __name__ == "__main__":
    main()