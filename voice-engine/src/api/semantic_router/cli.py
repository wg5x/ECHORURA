from __future__ import annotations

import json
import sys

from .router import SemanticRouter


def main() -> None:
    text = " ".join(sys.argv[1:]).strip()
    decision = SemanticRouter().route_text("cli-session", "turn-1", text, source="manual_text")
    print(json.dumps(decision, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
