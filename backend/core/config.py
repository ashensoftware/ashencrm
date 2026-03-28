import platform
import asyncio

H3_RESOLUTION = 8


def setup_windows_asyncio():
    """Configura ProactorEventLoop en Windows (crítico para Playwright)."""
    if platform.system() == "Windows":
        try:
            if not isinstance(
                asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy
            ):
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            pass


setup_windows_asyncio()
