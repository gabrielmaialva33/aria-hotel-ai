#!/usr/bin/env python
"""Main entry point for ARIA Hotel AI."""

import uvicorn

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def main():
    """Run the application."""
    logger.info(
        "Starting ARIA Hotel AI",
        version="0.1.0",
        environment=settings.app_env,
        host=settings.api_host,
        port=settings.api_port
    )

    uvicorn.run(
        "app.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.app_debug,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
