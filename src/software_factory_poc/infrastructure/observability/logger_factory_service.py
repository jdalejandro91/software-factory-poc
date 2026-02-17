import logging
import sys


class LoggerFactoryService:
    @staticmethod
    def configure_root_logger() -> None:
        """
        Basic config to ensure logs go to stdout.
        Should be called at application startup.
        """
        logging.basicConfig(
            stream=sys.stdout,
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            force=True,  # Override any previous config
        )

    @staticmethod
    def build_logger(name: str) -> logging.Logger:
        """
        Returns a configured logger instance.
        """
        return logging.getLogger(name)
