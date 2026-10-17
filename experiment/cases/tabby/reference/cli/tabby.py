"""The Tabby command line: what the waiter types (see README.md). Reference build."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

URL = os.environ.get("TABBY_URL", "http://127.0.0.1:8000")


def call(method: str, path: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        URL + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as reply:
            return json.loads(reply.read())
    except urllib.error.HTTPError as error:
        detail = json.loads(error.read() or b"{}").get("detail", error.reason)
        raise SystemExit(f"error: {detail}") from None
    except urllib.error.URLError as error:
        raise SystemExit(f"error: can't reach Tabby ({error.reason})") from None


def money(value: float) -> str:
    return f"{value:.2f}"


def print_bill(bill: dict) -> None:
    print(f"bill: {bill['id']}")
    print(f"subtotal: {money(bill['subtotal'])}")
    print(f"service: {money(bill['service'])}")
    print(f"tip: {money(bill['tip'])}")
    print(f"total: {money(bill['total'])}")


def main() -> int:
    parser = argparse.ArgumentParser(prog="tabby")
    commands = parser.add_subparsers(dest="command", required=True)
    bill = commands.add_parser("bill")
    bill.add_argument("items", nargs="+")
    bill.add_argument("--tip", type=float)
    show = commands.add_parser("show")
    show.add_argument("id", type=int)
    split = commands.add_parser("split")
    split.add_argument("id", type=int)
    split.add_argument("--people", type=int, required=True)
    args = parser.parse_args()
    try:
        if args.command == "bill":
            items = []
            for text in args.items:
                name, price, qty = text.rsplit(":", 2)
                items.append({"name": name, "price": float(price), "qty": int(qty)})
            body: dict = {"items": items}
            if args.tip is not None:
                body["tip_percent"] = args.tip
            print_bill(call("POST", "/bills", body))
        elif args.command == "show":
            print_bill(call("GET", f"/bills/{args.id}"))
        else:
            reply = call("GET", f"/bills/{args.id}/split?people={args.people}")
            print(f"per_person: {money(reply['per_person'])}")
    except SystemExit as stop:
        print(stop.code)
        return 1
    except ValueError:
        print("error: an item is <name>:<price>:<qty>")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
