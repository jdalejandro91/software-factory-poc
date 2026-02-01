from dataclasses import dataclass
from typing import Any

from software_factory_poc.application.core.agents.base_agent import BaseAgent
from software_factory_poc.application.core.agents.reporter.ports.task_tracker_gateway import TaskTrackerGateway, \
    TaskStatus
from software_factory_poc.application.core.agents.common.dtos.automation_context_dto import AutomationContextDTO
from .config.reporter_constants import ReporterMessages


@dataclass
class ReporterAgent(BaseAgent):
    """
    Agent responsible for reporting progress and status to the Task Tracker (Jira).
    """
    tracker: TaskTrackerGateway

    def report_start(self, task_id: str) -> None:
        self.tracker.add_comment(task_id, ReporterMessages.START_SCAFFOLDING)

    def report_success(self, task_id: str, message: Any) -> None:
        if isinstance(message, dict):
            self.tracker.add_comment(task_id, message)
        else:
            self.tracker.add_comment(task_id, f"{ReporterMessages.SUCCESS_PREFIX}{message}")

    def report_failure(self, task_id: str, error_msg: str) -> None:
        # Note: Previous code accessed self.gateway which did not exist in dataclass definition (which had `tracker`).
        # The audit didn't catch this bug directly but I should fix it.
        # self.tracker was defined, but methods used self.gateway?
        # Let's check original content.
        # Original Lines 20 and 23 used `self.gateway`.
        # Error in original code: `tracker: TaskTrackerGateway` field vs `self.gateway` usage.
        # I will fix standardizing on `self.tracker` as defined in dataclass.
        self.tracker.add_comment(task_id, f"{ReporterMessages.FAILURE_PREFIX}{error_msg}")

    def transition_task(self, task_id: str, status: TaskStatus) -> None:
        self.tracker.transition_status(task_id, status)

    def update_task_description(self, task_id: str, description: str) -> None:
        self.tracker.update_task_description(task_id, description)

    def save_automation_context(self, issue_key: str, context: AutomationContextDTO) -> None:
        """
        Saves the Automation Context to the issue description using safe Domain logic.
        """
        # 1. Fetch current task (Domain Entity)
        # This parses existing content safely
        current_task = self.tracker.get_task(issue_key)
        
        # 2. Create updated instance (Pure Logic)
        # Replaces or adds the automation metadata while keeping human text
        updated_task = current_task.update_metadata(context.model_dump())
        
        # 3. Persist changes (Infrastructure)
        # Mapper handles ADF conversion and Code Block injection
        self.tracker.update_task_description(issue_key, updated_task.description)

