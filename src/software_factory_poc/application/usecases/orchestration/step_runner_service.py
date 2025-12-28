import time
from collections.abc import Callable
from typing import Any

from software_factory_poc.infrastructure.observability.logger_factory_service import (
    build_logger,
    log_context_string,
)

logger = build_logger(__name__)


class StepExecutionError(Exception):
    """Raised when a step fails."""
    def __init__(self, step_name: str, original_error: Exception):
        self.step_name = step_name
        self.original_error = original_error
        super().__init__(f"Step '{step_name}' failed: {str(original_error)}")


class StepRunnerService:
    def run_step(
        self,
        step_name: str,
        fn: Callable[[], Any],
        run_id: str,
        issue_key: str,
    ) -> Any:
        """
        Executes a function as a tracked step with logging and error handling.
        """
        ctx_str = log_context_string(run_id=run_id, issue_key=issue_key, step_name=step_name)
        logger.info(f"{ctx_str} STARTing step")
        
        start_time = time.monotonic()
        
        try:
            result = fn()
            duration_ms = (time.monotonic() - start_time) * 1000
            logger.info(f"{ctx_str} COMPLETED step in {duration_ms:.2f}ms")
            return result
            
        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            logger.error(f"{ctx_str} FAILED step in {duration_ms:.2f}ms: {e}")
            # Wrap and re-raise
            raise StepExecutionError(step_name, e) from e
