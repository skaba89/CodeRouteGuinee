from __future__ import annotations

import logging

from app.soc_config import get_soc_settings
from app.soc_privacy import SOCPrivacyFilter


def install_soc_log_filter() -> bool:
    """Ajoute la barrière de pseudonymisation après le filtre secret existant."""
    if not get_soc_settings().enabled:
        return False
    root = logging.getLogger()
    for handler in root.handlers:
        if not any(isinstance(item, SOCPrivacyFilter) for item in handler.filters):
            handler.addFilter(SOCPrivacyFilter())
    return True
