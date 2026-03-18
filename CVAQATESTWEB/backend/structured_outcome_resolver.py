from ticket_workflow_resolver import TicketWorkflowResolver


class StructuredOutcomeResolver:
    @staticmethod
    def resolve(result):
        family = ((result.scenario.get("excel", {}) or {}).get("family", "") or result.scenario.get("family", "")).lower()

        if family in ("ticket_create", "ticket_update", "ticket_close", "ticket_query", "attachment"):
            return TicketWorkflowResolver.resolve(result)

        return {
            "final_path": "",
            "ticket_id": None,
            "notes": [],
            "alternate": False,
            "alternate_reason": "",
        }
