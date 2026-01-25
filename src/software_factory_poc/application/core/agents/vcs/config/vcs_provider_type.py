try:
    from enum import StrEnum, auto
except ImportError:
    from enum import Enum, auto
    class StrEnum(str, Enum):
        pass


class VcsProviderType(StrEnum):
    GITLAB = auto()
    GITHUB = auto()
    BITBUCKET = auto()
