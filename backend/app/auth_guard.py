from collections import defaultdict, deque
from time import monotonic


class LoginRateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)

    def is_blocked(self, key: str) -> bool:
        attempts = self._recent_attempts(key)
        return len(attempts) >= self.max_attempts

    def register_failure(self, key: str) -> None:
        attempts = self._recent_attempts(key)
        attempts.append(monotonic())

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)

    def clear(self) -> None:
        self._attempts.clear()

    def _recent_attempts(self, key: str) -> deque[float]:
        attempts = self._attempts[key]
        cutoff = monotonic() - self.window_seconds
        while attempts and attempts[0] < cutoff:
            attempts.popleft()
        return attempts
