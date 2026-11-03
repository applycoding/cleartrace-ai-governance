from __future__ import annotations

import uvicorn

from cleartrace_core_api.app import create_app


def run() -> None:
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    run()
