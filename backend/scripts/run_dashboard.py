import asyncio
import platform
import sys
from pathlib import Path

if platform.system() == "Windows":
    try:

        if not isinstance(
            asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy
        ):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

import uvicorn

sys.path.append(str(Path(__file__).parent.parent))

if __name__ == "__main__":
    print("Dashboard: http://localhost:8000")
    uvicorn.run(
        "src.dashboard.backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        loop="asyncio",
    )
