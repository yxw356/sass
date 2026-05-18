#!/usr/bin/env python3
"""Download the default embedding model into ./models/bge-small-zh-v1.5."""

from pathlib import Path

from huggingface_hub import snapshot_download

REPO_ID = "BAAI/bge-small-zh-v1.5"
DEST = Path(__file__).resolve().parent.parent / "models" / "bge-small-zh-v1.5"


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {REPO_ID} -> {DEST}")
    print("Tip: use HF_ENDPOINT=https://hf-mirror.com if huggingface.co is unreachable")
    snapshot_download(REPO_ID, local_dir=str(DEST))
    print(f"Done. Set EMBEDDING_MODEL={DEST} or restart the app (auto-detects local model).")


if __name__ == "__main__":
    main()
