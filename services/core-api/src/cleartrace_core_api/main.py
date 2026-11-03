from __future__ import annotations

import logging.config
from pathlib import Path

import uvicorn

from cleartrace_core_api.app import create_app
from cleartrace_core_api.config import Settings
from cleartrace_core_api.logging_setup import configure_logging, load_logging_dict


def run() -> None:
    settings = Settings()
    if settings.log_config_path:
        cfg_path = Path(settings.log_config_path)
        logging.config.dictConfig(load_logging_dict(cfg_path))
    else:
        configure_logging(json_logs=settings.json_logs)
    app = create_app(settings)
    # server_header=False: no component version in responses (ASVS V14.3.3).
    uvicorn.run(app, host=settings.api_host, port=settings.api_port, server_header=False)


if __name__ == "__main__":
    run()
