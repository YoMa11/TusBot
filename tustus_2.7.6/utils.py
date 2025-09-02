from __future__ import annotations
import logging
log = logging.getLogger("tustus.utils")

def chunked(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]
