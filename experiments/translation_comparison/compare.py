"""Show saved MADLAD and Qwen subtitle translations side by side."""

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent / "results"


def main():
    saved = {}
    for provider in ("madlad", "qwen"):
        path = HERE / f"{provider}.json"
        if not path.exists():
            raise SystemExit(f"Missing {path}; run run.py with {provider} first.")
        saved[provider] = json.loads(path.read_text(encoding="utf-8"))

    madlad = {item["id"]: item for item in saved["madlad"]["cases"]}
    qwen = {item["id"]: item for item in saved["qwen"]["cases"]}
    for case_id in sorted(madlad.keys() | qwen.keys()):
        left, right = madlad.get(case_id), qwen.get(case_id)
        if left is None or right is None:
            print(f"Skipping {case_id}: not present in both files.")
            continue
        if left["original"] != right["original"]:
            print(f"Skipping {case_id}: source texts differ.")
            continue
        print(f'\n[{case_id}] {left["original"]}')
        print(f'  MADLAD: {left["translated"]}')
        print(f'  Qwen:   {right["translated"]}')


if __name__ == "__main__":
    main()
