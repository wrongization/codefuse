from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from threading import Lock
from app.config import get_settings
from app.judge_runner import run_submission_judge


class _JudgePoolManager:
    def __init__(self, max_workers: int):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.max_workers = max_workers
        self._lock = Lock()
        self._pending_futures = set()
        self._running_count = 0

    def submit(self, submission_id: int):
        """Submit a tracked task. Returns a Future."""
        def wrapper(sub_id):
            # Mark as running
            with self._lock:
                self._running_count += 1
            try:
                return run_submission_judge(sub_id)
            finally:
                with self._lock:
                    self._running_count -= 1

        future = self.executor.submit(wrapper, submission_id)

        with self._lock:
            self._pending_futures.add(future)

        # remove from pending when done
        def _on_done(f):
            with self._lock:
                try:
                    self._pending_futures.discard(f)
                except Exception:
                    pass
        future.add_done_callback(_on_done)
        return future

    def get_stats(self):
        with self._lock:
            pending = sum(1 for f in self._pending_futures if not f.done())
            running = int(self._running_count)
            return {
                'max_workers': self.max_workers,
                'pending': pending,
                'running': running
            }


@lru_cache()
def _get_manager():
    settings = get_settings()
    max_workers = getattr(settings, 'JUDGE_MAX_WORKERS', None) or 4
    return _JudgePoolManager(max_workers)


def submit_submission_judge(submission_id: int):
    """Submit a submission judge task to the global thread pool.

    Returns a concurrent.futures.Future.
    """
    mgr = _get_manager()
    return mgr.submit(submission_id)


def get_stats():
    mgr = _get_manager()
    return mgr.get_stats()
