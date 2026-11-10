# file: free_slots.py
import re

_T = re.compile(r"(\d{2}):(\d{2})")


def _to_min(t):
    if not isinstance(t, str):
        raise ValueError(f"bad time {t!r}")
    m = _T.fullmatch(t)
    if not m:
        raise ValueError(f"bad time {t!r}")
    h, mi = int(m.group(1)), int(m.group(2))
    if t == "24:00":
        return 1440
    if h > 23 or mi > 59:
        raise ValueError(f"bad time {t!r}")
    return h * 60 + mi


def _fmt(m):
    return f"{m // 60:02d}:{m % 60:02d}"


def free_slots(busy, day_start, day_end, min_minutes=0):
    if isinstance(min_minutes, bool) or not isinstance(min_minutes, int) or min_minutes < 0:
        raise ValueError("min_minutes must be a non-negative int")
    ds, de = _to_min(day_start), _to_min(day_end)
    if ds >= de:
        raise ValueError("day_start must be before day_end")
    iv = []
    for item in busy:
        s, e = item
        s, e = _to_min(s), _to_min(e)
        if s >= e:
            raise ValueError("busy start must be before end")
        s, e = max(s, ds), min(e, de)
        if s < e:
            iv.append((s, e))
    iv.sort()
    out, cur = [], ds
    for s, e in iv:
        if s > cur:
            out.append((cur, s))
        cur = max(cur, e)
    if cur < de:
        out.append((cur, de))
    return [(_fmt(s), _fmt(e)) for s, e in out if e - s >= max(min_minutes, 1)]
