from __future__ import annotations

import argparse
import json

from .contracts import AgentRequest
from .factory import build_agent


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the evidence-grounded support agent")
    parser.add_argument("message")
    parser.add_argument("--brand", default="AmazonHelp")
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true", help="print the full machine-readable result")
    args = parser.parse_args()
    result = build_agent(args.root).run(AgentRequest(brand_id=args.brand, message=args.message))
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return
    print(f"Intent: {result.intent} ({result.intent_confidence:.2f})")
    print(f"Draft reply: {result.draft}")
    print(f"Decision: {result.route.value}")
    print(f"Reason: {result.reason}")
    print("Historical evidence:")
    for case in result.evidence:
        print(f"- {case.case_id}: {case.problem_excerpt}")


if __name__ == "__main__":
    main()
