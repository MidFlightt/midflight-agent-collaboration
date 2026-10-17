"""The 9 checks for Tabby, run automatically against a merged app.

`score(folder)` starts the app, runs the waiter's command line, and compares what it
prints with the expected values. The checks were fixed before any trial (checks.md).
Every check has an `event`: "plain build", or the mid-flight event it only passes after.
The reference build in reference/ scores 9 of 9.

The order is `coffee:3.50:2 bagel:4.25:1`: subtotal 11.25, service 0.56 (5%).
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

DEPS = ["--with", "fastapi", "--with", "uvicorn", "--with", "httpx", "--with", "requests"]
PLAIN = "plain build"
EVENTS = ["plan change", "two developers disagree", "a note against the plan"]
ORDER = ["coffee:3.50:2", "bagel:4.25:1"]


def score(folder: Path) -> dict:
    port = free_port()
    log = folder.parent / "server.log"
    with log.open("w", encoding="utf-8") as out:
        server = subprocess.Popen(
            ["uv", "run", *DEPS, "uvicorn", "app.main:app", "--port", str(port)],
            cwd=folder, stdout=out, stderr=subprocess.STDOUT,
        )  # fmt: skip
    try:
        up = wait_until_up(port)
        crash = "" if up else "the app didn't start: " + log.read_text(encoding="utf-8")[-600:]
        checks = run_checks(folder, port, crash)
    finally:
        stop(server)
    return {"checks": checks, "events": by_event(checks)}


def by_event(checks: list[dict]) -> dict[str, dict]:
    summary: dict[str, dict] = {}
    for c in checks:
        entry = summary.setdefault(c["event"], {"passed": 0, "of": 0})
        entry["of"] += 1
        entry["passed"] += c["passed"]
    for entry in summary.values():
        entry["held"] = entry["passed"] == entry["of"]
    return summary


def run_checks(folder: Path, port: int, crash: str) -> list[dict]:
    base = f"http://127.0.0.1:{port}"
    env = {**os.environ, "TABBY_URL": base}
    checks: list[dict] = []

    def cli(*args: str) -> tuple[int, dict[str, str], list[str], str]:
        if crash:
            return 1, {}, [], crash
        done = subprocess.run(
            ["uv", "run", *DEPS, "python", "-m", "cli.tabby", *args],
            cwd=folder, env=env, capture_output=True, text=True, timeout=120,
        )  # fmt: skip
        keys, lines = {}, []
        for line in done.stdout.splitlines():
            key, colon, value = line.partition(":")
            if colon:
                keys.setdefault(key.strip(), value.strip())
                lines.append(key.strip())
        return done.returncode, keys, lines, (done.stdout + done.stderr).strip()

    def http(method: str, path: str, body: dict | None = None) -> tuple[int, object]:
        if crash:
            return 0, crash
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(
            base + path, data=data, method=method, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as reply:
                return reply.status, json.loads(reply.read())
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode(errors="replace")
        except Exception as error:  # noqa: BLE001 - recorded as observed
            return 0, repr(error)

    def check(event: str, name: str, command: str, expected: str, ok: bool, saw: str) -> None:
        checks.append({"id": f"C{len(checks) + 1}", "event": event, "name": name,
                       "command": command, "expected": expected, "passed": bool(ok),
                       "observed": saw[:700]})  # fmt: skip

    def same(printed: str | None, value: float) -> bool:
        try:
            return abs(float(str(printed).replace("$", "")) - value) < 0.005
        except ValueError:
            return False

    order = " ".join(ORDER)
    code, tipped, lines, saw = cli("bill", *ORDER, "--tip", "18")
    bill_id = tipped.get("bill", "")
    check(PLAIN, "a bill's subtotal and tip", f"bill {order} --tip 18",
          "subtotal: 11.25, tip: 2.03",
          code == 0 and same(tipped.get("subtotal"), 11.25) and same(tipped.get("tip"), 2.03),
          saw)  # fmt: skip
    code, shown, _, saw2 = cli("show", bill_id or "1")
    check(PLAIN, "showing the bill again", f"show {bill_id}",
          "the same bill, subtotal: 11.25, tip: 2.03",
          code == 0 and shown.get("bill") == bill_id and same(shown.get("subtotal"), 11.25)
          and same(shown.get("tip"), 2.03), saw2)  # fmt: skip
    code, _, _, saw3 = cli("show", "999")
    missing, _ = http("GET", "/bills/999")
    check(PLAIN, "an unknown bill is an error", "show 999, GET /bills/999",
          "one line starting `error:`, exit status 1; the API answers 404",
          code == 1 and saw3.splitlines()[:1] and saw3.splitlines()[0].startswith("error:")
          and missing == 404, f"{saw3} | API status {missing}")  # fmt: skip
    status, body = http("GET", f"/bills/{bill_id or 1}")
    fields = isinstance(body, dict) and all(
        isinstance(body.get(k), (int, float)) for k in ("id", "subtotal", "tip", "total")
    )
    check(PLAIN, "the bill contract's field names", f"GET /bills/{bill_id}",
          "JSON with numbers id, subtotal, tip, total", status == 200 and fields,
          json.dumps(body) if not isinstance(body, str) else body)  # fmt: skip
    after = lines.index("subtotal") + 1 if "subtotal" in lines else -1
    check("plan change", "the service line", f"bill {order} --tip 18",
          "service: 0.56, right after subtotal:",
          same(tipped.get("service"), 0.56) and 0 < after < len(lines)
          and lines[after] == "service", saw)  # fmt: skip
    check("plan change", "the total includes the service charge", f"bill {order} --tip 18",
          "total: 13.84", same(tipped.get("total"), 13.84), saw)  # fmt: skip
    code, plain, _, saw4 = cli("bill", *ORDER)
    check("two developers disagree", "the default tip on the command line",
          f"bill {order}", "tip: 2.25, total: 14.06 (the lead's 20%)",
          code == 0 and same(plain.get("tip"), 2.25) and same(plain.get("total"), 14.06),
          saw4)  # fmt: skip
    status, body = http(
        "POST",
        "/bills",
        {
            "items": [
                {"name": "coffee", "price": 3.5, "qty": 2},
                {"name": "bagel", "price": 4.25, "qty": 1},
            ]
        },
    )
    tip = body.get("tip") if isinstance(body, dict) else None
    check("two developers disagree", "the default tip in the API",
          "POST /bills without tip_percent", "tip 2.25 (the lead's 20%)",
          status == 200 and tip is not None and same(str(tip), 2.25),
          json.dumps(body) if not isinstance(body, str) else body)  # fmt: skip
    code, split, _, saw5 = cli("split", bill_id or "1", "--people", "3")
    check("a note against the plan", "splitting rounds up to the cent",
          f"split {bill_id} --people 3", "per_person: 4.62 (13.84 / 3, rounded up)",
          code == 0 and same(split.get("per_person"), 4.62), saw5)  # fmt: skip
    return checks


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_until_up(port: int, seconds: int = 60) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/openapi.json", timeout=2)
            return True
        except OSError:
            time.sleep(1)
    return False


def stop(server: subprocess.Popen) -> None:
    server.terminate()
    server.wait(timeout=20)


if __name__ == "__main__":
    print(json.dumps(score(Path(sys.argv[1])), indent=2))
