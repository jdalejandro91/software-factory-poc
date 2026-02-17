try:
    from enum import StrEnum, auto
except ImportError:
    from enum import Enum, auto
    class StrEnum(str, Enum):
        pass


class ResearchProviderType(StrEnum):
    CONFLUENCE = auto()
    FILE_SYSTEM = auto()