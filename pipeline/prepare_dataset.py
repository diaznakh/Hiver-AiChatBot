from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path

REQUIRED = {
    "tweet_id",
    "author_id",
    "inbound",
    "created_at",
    "text",
    "response_tweet_id",
    "in_response_to_tweet_id",
}


def parse_bool(value: str) -> int:
    lowered = value.strip().lower()
    if lowered in {"true", "1"}:
        return 1
    if lowered in {"false", "0"}:
        return 0
    raise ValueError(f"unknown boolean: {value!r}")


def validate_timestamp(value: str) -> str:
    raw = value.strip()
    parsers = (
        lambda: datetime.fromisoformat(raw.replace("Z", "+00:00")),
        lambda: datetime.strptime(raw, "%a %b %d %H:%M:%S %z %Y"),
    )
    for parser in parsers:
        try:
            parser()
            return raw
        except ValueError:
            continue
    raise ValueError(f"unparseable timestamp: {raw!r}")


def ingest(csv_path: Path, db_path: Path) -> dict[str, int | str]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(
        """CREATE TABLE tweets (
        tweet_id TEXT PRIMARY KEY, author_id TEXT NOT NULL, inbound INTEGER NOT NULL,
        created_at TEXT NOT NULL, text TEXT NOT NULL, response_tweet_id TEXT,
        parent_id TEXT
        )"""
    )
    counts = Counter()
    checksum = hashlib.sha256()
    with csv_path.open("rb") as raw:
        for chunk in iter(lambda: raw.read(1024 * 1024), b""):
            checksum.update(chunk)
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"missing columns: {sorted(missing)}")
        batch = []
        for row in reader:
            try:
                record = (
                    str(row["tweet_id"]).strip(),
                    row["author_id"].strip(),
                    parse_bool(row["inbound"]),
                    validate_timestamp(row["created_at"]),
                    row["text"].strip(),
                    row["response_tweet_id"].strip(),
                    row["in_response_to_tweet_id"].strip() or None,
                )
                if not all((record[0], record[1], record[3], record[4])):
                    raise ValueError("required value empty")
                batch.append(record)
                if len(batch) >= 10_000:
                    conn.executemany("INSERT INTO tweets VALUES (?,?,?,?,?,?,?)", batch)
                    counts["accepted"] += len(batch)
                    conn.commit()
                    batch.clear()
            except (ValueError, sqlite3.IntegrityError):
                counts["quarantined"] += 1
        if batch:
            conn.executemany("INSERT INTO tweets VALUES (?,?,?,?,?,?,?)", batch)
            counts["accepted"] += len(batch)
            conn.commit()
    conn.execute("CREATE INDEX idx_tweets_parent ON tweets(parent_id)")
    conn.execute("CREATE INDEX idx_tweets_author ON tweets(author_id, inbound)")
    conn.commit()
    counts["missing_parent"] = conn.execute(
        "SELECT count(*) FROM tweets t WHERE parent_id IS NOT NULL AND NOT EXISTS "
        "(SELECT 1 FROM tweets p WHERE p.tweet_id=t.parent_id)"
    ).fetchone()[0]
    conn.close()
    return {**counts, "source_sha256": checksum.hexdigest()}


def root_for(conn: sqlite3.Connection, tweet_id: str, max_depth: int = 100) -> tuple[str, bool]:
    current = tweet_id
    seen = set()
    for _ in range(max_depth):
        if current in seen:
            return current, False
        seen.add(current)
        row = conn.execute("SELECT parent_id FROM tweets WHERE tweet_id=?", (current,)).fetchone()
        if not row or not row[0]:
            return current, bool(row)
        current = row[0]
    return current, False


def ancestry_for(conn: sqlite3.Connection, tweet_id: str, max_depth: int = 100) -> tuple[list[str], bool]:
    current = tweet_id
    seen = {tweet_id}
    ancestors = []
    for _ in range(max_depth):
        row = conn.execute("SELECT parent_id FROM tweets WHERE tweet_id=?", (current,)).fetchone()
        if not row:
            return list(reversed(ancestors)), False
        parent = row[0]
        if not parent:
            return list(reversed(ancestors)), True
        if parent in seen:
            return list(reversed(ancestors)), False
        seen.add(parent)
        ancestors.append(parent)
        current = parent
    return list(reversed(ancestors)), False


def export_brand(db_path: Path, brand: str, output: Path, manifest_path: Path) -> dict:
    conn = sqlite3.connect(db_path)
    replies = conn.execute(
        """SELECT c.tweet_id, c.author_id, c.created_at, c.text,
                  b.tweet_id, b.created_at, b.text
           FROM tweets b JOIN tweets c ON c.tweet_id=b.parent_id
           WHERE b.author_id=? AND b.inbound=0 AND c.inbound=1
           ORDER BY c.created_at, c.tweet_id""",
        (brand,),
    ).fetchall()
    rows = []
    incomplete = 0
    for customer_id, customer_author, customer_at, problem, brand_id, brand_at, response in replies:
        root, complete = root_for(conn, customer_id)
        history_ids, history_complete = ancestry_for(conn, customer_id)
        complete = complete and history_complete
        incomplete += int(not complete)
        rows.append(
            {
                "conversation_id": root,
                "target_tweet_id": customer_id,
                "response_tweet_id": brand_id,
                "customer_author_id": customer_author,
                "created_at": customer_at,
                "response_created_at": brand_at,
                "message": problem,
                "observed_response": response,
                "history_tweet_ids": history_ids,
                "complete": complete,
            }
        )
    conn.close()
    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(row["conversation_id"], []).append(row)
    ordered = sorted(groups.items(), key=lambda item: min(row["created_at"] for row in item[1]))
    n = len(ordered)
    boundaries = (int(n * 0.70), int(n * 0.85))
    split_by_group = {}
    for index, (group, _) in enumerate(ordered):
        split_by_group[group] = "train" if index < boundaries[0] else "dev" if index < boundaries[1] else "test"
    output.mkdir(parents=True, exist_ok=True)
    handles = {name: (output / f"candidates_{name}.jsonl").open("w") for name in ("train", "dev", "test")}
    seen_text = set()
    duplicate_count = 0
    for row in rows:
        normalized = " ".join(row["message"].lower().split())
        digest = hashlib.sha256(normalized.encode()).hexdigest()
        if digest in seen_text:
            duplicate_count += 1
            continue
        seen_text.add(digest)
        split = split_by_group[row["conversation_id"]]
        row["split"] = split
        handles[split].write(json.dumps(row, ensure_ascii=False) + "\n")
    for handle in handles.values():
        handle.close()
    manifest = {
        "brand_id": brand,
        "status": "CANDIDATES_REQUIRE_HUMAN_TAXONOMY_AND_LABELS",
        "eligible_pairs": len(rows),
        "conversation_groups": n,
        "incomplete_ancestry": incomplete,
        "exact_duplicate_messages_removed": duplicate_count,
        "split_method": "chronological 70/15/15 by whole conversation root",
        "output_files": {name: str(output / f"candidates_{name}.jsonl") for name in handles},
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare one brand from Customer Support on Twitter")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--brand", required=True)
    parser.add_argument("--work-db", default="artifacts/dataset.sqlite3")
    parser.add_argument("--output", default="data/processed")
    parser.add_argument("--manifest", default="data/manifest.json")
    args = parser.parse_args()
    stats = ingest(Path(args.csv), Path(args.work_db))
    manifest = export_brand(Path(args.work_db), args.brand, Path(args.output), Path(args.manifest))
    manifest["ingestion"] = stats
    Path(args.manifest).write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
