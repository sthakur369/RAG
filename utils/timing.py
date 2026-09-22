import time

from utils.logger import logger


def start_timer():
    return time.perf_counter()


def print_timing(name, description, start):
    elapsed = time.perf_counter() - start

    message = (
        f"{name:<30} "
        f"{elapsed:>8.4f}s | {description}"
    )

    print(f"[TIMING] {message}")
    logger.info(f"[TIMING] {message}")

    return elapsed