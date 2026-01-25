import logging
import sys
from typing import Any, Optional


class LoggerFactoryService:
    @staticmethod
    def configure_root_logger() -> None:
        """
        Basic configuration to ensure logs go to stdout.
        Should be called at application startup.
        """
        logging.basicConfig(
            stream=sys.stdout,
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            force=True  # Override any previous config
        )

    @staticmethod
    def build_logger(name: str) -> logging.Logger:
        """
        Returns a configured logger instance.
        """
        return logging.getLogger(name)

    @staticmethod
    def build_log_context(
        run_id: Optional[str] = None,
        issue_key: Optional[str] = None,
        step_name: Optional[str] = None,
        extra: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Builds a dictionary for use in logging 'extra' fields or structural logging.
        """
        context = {}
        if run_id:
            context["run_id"] = run_id
        if issue_key:
            context["issue_key"] = issue_key
        if step_name:
            context["step_name"] = step_name

        if extra:
            context.update(extra)

        return context

    @staticmethod
    def log_context_string(
        run_id: Optional[str] = None,
        issue_key: Optional[str] = None,
        step_name: Optional[str] = None,
    ) -> str:
        """
        Helper to create a standard prefix string '[run_id=... issue_key=...]'
        """
        parts = []
        if run_id:
            parts.append(f"run_id={run_id}")
        if issue_key:
            parts.append(f"issue_key={issue_key}")
        if step_name:
            parts.append(f"step={step_name}")

        if not parts:
            return ""

        return f"[{' '.join(parts)}]"
