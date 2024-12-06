import asyncio
import unittest

from custom_components.light_manager_air.const import Priority
from custom_components.light_manager_air.rate_limiter import RateLimiter


class TestRateLimiter(unittest.TestCase):
    def setUp(self):
        self.rate_limiter = RateLimiter[Priority](rate_limit=5, time_window=1.0)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_acquire_tokens(self):
        async def acquire_tokens():
            for _ in range(5):
                await self.rate_limiter.acquire(priority=Priority.EVENT)
            return self.rate_limiter._tokens

        result = self.loop.run_until_complete(acquire_tokens())
        self.assertEqual(result, 0)  # All tokens should be acquired

    def test_token_replenishment(self):
        async def acquire_and_wait():
            await self.rate_limiter.acquire(priority=Priority.EVENT)
            tokens_after_acquire = self.rate_limiter._tokens
            await asyncio.sleep(1.1)  # Wait for replenishment
            return tokens_after_acquire, self.rate_limiter._tokens

        initial_tokens, replenished_tokens = self.loop.run_until_complete(acquire_and_wait())
        self.assertEqual(initial_tokens, 4)  # One token should be acquired
        self.assertGreaterEqual(replenished_tokens, 5)  # Tokens should be replenished

    def test_priority_ordering(self):
        async def test_priorities():
            # Add tasks with different priorities
            await self.rate_limiter.acquire(priority=Priority.POLLING)  # Lower priority
            await self.rate_limiter.acquire(priority=Priority.EVENT)  # Higher priority
            
            # Check queue contents
            return (len(self.rate_limiter._queues[Priority.EVENT]), 
                   len(self.rate_limiter._queues[Priority.POLLING]))

        high_priority_count, low_priority_count = self.loop.run_until_complete(test_priorities())
        self.assertEqual(high_priority_count, 1)
        self.assertEqual(low_priority_count, 1)

    def test_priority_config(self):
        priority_config = {
            Priority.POLLING: {'min_calls': 3, 'time_window': 60}
        }
        rate_limiter = RateLimiter[Priority](rate_limit=5, time_window=1.0, priority_config=priority_config)

        async def test_with_config():
            await rate_limiter.acquire(priority=Priority.POLLING)
            return (rate_limiter._priority_config[Priority.POLLING]['min_calls'], 
                   rate_limiter._priority_config[Priority.POLLING]['time_window'])

        min_calls, time_window = self.loop.run_until_complete(test_with_config())
        self.assertEqual(min_calls, 3)
        self.assertEqual(time_window, 60)

if __name__ == '__main__':
    unittest.main() 