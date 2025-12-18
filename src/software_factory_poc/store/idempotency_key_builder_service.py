import hashlib

class IdempotencyKeyBuilderService:
    def build(self, issue_key: str, contract_version: str, template_version: str) -> str:
        """
        Builds a deterministic idempotency key.
        We stick to a simple format or a hash. 
        Given the limited input, a simple composed string is readable, but a hash handles chars better.
        """
        raw = f"{issue_key}|{contract_version}|{template_version}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
