# -*- coding: utf-8 -*-
from __future__ import annotations
import logging, functools, time, asyncio

def log_exceptions(tag: str):
    def deco(fn):
        if asyncio.iscoroutinefunction(fn):
            async def wrapper(*a, **kw):
                try:
                    return await fn(*a, **kw)
                except Exception as e:
                    logging.exception(f"{tag}: {e}")
                    raise
            return wrapper
        else:
            @functools.wraps(fn)
            def w(*a, **kw):
                try:
                    return fn(*a, **kw)
                except Exception as e:
                    logging.exception(f"{tag}: {e}")
                    raise
            return w
    return deco

def now_ts() -> int:
    return int(time.time())
