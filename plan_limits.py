from datetime import datetime, timezone

from models import User

# Mirrors glowai/src/lib/config.ts CONFIG
SCAN_LIMIT_FREE = 3
DIARY_LIMIT_FREE = 5


def is_pro(user: User) -> bool:
    if user.plan != "pro":
        return False
    if user.plan_expires_at is not None and user.plan_expires_at < datetime.now(timezone.utc):
        return False
    return True
