from enum import StrEnum

class TaskStatus(StrEnum):
    TO_DO = "To Do"
    IN_PROGRESS = "In Progress" 
    IN_REVIEW = "In Review"
    DONE = "Done"
    # Add other statuses as needed by the standard workflow
