"""
db_sync.py
----------
Sync comparables.db with a private GitHub repository.

On startup  → download the latest DB from GitHub if not present locally.
After write → push the updated DB back to GitHub so changes persist.

Required Streamlit secrets (in .streamlit/secrets.toml or the Cloud dashboard):

    [github]
    token     = "ghp_xxxxxxxxxxxx"        # Personal Access Token (repo scope)
    db_owner  = "filipejrcorreia"
    db_repo   = "real-estate-comparables-db"
    db_branch = "main"
    db_path   = "comparables.db"
"""

from __future__ import annotations

import base64
import os

import requests
import streamlit as st


# ── helpers ───────────────────────────────────────────────────────────────────

def _cfg() -> dict:
    """Return GitHub config from Streamlit secrets."""
    gh = st.secrets.get("github", {})
    return {
        "token":  gh.get("token", ""),
        "owner":  gh.get("db_owner",  "filipejrcorreia"),
        "repo":   gh.get("db_repo",   "real-estate-comparables-db"),
        "branch": gh.get("db_branch", "main"),
        "path":   gh.get("db_path",   "comparables.db"),
    }


def _api_url(cfg: dict) -> str:
    return (
        f"https://api.github.com/repos/{cfg['owner']}/{cfg['repo']}"
        f"/contents/{cfg['path']}"
    )


def _headers(cfg: dict) -> dict:
    return {
        "Authorization": f"token {cfg['token']}",
        "Accept": "application/vnd.github.v3+json",
    }


# ── public API ────────────────────────────────────────────────────────────────

def fetch_db(local_path: str) -> bool:
    """
    Download the database from GitHub into local_path.
    Returns True on success, False on failure.
    Called once at app startup if the db file is missing.
    """
    # Always pull the latest DB from GitHub on startup.
    # The file is small (~700 KB) so the download is fast, and this guarantees
    # the app never gets stuck with a stale/partial DB from a previous run.

    cfg = _cfg()
    if not cfg["token"]:
        st.warning(
            "⚠️ No GitHub token found in secrets — database cannot be fetched. "
            "Add `[github] token = '...'` to your Streamlit secrets."
        )
        return False

    try:
        # Use the Git blobs API to get the blob SHA first, then stream the raw
        # content via the media type header.  The Contents API silently returns
        # an empty `content` field (or 403) for files larger than ~1 MB.
        cfg_hdrs = _headers(cfg)

        # Step 1: get file metadata to find the blob SHA
        r = requests.get(
            _api_url(cfg),
            headers=cfg_hdrs,
            params={"ref": cfg["branch"]},
            timeout=30,
        )
        r.raise_for_status()
        meta = r.json()

        # Step 2: if content is provided inline (small file), use it directly;
        #         otherwise download via the raw download_url.
        inline = meta.get("content", "").replace("\n", "")
        if inline:
            raw = base64.b64decode(inline)
        else:
            download_url = meta.get("download_url")
            if not download_url:
                raise ValueError("GitHub returned no content and no download_url.")
            r2 = requests.get(download_url, headers=cfg_hdrs, timeout=120)
            r2.raise_for_status()
            raw = r2.content

        with open(local_path, "wb") as f:
            f.write(raw)
        return True
    except Exception as exc:
        st.error(f"Failed to fetch database from GitHub: {exc}")
        return False


@st.cache_data(ttl=0, show_spinner=False)
def _get_remote_sha(url: str, headers: dict, branch: str) -> str | None:
    """Cached one-request fetch of the current file SHA."""
    try:
        r = requests.get(url, headers=headers, params={"ref": branch}, timeout=15)
        r.raise_for_status()
        return r.json().get("sha")
    except Exception:
        return None


def push_db(local_path: str, commit_msg: str = "Update database") -> bool:
    """
    Push the local database file to GitHub using the Git Data API.
    Handles files of any size (up to 100 MB) — avoids the ~1 MB limit
    of the Contents API that causes HTTP 422 errors.
    Returns True on success, False on failure.
    """
    cfg = _cfg()
    if not cfg["token"]:
        return False  # silently skip — warning already shown at startup

    base = f"https://api.github.com/repos/{cfg['owner']}/{cfg['repo']}"
    hdrs = _headers(cfg)
    branch = cfg["branch"]

    try:
        with open(local_path, "rb") as f:
            raw_bytes = f.read()
        content_b64 = base64.b64encode(raw_bytes).decode()

        # ── Step 1: create a blob with the new file content ──────────────────
        r = requests.post(
            f"{base}/git/blobs",
            headers=hdrs,
            json={"content": content_b64, "encoding": "base64"},
            timeout=120,
        )
        r.raise_for_status()
        blob_sha = r.json()["sha"]

        # ── Step 2: get the current branch tip commit SHA + its tree SHA ─────
        r = requests.get(
            f"{base}/git/refs/heads/{branch}",
            headers=hdrs,
            timeout=15,
        )
        r.raise_for_status()
        tip_sha = r.json()["object"]["sha"]

        r = requests.get(
            f"{base}/git/commits/{tip_sha}",
            headers=hdrs,
            timeout=15,
        )
        r.raise_for_status()
        base_tree_sha = r.json()["tree"]["sha"]

        # ── Step 3: create a new tree that updates only our DB file ──────────
        r = requests.post(
            f"{base}/git/trees",
            headers=hdrs,
            json={
                "base_tree": base_tree_sha,
                "tree": [{
                    "path": cfg["path"],
                    "mode": "100644",
                    "type": "blob",
                    "sha":  blob_sha,
                }],
            },
            timeout=30,
        )
        r.raise_for_status()
        new_tree_sha = r.json()["sha"]

        # ── Step 4: create a commit ───────────────────────────────────────────
        r = requests.post(
            f"{base}/git/commits",
            headers=hdrs,
            json={
                "message": commit_msg,
                "tree":    new_tree_sha,
                "parents": [tip_sha],
            },
            timeout=30,
        )
        r.raise_for_status()
        new_commit_sha = r.json()["sha"]

        # ── Step 5: advance the branch ref ───────────────────────────────────
        r = requests.patch(
            f"{base}/git/refs/heads/{branch}",
            headers=hdrs,
            json={"sha": new_commit_sha},
            timeout=15,
        )
        r.raise_for_status()
        # Invalidate cached SHA so the next push fetches fresh state
        _get_remote_sha.clear()
        return True

    except Exception as exc:
        st.warning(f"Record saved locally, but GitHub sync failed: {exc}")
        return False
