from __future__ import annotations

import uvicorn

from cleartrace_core_api.app import create_app
from cleartrace_core_api.config import Settings


def run() -> None:
    settings = Settings()
    app = create_app(settings)
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
    run()
