"""
push_db_to_github.py
--------------------
One-off script to push the local comparables.db to the GitHub DB repo.
Run this whenever you want to seed or reset the remote database.

Usage:
    python3 push_db_to_github.py --token ghp_xxxx
    # OR set env var:
    GITHUB_TOKEN=ghp_xxxx python3 push_db_to_github.py
"""

import argparse
import base64
import os
import sys

import requests

# ── config ────────────────────────────────────────────────────────────────────
DB_OWNER  = "filipejrcorreia"
DB_REPO   = "real-estate-comparables-db"
DB_BRANCH = "main"
DB_PATH   = "comparables.db"
LOCAL_DB  = os.path.join(os.path.dirname(__file__), "comparables.db")
BASE_URL  = f"https://api.github.com/repos/{DB_OWNER}/{DB_REPO}"


def push(token: str) -> None:
    hdrs = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    if not os.path.exists(LOCAL_DB):
        sys.exit(f"ERROR: {LOCAL_DB} not found.")

    with open(LOCAL_DB, "rb") as f:
        raw = f.read()

    print(f"DB file: {LOCAL_DB}  ({len(raw):,} bytes)")
    content_b64 = base64.b64encode(raw).decode()

    # ── Step 1: create blob ───────────────────────────────────────────────────
    print("Step 1/5: Creating blob…")
    r = requests.post(
        f"{BASE_URL}/git/blobs",
        headers=hdrs,
        json={"content": content_b64, "encoding": "base64"},
        timeout=120,
    )
    r.raise_for_status()
    blob_sha = r.json()["sha"]
    print(f"          blob SHA: {blob_sha[:12]}…")

    # ── Step 2: get branch tip ────────────────────────────────────────────────
    print("Step 2/5: Getting branch tip…")
    r = requests.get(f"{BASE_URL}/git/refs/heads/{DB_BRANCH}", headers=hdrs, timeout=15)
    r.raise_for_status()
    tip_sha = r.json()["object"]["sha"]
    print(f"          tip SHA:  {tip_sha[:12]}…")

    # ── Step 3: get base tree ─────────────────────────────────────────────────
    print("Step 3/5: Getting base tree…")
    r = requests.get(f"{BASE_URL}/git/commits/{tip_sha}", headers=hdrs, timeout=15)
    r.raise_for_status()
    base_tree_sha = r.json()["tree"]["sha"]

    # ── Step 4: create new tree ───────────────────────────────────────────────
    print("Step 4/5: Creating new tree…")
    r = requests.post(
        f"{BASE_URL}/git/trees",
        headers=hdrs,
        json={
            "base_tree": base_tree_sha,
            "tree": [{
                "path": DB_PATH,
                "mode": "100644",
                "type": "blob",
                "sha":  blob_sha,
            }],
        },
        timeout=30,
    )
    r.raise_for_status()
    new_tree_sha = r.json()["sha"]

    # ── Step 5: create commit and advance ref ────────────────────────────────
    print("Step 5/5: Creating commit and advancing branch…")
    r = requests.post(
        f"{BASE_URL}/git/commits",
        headers=hdrs,
        json={
            "message": f"Seed DB: {len(raw):,} bytes ({LOCAL_DB.split('/')[-1]})",
            "tree":    new_tree_sha,
            "parents": [tip_sha],
        },
        timeout=30,
    )
    r.raise_for_status()
    new_commit_sha = r.json()["sha"]

    r = requests.patch(
        f"{BASE_URL}/git/refs/heads/{DB_BRANCH}",
        headers=hdrs,
        json={"sha": new_commit_sha},
        timeout=15,
    )
    r.raise_for_status()

    print(f"\n✅ Done — commit {new_commit_sha[:12]} pushed to {DB_OWNER}/{DB_REPO}")
    print(f"   https://github.com/{DB_OWNER}/{DB_REPO}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Push local DB to GitHub DB repo.")
    parser.add_argument("--token", default="", help="GitHub Personal Access Token")
    args = parser.parse_args()

    token = args.token or os.environ.get("GITHUB_TOKEN", "")
    if not token:
        sys.exit(
            "ERROR: provide a token via --token ghp_xxxx  "
            "or set GITHUB_TOKEN env var."
        )

    push(token)
