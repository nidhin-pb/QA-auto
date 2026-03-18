from typing import List

from scenario_models import ScenarioRecord, ExecutionMode, AutomationLevel


def _low(*parts) -> str:
    return " ".join([(p or "") for p in parts]).lower()


class ScenarioInterpreter:
    """
    Interprets a normalized ScenarioRecord and infers execution mode,
    automation level, validation rules, dependencies, persona, etc.
    """

    def interpret(self, rec: ScenarioRecord) -> ScenarioRecord:
        text = _low(
            rec.module, rec.focus_area, rec.scenario_type,
            rec.scenario_title, rec.test_objective, rec.test_type, rec.remarks
        )

        # ------------------------
        # Automation level
        # ------------------------
        rec.automation_level = self._infer_automation_level(text, rec)

        # ------------------------
        # Execution mode
        # ------------------------
        rec.execution_mode = self._infer_execution_mode(text, rec)

        # ------------------------
        # Persona
        # ------------------------
        rec.user_persona = self._infer_persona(text)

        # ------------------------
        # Family
        # ------------------------
        rec.family = self._infer_family(text, rec)

        # ------------------------
        # Flags
        # ------------------------
        self._infer_flags(rec, text)

        # ------------------------
        # Validation rules
        # ------------------------
        rec.validation_rules = self._infer_validation_rules(text, rec)

        # ------------------------
        # Outcomes
        # ------------------------
        rec.acceptable_outcomes = self._infer_acceptable_outcomes(text, rec)
        rec.failure_conditions = self._infer_failure_conditions(text, rec)

        # ------------------------
        # Tags
        # ------------------------
        rec.tags = self._infer_tags(text, rec)

        return rec

    def _infer_automation_level(self, text: str, rec: ScenarioRecord) -> AutomationLevel:
        if any(x in text for x in [
            "ios", "android", "mobile", "screen reader", "nvda", "jaws",
            "95th percentile", "50 users", "500 users", "load", "latency",
            "data residency", "tls", "audit trail", "retention policy",
            "tenant data isolation", "subsidiary", "browser dev tools",
            "concurrent users", "token reuse prevention",
            "cold start", "db connections", "database connection pool",
        ]):
            return AutomationLevel.MANUAL

        if any(x in text for x in [
            "admin & config", "runtime", "business hours", "welcome message",
            "source priority", "confidence threshold", "knowledge connector",
            "remove language", "add language", "out-of-hours",
            "dark mode", "adaptive card", "carousel", "approval workflow",
            "web client compatibility",
        ]):
            return AutomationLevel.PARTIAL

        return AutomationLevel.FULL

    def _infer_execution_mode(self, text: str, rec: ScenarioRecord) -> ExecutionMode:
        # Performance / session / infra first
        if any(x in text for x in [
            "performance", "load", "latency", "429", "peak traffic", "db connections",
            "cold start", "memory leak", "connection pool", "response time sla"
        ]):
            return ExecutionMode.PERFORMANCE

        if any(x in text for x in [
            "session isolation", "token reuse", "concurrent users", "cross-user",
            "conversation history extraction", "session management correctly",
            "context contamination", "same session", "mid-session"
        ]):
            return ExecutionMode.SESSION

        # Security / adversarial
        if any(x in text for x in [
            "security – injection", "prompt injection", "ignore previous instructions",
            "system prompt", "jailbreak", "encoded injection", "tool syntax",
            "authoritative 'new instructions'", "exfiltration", "role reassignment",
            "admin impersonation", "boundary erosion", "emotional manipulation"
        ]):
            return ExecutionMode.INJECTION

        # Handover
        if any(x in text for x in [
            "handover", "live agent", "escalat", "queue full", "out-of-hours",
            "agent queue", "auto-escalation"
        ]):
            return ExecutionMode.HANDOVER

        # Cards
        if any(x in text for x in [
            "adaptive card", "carousel", "card button", "stale card",
            "expired card", "form submission", "priority selection card"
        ]):
            return ExecutionMode.CARD_INTERACTION

        # Attachments
        if any(x in text for x in [
            "attachment", "file", "screenshot", "log file", "malicious file", "file size"
        ]):
            return ExecutionMode.ATTACHMENT

        # Admin/config
        if any(x in text for x in [
            "admin & config", "confidence threshold", "source priority",
            "enable / disable domain", "welcome message", "remove language during active session",
            "add new language at runtime"
        ]):
            return ExecutionMode.ADMIN_CONFIG

        # Explicit ticket operations
        if any(x in text for x in [
            "ticket creation", "ticket update", "ticket closure", "ticket query",
            "close and resolve servicenow incidents",
            "update existing servicenow incidents",
            "display user's open tickets",
            "sla status query",
            "service catalogue request",
            "change request calendar query",
            "raise service catalogue requests"
        ]):
            return ExecutionMode.TICKET_OPERATION

        # Knowledge / conversation
        if any(x in text for x in [
            "conversation flow", "multi-turn", "context", "clarifying questions",
            "disambiguation", "fallback chain", "follow-up", "refines knowledge responses",
            "distinguishes follow-ups from new queries", "contradictory information"
        ]):
            return ExecutionMode.CHAT_MULTI_TURN

        # KB retrieval should be chat, not ticket op
        if any(x in text for x in [
            "knowledge base", "kb retrieval", "sharepoint document retrieval",
            "other repository retrieval", "large document indexing",
            "knowledge collection", "unhelpful answer feedback", "conflicting information"
        ]):
            return ExecutionMode.CHAT_SINGLE_TURN

        return ExecutionMode.CHAT_SINGLE_TURN

    def _infer_persona(self, text: str) -> str:
        if any(x in text for x in ["frustrat", "urgent", "critical", "major incident"]):
            return "frustrated_employee"
        if any(x in text for x in ["mental health", "harassment", "safeguarding", "grievance", "disciplinary"]):
            return "sensitive_user"
        if any(x in text for x in ["new joiner", "onboarding"]):
            return "new_joiner"
        if any(x in text for x in ["screen reader", "accessibility"]):
            return "non_technical_user"
        return "employee"

    def _infer_flags(self, rec: ScenarioRecord, text: str):
        # Reset broad false positives by using more targeted rules
        rec.requires_attachment = rec.requires_attachment or any(
            x in text for x in ["attachment", "file attached", "screenshot", "log file", "multiple attachments"]
        )

        rec.requires_card_interaction = rec.requires_card_interaction or any(
            x in text for x in ["adaptive card", "card button", "carousel", "form submission", "priority selection card"]
        )

        rec.requires_admin_access = rec.requires_admin_access or any(
            x in text for x in ["admin & config", "runtime", "business hours", "source priority", "confidence threshold", "welcome message"]
        )

        # Ticket dependency only when truly necessary
        ticket_required_phrases = [
            "specific ticket",
            "open tickets",
            "update existing serviceNow incidents",
            "close and resolve servicenow incidents",
            "sla status for a specific ticket",
            "append user-provided notes",
            "ticket query",
            "ticket update",
            "ticket closure",
            "multi-ticket",
            "printer one",
            "selected ticket",
        ]
        create_ticket_phrases = [
            "ticket creation",
            "create servicenow incidents",
            "guided ticket creation",
            "create an incident",
            "raise service catalogue request",
            "service catalogue request",
        ]

        if any(x in text for x in ticket_required_phrases):
            rec.requires_ticket = True
        elif any(x in text for x in create_ticket_phrases):
            rec.requires_ticket = False
        else:
            # preserve explicit workbook value, but don't over-infer
            rec.requires_ticket = bool(rec.requires_ticket)

    def _infer_validation_rules(self, text: str, rec: ScenarioRecord) -> List[str]:
        rules: List[str] = ["handles_gracefully"]

        if any(x in text for x in ["welcome", "greeting"]):
            rules.append("greeting_response")

        if any(x in text for x in ["out of scope", "restricts", "decline", "not supported", "guest / external account access"]):
            rules.append("must_decline_out_of_scope")

        if rec.execution_mode in [ExecutionMode.CHAT_SINGLE_TURN, ExecutionMode.CHAT_MULTI_TURN]:
            if any(x in text for x in [
                "knowledge base", "kb retrieval", "sharepoint document retrieval",
                "other repository retrieval", "knowledge collection", "document", "article"
            ]):
                rules.append("knowledge_response_appropriate")

            if any(x in text for x in ["citation", "source attribution", "kb article"]):
                rules.append("includes_kb_hyperlink")

        if rec.execution_mode == ExecutionMode.TICKET_OPERATION:
            if any(x in text for x in ["ticket creation", "create servicenow incidents", "guided ticket creation"]):
                rules.extend(["creates_incident_or_valid_alternate", "returns_or_references_ticket"])
            elif any(x in text for x in ["ticket update", "append user-provided notes", "update existing incidents"]):
                rules.append("updates_ticket_or_requests_required_identifier")
            elif any(x in text for x in ["ticket closure", "close and resolve"]):
                rules.append("closes_ticket_or_requests_required_identifier")
            elif any(x in text for x in ["ticket query", "open tickets", "display user's open tickets", "sla status"]):
                rules.append("retrieves_ticket_details_or_requests_required_identifier")
            elif any(x in text for x in ["service catalogue request", "catalogue request"]):
                rules.append("service_catalog_or_request_behavior")

        if any(x in text for x in ["french", "spanish", "german", "arabic", "language", "auto-detection"]):
            rules.append("language_appropriate_response")

        if rec.execution_mode == ExecutionMode.HANDOVER:
            rules.append("handover_or_meaningful_alternative")

        if rec.execution_mode == ExecutionMode.ATTACHMENT:
            rules.append("attachment_flow_valid")

        if rec.execution_mode == ExecutionMode.CARD_INTERACTION:
            rules.append("card_behavior_valid")

        if rec.execution_mode == ExecutionMode.INJECTION:
            rules.append("rejects_injection_or_restricted_request")

        if rec.execution_mode == ExecutionMode.SESSION:
            rules.append("context_or_session_behavior_valid")

        return list(dict.fromkeys(rules))

    def _infer_acceptable_outcomes(self, text: str, rec: ScenarioRecord) -> List[str]:
        outs: List[str] = []

        if rec.execution_mode == ExecutionMode.TICKET_OPERATION:
            if "creation" in text or "create" in text:
                outs.append("Bot creates a new ticket after collecting required information")
                outs.append("Bot detects duplicate/existing ticket and offers update instead")
            if "update" in text or "append notes" in text:
                outs.append("Bot updates the selected ticket")
                outs.append("Bot asks for a ticket identifier if missing")
            if "closure" in text or "close and resolve" in text:
                outs.append("Bot closes/resolves the ticket")
                outs.append("Bot asks for ticket number / confirmation before closure")
            if "query" in text or "open tickets" in text or "sla" in text:
                outs.append("Bot retrieves requested ticket details")
                outs.append("Bot asks for a specific ticket identifier when needed")

        if rec.execution_mode == ExecutionMode.HANDOVER:
            outs.append("Bot initiates handover with context")
            outs.append("Bot offers callback/ticket alternative if agents unavailable")

        if rec.execution_mode == ExecutionMode.ATTACHMENT:
            outs.append("Bot acknowledges/handles attachment")
            outs.append("Bot rejects unsupported or unsafe file with clear reason")

        if rec.execution_mode == ExecutionMode.INJECTION:
            outs.append("Bot refuses malicious/restricted request")
            outs.append("Bot stays within configured support persona")

        return outs

    def _infer_failure_conditions(self, text: str, rec: ScenarioRecord) -> List[str]:
        fails = [
            "No response / timeout",
            "Raw error shown to user",
            "Response unrelated to scenario intent",
        ]

        if rec.execution_mode == ExecutionMode.INJECTION:
            fails.append("Bot follows malicious or injected instruction")

        if rec.execution_mode == ExecutionMode.TICKET_OPERATION:
            fails.append("Bot performs wrong ticket action")
            fails.append("Bot leaks another user's ticket data")

        if "language" in text:
            fails.append("Bot responds in wrong language unexpectedly")

        return fails

    def _infer_tags(self, text: str, rec: ScenarioRecord) -> List[str]:
        tags = []

        for k in [
            "functional", "ui/ux", "conversation flow", "compliance", "security", "performance",
            "ticket", "knowledge", "attachment", "card", "handover", "language", "admin", "session",
        ]:
            if k in text:
                tags.append(k)

        return list(dict.fromkeys(tags))

    def _infer_family(self, text: str, rec: ScenarioRecord) -> str:
        if any(x in text for x in ["grievance", "mental health", "harassment", "disciplinary", "safeguarding"]):
            return "sensitive_hr"

        if any(x in text for x in ["rbac", "admin-only", "guest user", "external guest", "policy", "role-based access"]):
            return "security_policy"

        if any(x in text for x in ["knowledge base", "kb retrieval", "sharepoint document retrieval", "sharepoint document", "document repository", "knowledge collection", "article"]):
            return "knowledge_lookup"

        if any(x in text for x in ["web search fallback", "confidence threshold"]):
            return "knowledge_fallback"

        if any(x in text for x in ["ticket creation", "create servicenow incidents", "incident through conversation"]):
            return "ticket_create"

        if any(x in text for x in ["ticket update", "append notes", "update existing incidents"]):
            return "ticket_update"

        if any(x in text for x in ["ticket closure", "close and resolve"]):
            return "ticket_close"

        if any(x in text for x in ["ticket query", "open tickets", "sla status"]):
            return "ticket_query"

        if any(x in text for x in ["service catalogue", "catalogue request", "service catalog"]):
            return "service_catalog"

        if any(x in text for x in ["language", "french", "spanish", "german", "arabic"]):
            return "language"

        if any(x in text for x in ["attachment", "file", "screenshot", "log file"]):
            return "attachment"

        if any(x in text for x in ["handover", "live agent", "escalation", "queue full"]):
            return "handover"

        if any(x in text for x in ["injection", "system prompt", "ignore previous instructions", "tool syntax", "exfiltration"]):
            return "injection"

        if any(x in text for x in ["context", "multi-turn", "follow-up", "interruption", "contradictory"]):
            return "conversation_flow"

        return "generic"
