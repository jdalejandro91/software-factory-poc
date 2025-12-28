import json
import os
import tempfile

from software_factory_poc.config.settings_pydantic import Settings
from software_factory_poc.contracts.artifact_result_model import ArtifactResultModel
from software_factory_poc.observability.logger_factory_service import build_logger

logger = build_logger(__name__)


class RunResultStoreFileAdapter:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.store_dir = settings.runtime_data_dir
        self.file_path = self.store_dir / "run_results.json"
        self._ensure_store()

    def _ensure_store(self):
        if not self.store_dir.exists():
            self.store_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.file_path.exists():
            self._write_json({})

    def _read_json(self) -> dict[str, dict]:
        if not self.file_path.exists():
            return {}
        try:
            with open(self.file_path, encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read run result store: {e}. Returning empty.")
            return {}

    def _write_json(self, data: dict[str, dict]):
        try:
            with tempfile.NamedTemporaryFile("w", dir=self.store_dir, delete=False, encoding="utf-8") as tmp:
                json.dump(data, tmp, indent=2)
                tmp_path = tmp.name
            
            os.replace(tmp_path, self.file_path)
            
        except Exception as e:
            logger.error(f"Failed to write to run result store: {e}")
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    def get(self, run_id: str) -> ArtifactResultModel | None:
        data = self._read_json()
        item = data.get(run_id)
        if item:
            try:
                return ArtifactResultModel(**item)
            except Exception as e:
                logger.error(f"Failed to parse stored result for {run_id}: {e}")
                return None
        return None

    def put(self, run_id: str, result: ArtifactResultModel):
        data = self._read_json()
        # Serialize model to dict
        data[run_id] = result.model_dump(mode='json')
        self._write_json(data)
