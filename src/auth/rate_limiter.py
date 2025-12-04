from collections import defaultdict, deque
from time import time

_requests = defaultdict(deque)
MAX_REQUESTS = 1
WINDOW_SECONDS = 300  # 5 минут

def is_password_reset_allowed(email: str) -> bool:
    now = time()
    hist = _requests[email]
    while hist and hist[0] < now - WINDOW_SECONDS:
        hist.popleft()
    if len(hist) >= MAX_REQUESTS:
        return False
    hist.append(now)
    return True