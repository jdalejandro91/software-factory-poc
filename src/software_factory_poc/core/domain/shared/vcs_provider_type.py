from enum import StrEnum, auto


class VcsProviderType(StrEnum):
    GITLAB = auto()
    GITHUB = auto()
    BITBUCKET = auto()
