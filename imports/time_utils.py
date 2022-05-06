from contextlib import contextmanager
from time import perf_counter

from .logging import get_logger


logger = get_logger(__name__)

@contextmanager
def timer(message=None):
    t0 = perf_counter()
    yield lambda: round(t1 - t0, 3)
    t1 = perf_counter()
    if message:
        logger.info(f'{message} in {round(1000 * (t1 - t0), 3)} msecs')










