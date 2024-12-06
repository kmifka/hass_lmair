"""Rate limiter for Light Manager Air."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, TypeVar, Generic, TypedDict
from collections import defaultdict, deque

_LOGGER = logging.getLogger(__name__)

# Generic type for priority
P = TypeVar('P')

class PriorityConfig(TypedDict):
    """Type definition for priority configuration."""
    min_calls: int
    time_window: int
    rate_limit: Optional[int]
    rate_window: Optional[float]
    latest_only: Optional[bool]

class RateLimiter(Generic[P]):
    """Token bucket rate limiter implementation with priority for events."""
    
    def __init__(
        self,
        default_rate_limit: int,
        default_time_window: float,
        priority_config: Optional[Dict[P, PriorityConfig]] = None
    ):
        """Initialize the rate limiter.
        
        :param default_rate_limit: Default maximum number of requests per time window
        :param default_time_window: Default time window in seconds
        :param priority_config: Configuration for each priority
        """
        self._default_rate_limit: int = default_rate_limit
        self._default_time_window: float = default_time_window
        self._tokens: int = default_rate_limit
        self._last_update: datetime = datetime.now()
        self._lock: asyncio.Lock = asyncio.Lock()
        self._token_event: asyncio.Event = asyncio.Event()
        self._token_event.set()  # Tokens sind anfänglich verfügbar
        self._queues: defaultdict[P, deque[P]] = defaultdict(deque)
        self._priority_config: Optional[Dict[P, PriorityConfig]] = priority_config
        self._priority_counters: defaultdict[P, int] = defaultdict(int)
        self._last_reset_times: defaultdict[P, datetime] = defaultdict(lambda: datetime.now())
        self._priority_locks: Dict[P, asyncio.Lock] = defaultdict(asyncio.Lock)
        # Starten der Token-Auffüllung
        asyncio.create_task(self._replenish_tokens())

    async def _replenish_tokens(self):
        while True:
            async with self._lock:
                now = datetime.now()
                time_passed = (now - self._last_update).total_seconds()
                if time_passed >= self._default_time_window:
                    self._tokens = self._default_rate_limit
                    self._last_update = now
                    self._token_event.set()  # Tokens sind wieder verfügbar
            await asyncio.sleep(self._default_time_window)

    async def acquire(self, priority: P) -> None:
        """Acquire a token, waiting if necessary."""
        # Prioritätskonfiguration abrufen
        config = self._priority_config.get(priority, {}) if self._priority_config else {}
        latest_only = config.get('latest_only', False)
        
        if latest_only:
            # Bestehenden Lock für diese Priorität abbrechen
            if priority in self._priority_locks:
                old_lock = self._priority_locks[priority]
                if old_lock.locked():
                    old_lock._locked = False  # Erzwungenes Freigeben des alten Locks
            
            # Neuen Lock für diese Priorität erstellen
            self._priority_locks[priority] = asyncio.Lock()
            priority_lock = self._priority_locks[priority]
            
            async with priority_lock:
                await self._acquire_token(priority)
        else:
            # Kein latest_only, normaler Ablauf
            await self._acquire_token(priority)

    async def _acquire_token(self, priority: P):
        await self._token_event.wait()
        async with self._lock:
            # Prioritätsspezifische Rate Limits abrufen
            config = self._priority_config.get(priority, {}) if self._priority_config else {}
            rate_limit = config.get('rate_limit', self._default_rate_limit)
            rate_window = config.get('rate_window', self._default_time_window)

            # Rate Limiting überspringen, wenn nicht definiert
            if rate_limit is None or rate_window is None:
                self._queues[priority].append(priority)
                return

            if self._tokens > 0:
                self._tokens -= 1
                if self._tokens == 0:
                    self._token_event.clear()  # Keine Tokens mehr verfügbar
                self._queues[priority].append(priority)
            else:
                # Keine Tokens verfügbar, warten bis zur nächsten Auffüllung
                self._token_event.clear()
                # Wiederholen ohne while True durch rekursiven Aufruf
                await self.acquire(priority)

    async def process_queues(self) -> None:
        """Process the queues based on priority."""
        while True:
            async with self._lock:
                now = datetime.now()
                if self._priority_config:
                    for priority in self._queues.keys():
                        config = self._priority_config.get(priority, {})
                        if (now - self._last_reset_times[priority]).total_seconds() >= config.get('time_window', 0):
                            self._priority_counters[priority] = 0
                            self._last_reset_times[priority] = now

                for priority in sorted(self._queues.keys()):
                    if self._queues[priority]:
                        if self._priority_config:
                            config = self._priority_config.get(priority, {})
                            min_calls = config.get('min_calls', 0)
                            if min_calls == 0 or self._priority_counters[priority] < min_calls:
                                # Process task
                                self._queues[priority].popleft()
                                self._priority_counters[priority] += 1
                                break
                        else:
                            # Process task without priority consideration
                            self._queues[priority].popleft()
                            break
            await asyncio.sleep(0.1)  # Adjust sleep time as needed