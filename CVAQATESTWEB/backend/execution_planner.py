from typing import List, Dict

from scenario_models import ScenarioRecord, AutomationLevel, ExecutionMode


class ExecutionPlanner:
    """
    Creates a safe run order:
    1. Fully automatable chat/ticket scenarios first
    2. Attachment/card/handover next
    3. Partial/manual last
    Also keeps ticket-creating scenarios early if possible.
    """

    def plan(self, records: List[ScenarioRecord]) -> Dict:
        full = [r for r in records if r.automation_level == AutomationLevel.FULL]
        partial = [r for r in records if r.automation_level == AutomationLevel.PARTIAL]
        manual = [r for r in records if r.automation_level == AutomationLevel.MANUAL]

        def score(r: ScenarioRecord):
            p = (r.priority or "medium").lower()
            p_score = {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(p, 2)

            # Create ticket early so later scenarios can reuse tickets
            mode_score = {
                ExecutionMode.TICKET_OPERATION: 0,
                ExecutionMode.CHAT_MULTI_TURN: 1,
                ExecutionMode.CHAT_SINGLE_TURN: 2,
                ExecutionMode.ATTACHMENT: 3,
                ExecutionMode.CARD_INTERACTION: 4,
                ExecutionMode.HANDOVER: 5,
                ExecutionMode.INJECTION: 6,
                ExecutionMode.ADMIN_CONFIG: 7,
                ExecutionMode.SESSION: 8,
                ExecutionMode.PERFORMANCE: 9,
                ExecutionMode.MANUAL_REVIEW: 10,
            }.get(r.execution_mode, 10)

            title = (r.scenario_title or "").lower()
            create_bias = 0
            if "create" in title and "ticket" in title:
                create_bias = -1

            return (p_score, mode_score, create_bias, r.scenario_id)

        ordered_full = sorted(full, key=score)
        ordered_partial = sorted(partial, key=score)
        ordered_manual = sorted(manual, key=score)

        ordered = ordered_full + ordered_partial + ordered_manual

        summary = {
            "total": len(records),
            "full": len(full),
            "partial": len(partial),
            "manual": len(manual),
            "execution_modes": self._mode_counts(records),
        }

        return {
            "ordered_records": ordered,
            "summary": summary,
        }

    def _mode_counts(self, records: List[ScenarioRecord]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for r in records:
            k = r.execution_mode.value
            counts[k] = counts.get(k, 0) + 1
        return counts
