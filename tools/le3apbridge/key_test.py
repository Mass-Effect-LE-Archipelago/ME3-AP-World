"""Live mission-key test on a disposable test career (owner-approved 2026-10-29).

Binds the loaded, unbound career to a test identity, then delivers the named mission keys as the next indexed items
(DEV_TXN ... KEY <k>). Never touches a career bound to another identity. Appends to a JSON-lines receipt.
usage: python key_test.py <receipt.jsonl> <key index or region substring>...
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from probe import Connection

IDENTITY = hashlib.sha256(b"le3 mission key test 2026-10-29").hexdigest()
HISTORY = hashlib.sha256(b"research_existing_save_v1_NOT_maximum_content").hexdigest()
KEYS = [entry["region"] for entry in json.loads((Path(__file__).resolve().parents[1] / "le3mod/mission_keys.json").read_text())]


def resolve(text: str) -> int:
    if text.isdigit():
        return int(text)
    hits = [i for i, region in enumerate(KEYS) if text.lower() in region.lower()]
    if len(hits) != 1:
        raise SystemExit(f"{text!r} matches {[KEYS[i] for i in hits]}; use one of {list(enumerate(KEYS))}")
    return hits[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("keys", nargs="+")
    args = parser.parse_args()
    wanted = [resolve(k) for k in args.keys]
    log = []
    with Connection() as c:
        def ask(text):
            reply = c.request(text)
            log.append({"request": text, "reply": reply})
            return reply
        if "KEYS" not in ask("CAPS").split():
            raise SystemExit("installed bridge has no KEY delivery (needs 0.2.4)")
        ask("MAP")
        session = ask("DEV_SESSION").split()
        if session[2] == "unbound":
            ask(f"DEV_BIND {IDENTITY} {HISTORY} RESEARCH_ONLY")
            session = ask("DEV_SESSION").split()
        if session[2] != IDENTITY or session[3] != HISTORY:
            raise SystemExit("loaded career belongs to another identity; refusing")
        cursor = int(session[4])
        for k in wanted:
            ask(f"DEV_TXN {IDENTITY} {HISTORY} {cursor} KEY {k}")
            cursor += 1
        ask("GETBS " + " ".join(str(26100 + k) for k in range(len(KEYS))))
    with args.receipt.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"utc": datetime.now(timezone.utc).isoformat(), "keys": [KEYS[k] for k in wanted], "log": log}) + "\n")
    for entry in log:
        print(entry["request"][:60], "->", entry["reply"])


if __name__ == "__main__":
    main()
