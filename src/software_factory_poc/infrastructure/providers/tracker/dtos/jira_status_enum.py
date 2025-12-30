from enum import StrEnum

class JiraStatus(StrEnum):
    TO_DO = "Por hacer"
    IN_PROGRESS = "En curso"
    IN_REVIEW = "In Review" # Or "En revisión" depending on checks
    DONE = "Listo"
