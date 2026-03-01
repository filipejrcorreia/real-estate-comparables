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
import time

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
    if os.path.exists(local_path):
        return True

    cfg = _cfg()
    if not cfg["token"]:
        st.warning(
            "⚠️ No GitHub token found in secrets — database cannot be fetched. "
            "Add `[github] token = '...'` to your Streamlit secrets."
        )
        return False

    try:
        r = requests.get(
            _api_url(cfg),
            headers=_headers(cfg),
            params={"ref": cfg["branch"]},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        raw = base64.b64decode(data["content"])
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
    Push the local database file to GitHub.
    Returns True on success, False on failure.
    Called after every write operation so new records persist.
    """
    cfg = _cfg()
    if not cfg["token"]:
        return False  # silently skip — warning already shown at startup

    try:
        with open(local_path, "rb") as f:
            content_b64 = base64.b64encode(f.read()).decode()

        url = _api_url(cfg)
        hdrs = _headers(cfg)

        # Get the current SHA (needed by GitHub API to update an existing file)
        sha = _get_remote_sha(url, frozenset(hdrs.items()), cfg["branch"])
        # Clear the cache so next call fetches fresh SHA
        _get_remote_sha.clear()

        payload: dict = {
            "message": commit_msg,
            "content": content_b64,
            "branch":  cfg["branch"],
        }
        if sha:
            payload["sha"] = sha

        r = requests.put(url, headers=hdrs, json=payload, timeout=60)
        r.raise_for_status()
        return True
    except Exception as exc:
        st.warning(f"Record saved locally, but GitHub sync failed: {exc}")
        return False
