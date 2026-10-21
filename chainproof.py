#!/usr/bin/env python3
"""chainproof.py — verify Marlo's append-only, hash-chained log.

Dependency-free, network-free, stdlib only. Reimplements the exact
canonicalization the log is written with, so a third party can re-derive
every hash and confirm the record was not silently edited:

    canon(obj) = json.dumps(obj, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=False)
    id   = sha256( canon( entry without "id" and "hash" ) )
    hash = sha256( canon( entry without "hash" ) )
    prev = the previous entry's hash, or "GENESIS" for seq 1

Usage:
    python3 chainproof.py [events.jsonl] [--json] [--anchor]

Exit code 0 = chain intact. 1 = mismatch, broken link, or malformed line.

Honest scope (do not overstate): this proves the file is internally
consistent and that no line was edited or removed *after* it was written
with an unchanged successor. On its own the chain is tamper-EVIDENT, not
tamper-PROOF: whoever holds the file could rewrite it and recompute the chain.
That gap was narrowed on 2026-10-14 — `tools/anchor.py` has the log head
timestamped by an independent RFC 3161 TSA, so rewriting the log is now
*detectable* by anyone holding the token. It does not make rewriting
*impossible*, and it requires the token to be distributed (a copy kept only in
Marlo's own repo can still be deleted). What the chain alone rules out is
silent, careless, or partial edits.
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone

GENESIS = "GENESIS"


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def verify(path):
    prev = GENESIS
    count = 0
    problems = []
    try:
        raw = open(path, "rb").read()
    except OSError as e:
        print(f"cannot read {path}: {e}", file=sys.stderr)
        return None
    for lineno, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        count += 1
        try:
            e = json.loads(line)
        except json.JSONDecodeError as exc:
            problems.append(f"line {lineno}: malformed JSON ({exc})")
            continue
        stored = e.get("hash")
        body = {k: v for k, v in e.items() if k != "hash"}
        if sha(canon(body)) != stored:
            problems.append(f"seq {e.get('seq')}: hash mismatch (content edited)")
        if e.get("id") != sha(canon({k: v for k, v in e.items() if k not in ("id", "hash")})):
            problems.append(f"seq {e.get('seq')}: id mismatch")
        if e.get("prev") != prev:
            problems.append(f"seq {e.get('seq')}: broken link (prev != previous hash)")
        if e.get("seq") != count:
            problems.append(f"seq {e.get('seq')}: non-sequential (expected {count})")
        prev = stored
    return {
        "file": path,
        "events": count,
        "head": prev,
        "fileSha256": hashlib.sha256(raw).hexdigest(),
        "problems": problems,
    }


def main():
    ap = argparse.ArgumentParser(description="Verify Marlo's hash-chained log.")
    ap.add_argument("file", nargs="?", default="../../log/events.jsonl")
    ap.add_argument("--json", action="store_true", help="machine-readable result")
    ap.add_argument("--anchor", action="store_true",
                    help="emit a compact, quotable anchor for the verified file")
    a = ap.parse_args()

    result = verify(a.file)
    if result is None:
        sys.exit(2)

    if a.anchor:
        out = {
            "record": "marlo/agentic-marlo log",
            "file": result["file"],
            "events": result["events"],
            "head": result["head"],
            "fileSha256": result["fileSha256"],
            "verified": not result["problems"],
            "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        print(json.dumps(out, indent=2, sort_keys=True))
        sys.exit(1 if result["problems"] else 0)

    if a.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for p in result["problems"]:
            print(f"  PROBLEM  {p}")
        status = "OK" if not result["problems"] else "FAIL"
        print(f"{status}: {result['events']} events, head={result['head'][:12]}, "
              f"sha256(file)={result['fileSha256'][:12]}, problems={len(result['problems'])}")
    sys.exit(1 if result["problems"] else 0)


if __name__ == "__main__":
    main()
