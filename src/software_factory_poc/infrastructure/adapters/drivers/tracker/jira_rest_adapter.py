from software_factory_poc.application.ports.drivers.tracker_driver_port import TrackerDriverPort

class JiraRestAdapter(TrackerDriverPort):
    def __init__(self, jira_http_client):
        self.client = jira_http_client

    async def get_task_description(self, ticket_id: str) -> str:
        data = await self.client.get_issue(ticket_id)
        return str(data.get("fields", {}).get("description", ""))

    async def update_status(self, ticket_id: str, status: str) -> None:
        await self.client.transition_issue(ticket_id, status)

    async def add_comment(self, ticket_id: str, comment: str) -> None:
        await self.client.add_comment(ticket_id, comment)