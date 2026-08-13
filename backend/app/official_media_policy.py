"""Operational policy switch for the national official-media cutover.

The default deliberately preserves legacy-compatible pilot behaviour. Operators
must explicitly enable strict mode only after the admin readiness endpoint reports
that a complete 40-question normalized/regulatory bank is constructible.
"""
from __future__ import annotations

import os

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"", "0", "false", "no", "off"}


def official_media_strict_mode_enabled() -> bool:
    """Return whether new official attempts must use strict-ready media only.

    An invalid configured value is rejected instead of silently falling back to
    compatibility mode, because a typo during national cutover must be visible.
    """
    raw = os.getenv("OFFICIAL_MEDIA_STRICT_MODE", "false").strip().lower()
    if raw in _TRUE_VALUES:
        return True
    if raw in _FALSE_VALUES:
        return False
    raise RuntimeError(
        "OFFICIAL_MEDIA_STRICT_MODE must be one of true/false, 1/0, yes/no or on/off"
    )
