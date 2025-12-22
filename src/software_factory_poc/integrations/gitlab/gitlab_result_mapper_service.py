from typing import Any, Dict
from pydantic import BaseModel

class GitLabMergeRequestDataModel(BaseModel):
    mr_url: str
    mr_id: int
    mr_iid: int


class GitLabResultMapperService:
    def map_mr(self, raw_data: Dict[str, Any]) -> GitLabMergeRequestDataModel:
        """
        Maps raw GitLab MR response to internal data model.
        """
        mr_url = raw_data.get("web_url", "")
        mr_id = raw_data.get("id", 0)
        mr_iid = raw_data.get("iid", 0)
        
        return GitLabMergeRequestDataModel(
            mr_url=mr_url,
            mr_id=mr_id,
            mr_iid=mr_iid
        )
