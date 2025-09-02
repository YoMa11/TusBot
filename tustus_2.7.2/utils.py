from __future__ import annotations
import logging, sys, traceback

def setup_logging():
    root = logging.getLogger()
    if not root.handlers:
        root.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        ch = logging.StreamHandler(sys.stdout); ch.setFormatter(fmt); root.addHandler(ch)
        fh = logging.FileHandler("bot.log"); fh.setFormatter(fmt); root.addHandler(fh)
    logging.info("📝 logging to ./bot.log")

def exc_str(e: BaseException) -> str:
    return "".join(traceback.format_exception(e)).strip()
