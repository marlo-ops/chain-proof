# ChainProof — make the record checkable, not just claimed

**Status:** local draft for principal review. Not published, not sent.
**Fills:** `business/needs.md` B6 — *a verifiable public record: expose the
hash-chained log as a checkable artifact.*

## The problem this solves

A record kept by an AI agent is worth nothing if a reader has to take the
agent's word that it wasn't edited. "Trust me, the log is append-only" is a
claim. `chainproof.py` turns it into something anyone can check in one command.

Every entry in `log/events.jsonl` is written with a SHA-256 hash over its own
canonical content and a `prev` pointer to the previous entry's hash. Editing,
reordering, inserting, or deleting any line breaks the chain from that point
on. `chainproof.py` re-derives all of it from scratch.

## Use it

```sh
python3 chainproof.py path/to/events.jsonl        # human summary, exit 1 on failure
python3 chainproof.py path/to/events.jsonl --json # machine-readable
python3 chainproof.py path/to/events.jsonl --anchor  # quotable checkpoint
./reproduce.sh                                     # verify + self-test + anchor
```

`reproduce.sh` deliberately tampers a copy and confirms the checker fails on
it — a verifier that can never fail proves nothing.

## What it proves — and what it does not

**Proves:** the file is internally consistent; no line has been silently edited
or dropped since it was written; the head hash and the file digest are
reproducible.

**Does not prove:** that the log is honest in the first place, or that an
adversary who holds *both* the file and every copy of the anchor couldn't
rewrite the whole file and recompute the chain.

**External anchor (added 2026-10-14).** The chain is no longer only self-held;
its head is now timestamped by an independent RFC 3161 Time-Stamp Authority
(DigiCert, with a pinned freeTSA fallback) via `tools/anchor.py`. The TSA signs a
token with a key Marlo does not hold, attesting that the head digest existed at a
given time. Anyone re-verifies it offline with `openssl ts -verify` against the
OS CA bundle, then confirms the anchored head still appears as a committed event
hash in the live chain:

```sh
python3 tools/anchor.py verify      # every stored anchor, offline
python3 tools/anchor.py --negative  # proves a tampered anchor is rejected
```

So the earlier blanket "tamper-EVIDENT, not tamper-PROOF" no longer holds. What
remains is narrower and stated precisely: the anchor makes rewriting the log
**detectable, not impossible**. It works for a verifier who has *seen* the token —
so the residual gap is **distribution**: a copy of the token kept only in Marlo's
own repo can still be deleted by an adversary who controls that repo. Publishing
the token somewhere Marlo cannot rewrite (a repo it does not own, or a
counterparty's copy) closes that last step; the artifact is built so it is one
command away. Until then the honest claim is: *anchored and independently
verifiable, with token distribution still pending.* (Supersedes the 2026-10-13
"no external anchor" note in `SECURITY.md`.)

## Canonicalization (so anyone can reimplement it)

```python
canon(obj) = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
id   = sha256(canon(entry_without_id_and_hash))
hash = sha256(canon(entry_without_hash))
prev = previous entry's hash, or "GENESIS" for seq 1
```

## Why it matters commercially

The ledger's only durable asset is *trust that the record wasn't doctored* —
that is what a paid alert feed / API subscriber is buying. This gives buyers a
one-command way to audit their supplier, which is exactly the differentiator an
agent-run business needs and a PDF-with-a-logo vendor cannot offer.

_No source, no claim. This proves syntax and integrity; the incidents' truth
rests on their cited sources (`ledger/sources/status.jsonl`)._
