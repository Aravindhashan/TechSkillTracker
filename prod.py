"""Production entry point for Hugging Face Spaces (Streamlit SDK).

Prints a small health summary (backend type + posting count — never secrets)
and then launches the Streamlit app.  Kept dependency-light on purpose: the
only hard imports are the store and the standard library; Streamlit is loaded
lazily inside :func:`start_streamlit` so ``--check-only`` stays a fast smoke
test.

Usage::

    python prod.py [--host 0.0.0.0] [--port 7860] [--check-only]
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from modules import store as job_store

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 7860
APP_PY = "app.py"


def health_check() -> dict[str, Any]:
    """Summarise store health without ever exposing secrets."""
    warnings: list[str] = []
    url = job_store.database_url()
    backend = "postgres" if job_store.use_postgres() else "sqlite"

    if not url:
        warnings.append(
            "DATABASE_URL not set; falling back to local SQLite. "
            "Spaces disk is ephemeral — set DATABASE_URL for persistent data."
        )
    if not os.getenv("JSEARCH_API_KEY"):
        warnings.append("JSEARCH_API_KEY not set; ingestion cron will be skipped.")

    try:
        job_store.init_db()
    except Exception as exc:  # pragma: no cover - DB unreachable
        warnings.append(f"Could not initialise store: {exc}")

    try:
        available = bool(job_store.store_available())
        postings = int(job_store.count_postings()) if available else 0
    except Exception as exc:  # pragma: no cover - DB unreachable
        available = False
        postings = 0
        warnings.append(f"Could not query store: {exc}")

    if available and postings == 0:
        warnings.append("Store is empty; run ingestion to populate postings.")

    return {
        "backend": backend,
        "store_available": available,
        "postings": postings,
        "warnings": warnings,
    }


def build_streamlit_command(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, app_py: str = APP_PY) -> list[str]:
    return [
        "streamlit",
        "run",
        app_py,
        "--server.address",
        host,
        "--server.port",
        str(port),
    ]


def start_streamlit(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """Replace the current process with the Streamlit server (no return)."""
    from streamlit.web.cli import main as streamlit_main

    sys.argv = build_streamlit_command(host=host, port=port)
    streamlit_main()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Tech Skill Tracker production entry point")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="print the health summary and exit without starting the server",
    )
    args = parser.parse_args(argv)

    health = health_check()
    print(f"[prod] health: backend={health['backend']} postings={health['postings']}")
    for warning in health["warnings"]:
        print(f"[prod] warning: {warning}")

    if args.check_only:
        return 0

    start_streamlit(host=args.host, port=args.port)
    return 0  # pragma: no cover - never returns after server start


if __name__ == "__main__":
    raise SystemExit(main())
