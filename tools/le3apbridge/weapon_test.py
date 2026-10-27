"""Live WEAPON delivery test on a disposable research career (owner-approved 2026-10-27).

Binds the loaded, unbound career to a test identity (research-only history), then delivers
indexed WEAPON items. Never touches a career bound to another identity. Writes a receipt.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from probe import Connection

IDENTITY = hashlib.sha256(b"le3 weapon test 2026-10-27").hexdigest()
HISTORY = hashlib.sha256(b"research_existing_save_v1_NOT_maximum_content").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("weapons", type=int, nargs="+", help="Weapons.hpp ids, delivered in order")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("receipt exists")
    log = []
    with Connection() as c:
        def ask(text):
            reply = c.request(text)
            log.append({"request": text, "reply": reply})
            return reply
        if "WEAPONS" not in ask("CAPS").split():
            raise RuntimeError("installed bridge has no WEAPON delivery")
        ask("MAP")
        session = ask("DEV_SESSION").split()
        if session[2] == "unbound":
            ask(f"DEV_BIND {IDENTITY} {HISTORY} RESEARCH_ONLY")
            session = ask("DEV_SESSION").split()
        if session[2] != IDENTITY or session[3] != HISTORY:
            raise RuntimeError("loaded career belongs to another identity; refusing")
        cursor = int(session[4])
        for index, weapon in enumerate(args.weapons):
            if index < cursor:
                continue
            ask(f"DEV_TXN {IDENTITY} {HISTORY} {index} WEAPON {weapon}")
        ask("DEV_SESSION")
    receipt = {"utc": datetime.now(timezone.utc).isoformat(), "identity": IDENTITY, "history": HISTORY,
               "weapons": args.weapons, "log": log}
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)
    print(json.dumps(log, indent=1))


if __name__ == "__main__":
    main()
