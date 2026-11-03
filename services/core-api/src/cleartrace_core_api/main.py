from __future__ import annotations

import uvicorn

from cleartrace_core_api.app import create_app
from cleartrace_core_api.config import Settings


def run() -> None:
    settings = Settings()
    app = create_app(settings)
    # server_header=False: no component version in responses (ASVS V14.3.3).
    uvicorn.run(app, host=settings.api_host, port=settings.api_port, server_header=False)


if __name__ == "__main__":
    run()
