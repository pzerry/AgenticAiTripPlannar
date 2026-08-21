from __future__ import annotations

import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from Backend.Logger import get_logger
from Backend.Logger.context import (
    generate_execution_id,
    set_execution_id,
    set_request_id,
)

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that initializes request logging context
    and logs every HTTP request.
    """

    async def dispatch(
        self,
        request: Request,
        call_next,
    ):

        request_id = str(uuid4())
        execution_id = generate_execution_id()

        # Store context and keep tokens
        request_token = set_request_id(request_id)
        execution_token = set_execution_id(execution_id)

        start = time.perf_counter()

        logger.info(
            "Incoming Request | %s %s",
            request.method,
            request.url.path,
        )

        try:

            response = await call_next(request)

            duration = (time.perf_counter() - start) * 1000

            logger.info(
                "Completed Request | %s %s | status=%d | %.2f ms",
                request.method,
                request.url.path,
                response.status_code,
                duration,
            )

            response.headers["X-Request-ID"] = request_id

            return response

        except Exception:

            duration = (time.perf_counter() - start) * 1000

            logger.exception(
                "Unhandled Request Error | %s %s | %.2f ms",
                request.method,
                request.url.path,
                duration,
            )

            raise

        finally:
            # Restore previous ContextVar values
            execution_token.var.reset(execution_token)
            request_token.var.reset(request_token)