from __future__ import annotations

try:
    import orjson
    ORJSON_AVAILABLE = True
except ImportError:
    import json
    ORJSON_AVAILABLE = False

from pathlib import Path
from typing import Any


def dumps(data: Any) -> str:
    if ORJSON_AVAILABLE:
        return orjson.dumps(data, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS).decode()
    else:
        return json.dumps(data, indent=2, sort_keys=True)


def dump_to_file(path: str | Path, data: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if ORJSON_AVAILABLE:
        p.write_bytes(orjson.dumps(data, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS))
    else:
        p.write_text(json.dumps(data, indent=2, sort_keys=True))
