"""Load ``.env`` once for every module that touches configuration."""

from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # dotenv is optional; environment variables still work
    load_dotenv = None

if load_dotenv is not None:
    _root = Path(__file__).resolve().parent.parent
    load_dotenv(_root / ".env")
    load_dotenv()  # also honour a shell-provided .env in the CWD
