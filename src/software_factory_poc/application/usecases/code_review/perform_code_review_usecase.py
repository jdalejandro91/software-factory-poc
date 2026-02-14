from software_factory_poc.application.ports.drivers.tracker_driver_port import TrackerDriverPort
from software_factory_poc.application.core.agents.code_reviewer_agent import CodeReviewerAgent

class PerformCodeReviewUseCase:
    def __init__(self, agent: CodeReviewerAgent, tracker: TrackerDriverPort):
        self.agent = agent
        self.tracker = tracker

    async def execute(self, ticket_id: str) -> dict:
        """El Use Case extrae la Entidad Task desde el Tracker y la inyecta al Agente."""
        task = await self.tracker.get_task(ticket_id)
        return await self.agent.execute(task)