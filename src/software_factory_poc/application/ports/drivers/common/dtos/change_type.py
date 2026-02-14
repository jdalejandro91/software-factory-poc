from enum import StrEnum


class ChangeType(StrEnum):
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    RENAMED = "RENAMED"
    COPIED = "COPIED"
