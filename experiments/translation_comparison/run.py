"""Save real translation outputs from the currently selected provider."""

import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen


HERE = Path(__file__).resolve().parent


def request_json(base_url, endpoint, payload=None):
    headers = {"Content-Type": "application/json"}
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(base_url.rstrip("/") + endpoint, data=data, headers=headers)
    with urlopen(request, timeout=240) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()

    ready = request_json(args.url, "/ready")
    if not ready.get("ready"):
        raise SystemExit("Translation API is not ready.")
    provider = ready.get("provider")
    if provider not in ("madlad", "qwen"):
        raise SystemExit(f"Unexpected translation provider: {provider!r}")

    cases = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
    outputs = []
    for case in cases:
        response = request_json(args.url, "/v1/translate", {
            "text": case["text"],
            "source": case["source"],
            "target": "th",
        })
        outputs.append({
            "id": case["id"],
            "source": case["source"],
            "original": case["text"],
            "translated": response["translated"],
        })
        print(f'{case["id"]}: {response["translated"]}')

    path = HERE / "results" / f"{provider}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "provider": provider,
        "model": ready["model"],
        "cases": outputs,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Saved: {path}")


if __name__ == "__main__":
    main()
