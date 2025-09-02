# -*- coding: utf-8 -*-
from __future__ import annotations
import os

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

PACKAGE_VERSION = "2.5.10b"
INTERVAL = int(os.getenv("TUSTUS_INTERVAL", "60"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
DB_PATH = os.getenv("DB_PATH", os.path.abspath(os.path.join(os.getcwd(), "flights.db")))

def enforce_local_imports():
    import sys, importlib, inspect, os as _os
    cwd = _os.path.abspath(_os.getcwd())
    if sys.path[0] != cwd:
        sys.path = [cwd] + [p for p in sys.path if _os.path.abspath(p) != cwd]
    for name in ("config","db","handlers","logic","telegram_view","utils"):
        m = importlib.import_module(name)
        origin = inspect.getsourcefile(m) or inspect.getfile(m)
        if not origin or not _os.path.abspath(origin).startswith(cwd):
            raise ImportError(f"Module {name} not loaded from run dir: {origin} (cwd={cwd})")
    return True
