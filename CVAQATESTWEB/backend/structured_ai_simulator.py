from typing import Dict, List


class StructuredAISimulator:
    """
    Builds compact prompts for LLM-driven human-like structured testing.
    Token-efficient by design.
    """

    @staticmethod
    def build_initial_prompt_request(scenario: Dict) -> Dict:
        family = ((scenario.get("excel", {}) or {}).get("family", "") or scenario.get("family", "")).lower()
        title = ((scenario.get("excel", {}) or {}).get("scenario_title", "") or scenario.get("name", "")).strip()
        goal = (scenario.get("goal", "") or "").strip()
        persona = (scenario.get("user_persona", "") or "employee").strip()

        prompt = (
            f"Scenario title: {title}\n"
            f"Goal: {goal}\n"
            f"Persona: {persona}\n"
            f"Family: {family}\n\n"
            "Write the FIRST message a real employee would send to the IT support bot.\n"
            "Rules:\n"
            "- Be natural and short.\n"
            "- Be the USER, not the bot.\n"
            "- Do not mention testing.\n"
            "- Do not say 'please proceed with test'.\n"
            "- 1-2 sentences only.\n"
            "- Return only the user message."
        )

        return {
            "system": (
                "You are simulating an employee asking an IT support bot for help. "
                "You are NOT the bot. Return only the user's message."
            ),
            "prompt": prompt,
        }

    @staticmethod
    def build_followup_request(scenario: Dict, history: List[Dict], cva_response: str) -> Dict:
        family = ((scenario.get("excel", {}) or {}).get("family", "") or scenario.get("family", "")).lower()
        title = ((scenario.get("excel", {}) or {}).get("scenario_title", "") or scenario.get("name", "")).strip()
        goal = (scenario.get("goal", "") or "").strip()
        persona = (scenario.get("user_persona", "") or "employee").strip()
        ticket_id = scenario.get("context_ticket_id", "") or ""

        recent = []
        for msg in history[-6:]:
            role = "USER" if msg.get("role") == "user" else "BOT"
            content = (msg.get("content") or "")[:400]
            recent.append(f"{role}: {content}")
        conv = "\n".join(recent)

        extra_rules = ""
        if family == "attachment":
            extra_rules = (
                "\n- Never invent a fake ticket number.\n"
                f"- If a ticket number is needed, use this exact one if available: {ticket_id}\n"
                "- Never claim a file was uploaded unless bot/user context clearly says it was uploaded.\n"
            )

        prompt = (
            f"Scenario title: {title}\n"
            f"Goal: {goal}\n"
            f"Persona: {persona}\n"
            f"Family: {family}\n\n"
            f"Conversation so far:\n{conv}\n\n"
            f"Latest bot message:\n{(cva_response or '')[:1200]}\n\n"
            "Write the NEXT user reply.\n"
            "Rules:\n"
            "- Be USER, not the bot.\n"
            "- Answer the bot's actual question.\n"
            "- If bot asks for missing details, provide them directly.\n"
            "- Do not repeat old replies.\n"
            "- Do not explain your reasoning.\n"
            "- Keep it under 60 words.\n"
            f"{extra_rules}"
            "- Return only the user reply."
        )

        return {
            "system": (
                "You are simulating an employee replying to an IT support bot. "
                "You must answer the bot's latest question naturally and briefly. "
                "Return only the employee's next message."
            ),
            "prompt": prompt,
        }
