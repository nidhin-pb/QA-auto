from typing import Dict


class ScenarioFamilyMapper:
    @staticmethod
    def get_family(scenario: Dict) -> str:
        title = ((scenario.get("excel", {}) or {}).get("scenario_title", "") or scenario.get("name", "")).lower()
        module = (scenario.get("category", "") or "").lower()
        goal = (scenario.get("goal", "") or "").lower()
        mode = (scenario.get("execution_mode", "") or "").lower()
        focus = ((scenario.get("excel", {}) or {}).get("focus_area", "") or
                 (scenario.get("description", "") or "")).lower()
        blob = f"{title} {module} {goal} {mode} {focus}"

        # --- Sensitive HR ---
        if any(x in blob for x in ["grievance", "mental health", "harassment", "disciplinary", "safeguarding"]):
            return "sensitive_hr"

        # --- Security policy / RBAC / guest ---
        if any(x in blob for x in [
            "rbac", "admin-only", "guest user", "external guest", "role-based access",
            "guest / external account access", "oauth token", "data residency",
            "audit trail", "data retention", "encryption in transit",
        ]):
            return "security_policy"

        # --- Injection (broad) ---
        if any(x in blob for x in [
            "injection", "system prompt", "ignore previous instructions", "tool syntax",
            "exfiltration", "fabricated previous bot", "cross-user conversation",
            "authorisation for restricted actions", "authorization for restricted actions",
            "knowledge article poisoning", "bulk tickets via loop", "loop or repeat commands",
            "mass ticket spam", "role reassignment", "admin impersonation",
            "emotional manipulation", "boundary erosion", "foot in the door",
            "enumeration of other users", "data exfiltration", "command syntax in chat",
            "context window flooding", "false prior-session", "injection in non-english",
            "non-english language", "safety filters apply consistently",
            "encoded injection", "base64", "unicode obfuscation",
            "web search abuse", "restricted content",
            "injection via ticket description",
        ]):
            return "injection"

        # --- SLA ---
        if any(x in blob for x in ["sla status", "target resolution time", "time remaining", "breached"]):
            return "sla_query"

        # --- Change calendar ---
        if any(x in blob for x in [
            "change calendar", "approved changes", "upcoming approved changes", "chg",
            "change request calendar",
        ]):
            return "change_calendar"

        # --- Approval workflow ---
        if any(x in blob for x in ["approval workflow", "approve/reject", "pending approvals", "manager approval"]):
            return "approval_workflow"

        # --- Ticket update ---
        if any(x in blob for x in [
            "ticket update", "update existing servicenow incidents", "update existing incident",
            "update incident", "append notes", "add note", "work note",
            "user corrects information mid-conversation",
        ]):
            return "ticket_update"

        # --- Ticket close ---
        if any(x in blob for x in [
            "ticket closure", "close and resolve", "close incident", "resolve incident",
            "user abandons ticket creation",
        ]):
            return "ticket_close"

        # --- Ticket query ---
        if any(x in blob for x in [
            "ticket query", "open tickets", "show my open tickets", "display user's open tickets",
            "display user's open tickets", "multi-ticket query", "selective update",
            "recurring issue pattern",
        ]):
            return "ticket_query"

        # --- Ticket create ---
        if any(x in blob for x in [
            "ticket creation", "create servicenow incidents", "incident through conversation",
            "guided ticket creation", "raise an incident", "create incident",
            "slot filling", "ticket creation interrupted",
        ]):
            return "ticket_create"

        # --- Service catalog ---
        if any(x in blob for x in ["service catalogue", "catalogue request", "service catalog"]):
            return "service_catalog"

        # --- Knowledge lookup ---
        if any(x in blob for x in [
            "knowledge base", "kb retrieval", "sharepoint document retrieval",
            "sharepoint document", "document repository", "knowledge collection", "article",
            "progressive refinement", "follow-up questions",
            "ambiguous query disambiguation",
            "kb miss", "fallback chain",
            "new article indexed", "retired article",
            "duplicate articles", "de-duplicat",
            "knowledge gap", "unhelpful answer",
            "conflicting information across sources",
            "knowledge collection completely empty",
            "large document indexing", "100+ page",
            "kb article in unsupported language",
        ]):
            return "knowledge_lookup"

        # --- Knowledge fallback ---
        if any(x in blob for x in [
            "web search fallback", "confidence threshold", "search trigger behaviour",
            "search trigger behavior", "content safety & edge cases",
            "domain-specific web search",
        ]):
            return "knowledge_fallback"

        # --- Language ---
        if any(x in blob for x in [
            "language", "french", "spanish", "german", "arabic",
            "language switch", "auto-detection",
            "add new language", "remove language",
        ]):
            return "language"

        # --- Attachment ---
        if any(x in blob for x in [
            "attachment", "file", "screenshot", "log file",
            "unsupported file type", "file size", "attached to ticket",
            "malicious file", "multiple attachments",
        ]):
            return "attachment"

        # --- Handover ---
        if any(x in blob for x in [
            "handover", "live agent", "escalation", "queue full", "out-of-hours",
            "auto-escalation", "graceful escalation",
            "repeated failed intents",
            "cancels handover", "domain-aware routing",
        ]):
            return "handover"

        # --- Conversation flow ---
        if any(x in blob for x in [
            "context", "multi-turn", "follow-up", "interruption", "contradictory",
            "bot recovers", "bot misunderstands", "user corrects",
            "conversation quality", "context management",
            "knowledge api failure", "recovery",
            "proactive related action", "post-resolution",
            "bot availability", "discoverability",
            "bot is accessible and responsive",
        ]):
            return "conversation_flow"

        # --- Out-of-scope / compliance / policy (catch broader patterns) ---
        if any(x in blob for x in [
            "compliance", "privacy", "accessibility", "csat",
            "content safety", "data privacy",
        ]):
            return "security_policy"

        # --- Multi-tenancy / org config ---
        if any(x in blob for x in [
            "department-specific", "white-label", "bot persona",
            "tenant data isolation", "multi-tenancy",
            "knowledge scope isolation", "tool availability",
        ]):
            return "security_policy"

        # --- Domain flexibility edge cases ---
        if any(x in blob for x in [
            "hr domain", "sales domain", "crm",
            "cross-department", "ticket routing",
            "domain switching", "spanning it and hr",
            "redundancy", "restructuring",
            "at-risk role",
        ]):
            return "conversation_flow"

        # --- Session / auth ---
        if any(x in blob for x in [
            "session", "authentication", "azure ad", "sso",
            "token reuse", "session isolation",
        ]):
            return "conversation_flow"

        return "generic"
