import queue
import logging
from typing import Optional
import os

from grok3api.driver import WebDriverSingleton
from grok3api.logger import logger


class DriverPool:
    """Pool of WebDriverSingleton instances for thread-safe parallel access."""

    def __init__(self, size: int = 3):
        self._size = size
        self._pool = queue.Queue()
        logger.info(f"Initializing DriverPool with size {size}...")

        for i in range(size):
            driver_instance = WebDriverSingleton(bypass_singleton=True)
            try:
                logger.info(f"Starting driver {i + 1}/{size}...")
                driver_instance.init_driver()   # ← FIX: arranca Chrome real
            except Exception as e:
                logger.error(f"Driver {i + 1} failed to initialize: {e}")
            self._pool.put(driver_instance)

        logger.info("DriverPool initialized.")

    def _execute_with_driver(self, method_name: str, *args, **kwargs):
        """Acquire a driver, execute a method, and return it to the pool."""
        driver = self._pool.get()  # blocking — waits if all drivers are busy
        try:
            method = getattr(driver, method_name)
            return method(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error executing {method_name} in DriverPool: {e}")
            try:
                logger.info("Attempting to recover driver...")
                driver.init_driver()
            except Exception as reinit_error:
                logger.error(f"Failed to recover driver: {reinit_error}")
            raise e
        finally:
            self._pool.put(driver)  # always return to pool

    # ─────────────────────────────────────────────
    # Delegated methods — same interface as WebDriverSingleton
    # ─────────────────────────────────────────────

    def execute_script(self, script, *args):
        driver = self._pool.get()
        try:
            # Call directly on _driver to avoid stale _bind_driver_methods reference
            return driver._driver.execute_script(script, *args)
        except Exception as e:
            logger.error(f"Error executing execute_script in DriverPool: {e}")
            try:
                driver.init_driver()
            except Exception as reinit_error:
                logger.error(f"Failed to recover driver: {reinit_error}")
            raise e
        finally:
            self._pool.put(driver)

    def add_cookie(self, cookie):
        return self._execute_with_driver("add_cookie", cookie)

    def get_cookies(self):
        return self._execute_with_driver("get_cookies")

    def get(self, url):
        return self._execute_with_driver("get", url)

    def set_cookies(self, cookies_input):
        return self._execute_with_driver("set_cookies", cookies_input)

    def restart_session(self):
        return self._execute_with_driver("restart_session")

    def close_driver(self):
        return self._execute_with_driver("close_driver")

    def init_driver(self, **kwargs):
        return self._execute_with_driver("init_driver", **kwargs)

    def get_statsig(self, **kwargs):
        return self._execute_with_driver("get_statsig", **kwargs)

    def del_captcha(self, **kwargs):
        return self._execute_with_driver("del_captcha", **kwargs)

    # ─────────────────────────────────────────────
    # Properties — read from first available driver
    # ─────────────────────────────────────────────

    @property
    def TIMEOUT(self):
        driver = self._pool.get()
        t = driver.TIMEOUT
        self._pool.put(driver)
        return t

    @property
    def def_proxy(self):
        driver = self._pool.get()
        p = driver.def_proxy
        self._pool.put(driver)
        return p

    @property
    def need_proxy(self):
        driver = self._pool.get()
        n = driver.need_proxy
        self._pool.put(driver)
        return n

    @property
    def proxy_try(self):
        driver = self._pool.get()
        pt = driver.proxy_try
        self._pool.put(driver)
        return pt

    @property
    def WAS_FATAL(self):
        driver = self._pool.get()
        f = driver.WAS_FATAL
        self._pool.put(driver)
        return f