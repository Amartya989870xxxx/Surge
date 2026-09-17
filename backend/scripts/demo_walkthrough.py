"""Drive a Surge investigation against a running server and print the live timeline.

Usage:
  python scripts/demo_walkthrough.py                       # primary demo, asks before approving
  python scripts/demo_walkthrough.py --fail slack_unavailable --auto-approve
  python scripts/demo_walkthrough.py --reasoning llm --base-url http://localhost:8000
"""

import argparse
import json
import sys

import httpx

PRIMARY = (
    "Something changed after yesterday's release. Our conversion rate dropped. "
    "Investigate the cause and coordinate the response."
)
TTY = sys.stdout.isatty()
COLORS = {
    "PLAN": "35", "SHEETS": "32", "GITHUB": "37", "SLACK": "36", "EVIDENCE": "34", "HYPOTHESIS": "33",
    "SYNTHESIS": "1;33", "ACTION": "1;35", "VERIFICATION": "1;32", "DEGRADED": "1;31", "POLICY": "31", "SYSTEM": "90",
}
DETAIL_TYPES = {"PLAN", "DEGRADED", "POLICY", "SYNTHESIS", "SUFFICIENCY_CHECK", "ACTION_BLOCKED", "VERIFICATION"}


def paint(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if TTY else text


def show(event: dict) -> None:
    if event["event_type"] in ("TOOL_CALL_STARTED", "STATUS_CHANGED"):
        return
    clock = event["timestamp"][11:19]
    category = event["category"]
    duration = f"  {event['duration_ms']}ms" if event.get("duration_ms") is not None else ""
    print(f"{paint(clock, '90')}  {paint(f'{category:<12}', COLORS.get(category, '0'))} {event['title']}{paint(duration, '90')}")
    if event["event_type"] in DETAIL_TYPES and event.get("summary"):
        print(paint(f"{'':22}{event['summary'][:220]}", "90"))


def stream(client: httpx.Client, inv_id: str, after: int) -> tuple[int, str]:
    """Returns (last sequence, reason) where reason is 'approval' or 'end'."""
    name = None
    with client.stream("GET", f"/api/investigations/{inv_id}/stream", params={"after": after}, timeout=None) as resp:
        for line in resp.iter_lines():
            if line.startswith("event: "):
                name = line[7:]
                if name == "end":
                    return after, "end"
            elif line.startswith("data: ") and name:
                event = json.loads(line[6:])
                after = event["sequence"]
                show(event)
                if event["event_type"] == "APPROVAL_REQUIRED":
                    return after, "approval"
    return after, "end"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--request", default=PRIMARY)
    parser.add_argument("--fail", action="append", help="Fault preset to inject (repeatable)")
    parser.add_argument("--scenario", help="Seeded demo world, e.g. payment_provider_01")
    parser.add_argument("--reasoning", choices=["llm", "heuristic"])
    parser.add_argument("--auto-approve", action="store_true")
    args = parser.parse_args()

    body = {"request": args.request, "inject_failures": args.fail or []}
    if args.reasoning:
        body["reasoning"] = args.reasoning
    if args.scenario:
        body["scenario_id"] = args.scenario

    with httpx.Client(base_url=args.base_url, timeout=30) as client:
        created = client.post("/api/investigations", json=body)
        if created.status_code >= 400:
            sys.exit(f"Could not start investigation: {created.text}")
        inv = created.json()
        print(paint("SURGE", "1;37"), f"investigation {inv['id']}  ·  connectors {inv['connector_mode']}  ·  reasoning {inv['reasoning_mode']}")
        if inv["injected_faults"]:
            print(paint(f"Injected faults (disclosed): {inv['injected_faults']}", "31"))
        print(paint(f"“{args.request}”\n", "1"))

        after, reason = 0, "start"
        while reason != "end":
            after, reason = stream(client, inv["id"], after)
            if reason == "approval":
                action = next(a for a in client.get(f"/api/investigations/{inv['id']}/actions").json() if a["approval_status"] == "PENDING")
                print(paint(f"\n  ACTION REQUIRES APPROVAL  [{action['risk_level']}]  {action['title']}", "1;35"))
                print(f"  Why: {action['rationale']}")
                approve = args.auto_approve or input("  Approve? [y/N] ").strip().lower() == "y"
                client.post(f"/api/investigations/{inv['id']}/approve", json={"action_id": action["id"], "approved": approve})
                print()

        detail = client.get(f"/api/investigations/{inv['id']}").json()
        print(paint("\nRESULT", "1;37"), detail["status"], "·", detail["outcome"], "· confidence", detail["confidence"])
        print(detail["final_summary"])
        for action in client.get(f"/api/investigations/{inv['id']}/actions").json():
            print(f"Action: {action['title']} → {action['execution_status']} / {action['verification_status']}"
                  + (f"  {action['external_url']}" if action.get("external_url") else ""))


if __name__ == "__main__":
    main()
