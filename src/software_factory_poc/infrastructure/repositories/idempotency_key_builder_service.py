import hashlib


class IdempotencyKeyBuilderService:
    def build(self, issue_key: str, contract_version: str, description_hash: str) -> str:
        """
        Builds a deterministic idempotency key.
        """
        raw = f"{issue_key}|{contract_version}|{description_hash}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
