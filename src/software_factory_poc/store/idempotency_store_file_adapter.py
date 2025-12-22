import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Optional

from software_factory_poc.config.settings_pydantic import Settings
from software_factory_poc.observability.logger_factory_service import build_logger

logger = build_logger(__name__)


class IdempotencyStoreFileAdapter:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.store_dir = settings.runtime_data_dir
        self.file_path = self.store_dir / "idempotency_store.json"
        self._ensure_store()

    def _ensure_store(self):
        if not self.store_dir.exists():
            self.store_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.file_path.exists():
            self._write_json({})

    def _read_json(self) -> Dict[str, str]:
        if not self.file_path.exists():
            return {}
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read idempotency store: {e}. Returning empty.")
            return {}

    def _write_json(self, data: Dict[str, str]):
        """
        Atomic write: write to temp file then rename.
        """
        try:
            # Create a temp file in the same directory to ensure atomic rename works across filesystems
            with tempfile.NamedTemporaryFile("w", dir=self.store_dir, delete=False, encoding="utf-8") as tmp:
                json.dump(data, tmp, indent=2)
                tmp_path = tmp.name
            
            # Atomic replace
            os.replace(tmp_path, self.file_path)
            
        except Exception as e:
            logger.error(f"Failed to write to idempotency store: {e}")
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    def get(self, key: str) -> Optional[str]:
        data = self._read_json()
        return data.get(key)

    def put(self, key: str, mr_url: str):
        data = self._read_json()
        data[key] = mr_url
        self._write_json(data)
