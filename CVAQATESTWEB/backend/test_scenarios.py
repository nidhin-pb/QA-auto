"""Test Scenarios v6 - adds deeper conversations + mandatory KB hyperlink checks."""

TEST_SCENARIOS = [
    {
        "id": "KB-001", "name": "Troubleshoot Slow PC",
        "category": "Knowledge & Troubleshooting",
        "description": "Ask about a slow PC and get troubleshooting help",
        "goal": "CVA provides step-by-step troubleshooting with KB hyperlink",
        "initial_message": "my pc is running really slow, apps take forever to open",
        "min_turns": 3, "max_turns": 6,
        "validations": ["provides_troubleshooting_steps", "includes_kb_hyperlink", "asks_follow_up_questions"],
        "priority": "high",
    },
    {
        "id": "KB-002", "name": "Troubleshoot VPN",
        "category": "Knowledge & Troubleshooting",
        "description": "VPN connectivity issues with error code",
        "goal": "CVA provides VPN troubleshooting steps with KB hyperlink",
        "initial_message": "I can't connect to VPN, it keeps timing out with error code 809",
        "min_turns": 3, "max_turns": 6,
        "validations": ["provides_troubleshooting_steps", "includes_kb_hyperlink"],
        "priority": "high",
    },
    {
        "id": "INC-001", "name": "Create Incident Ticket",
        "category": "Ticket Management",
        "description": "Create incident ticket for hardware issue",
        "goal": "CVA creates an incident ticket and returns INC number",
        "initial_message": "Please create a ticket for me. My monitor is completely black and won't turn on. I already tried different cables.",
        "min_turns": 1, "max_turns": 4,
        "validations": ["creates_incident", "returns_inc_number", "shows_ticket_details"],
        "priority": "critical",
    },
    {
        "id": "INC-002", "name": "Troubleshoot Then Create Ticket",
        "category": "Ticket Management",
        "description": "Report BSOD, try troubleshooting, then request ticket if unresolved",
        "goal": "CVA provides troubleshooting first (with KB hyperlink), then creates ticket when asked",
        "initial_message": "My PC keeps getting blue screen error CRITICAL_PROCESS_DIED",
        "min_turns": 2, "max_turns": 6,
        "validations": ["provides_troubleshooting_steps", "includes_kb_hyperlink", "asks_follow_up_questions"],
        "priority": "critical",
    },
    {
        "id": "SR-001", "name": "Software Install Request",
        "category": "Service Request",
        "description": "Request Adobe Acrobat Pro installation",
        "goal": "CVA shows service catalog items / complete request card",
        "initial_message": "I want to install Adobe Acrobat Pro on my laptop",
        "min_turns": 1, "max_turns": 3,
        "validations": ["shows_catalog_item", "detects_service_request"],
        "priority": "high",
    },
    {
        "id": "RET-001", "name": "View Open Tickets",
        "category": "Ticket Retrieval",
        "description": "View open tickets",
        "goal": "CVA lists open INC and RITM tickets",
        "initial_message": "Show my open tickets",
        "min_turns": 1, "max_turns": 2,
        "validations": ["shows_ticket_list", "includes_inc_numbers"],
        "priority": "critical",
    },
    {
        "id": "RET-002", "name": "View Closed Tickets",
        "category": "Ticket Retrieval",
        "description": "View closed/resolved tickets",
        "goal": "CVA shows closed tickets or explains limitations",
        "initial_message": "Show my closed tickets",
        "min_turns": 1, "max_turns": 2,
        "validations": ["handles_gracefully"],
        "priority": "high",
    },
    {
        "id": "AGT-001", "name": "Request Live Agent",
        "category": "Live Agent",
        "description": "Request transfer to human agent",
        "goal": "CVA initiates agent handoff (or clearly states unavailability)",
        "initial_message": "I need to talk to a human agent please, this is urgent",
        "min_turns": 1, "max_turns": 3,
        "validations": ["initiates_handoff"],
        "priority": "high",
    },
    {
        "id": "LANG-001", "name": "Spanish Language",
        "category": "Multilingual",
        "description": "Chat in Spanish to test language detection",
        "goal": "CVA detects Spanish and responds in Spanish",
        "initial_message": "Tengo un problema con la pantalla de mi computadora portátil que parpadea y no se muestra ningún mensaje de error",
        "min_turns": 2, "max_turns": 4,
        "validations": ["detects_language", "responds_in_same_language"],
        "priority": "medium",
    },
    {
        "id": "EDGE-001", "name": "Gibberish Input",
        "category": "Edge Cases",
        "description": "Send gibberish to test graceful handling",
        "goal": "CVA handles gibberish gracefully",
        "initial_message": "asdfjkl qwerty zxcvbnm 12345 !@#$%^&*",
        "min_turns": 1, "max_turns": 2,
        "validations": ["handles_gracefully", "no_error_crash"],
        "priority": "medium",
    },
    {
        "id": "EDGE-002", "name": "Sensitive Data Warning",
        "category": "Edge Cases",
        "description": "Send password in chat - test PII handling + KB hyperlink for account lockout",
        "goal": "CVA handles login issue safely and provides KB link without requesting password again",
        "initial_message": "My password is Test@123 and I can't login to my account",
        "min_turns": 2, "max_turns": 4,
        "validations": ["handles_gracefully", "asks_follow_up_questions", "includes_kb_hyperlink"],
        "priority": "high",
    },
    {
        "id": "ATT-001", "name": "Add Attachment to Latest Ticket",
        "category": "Ticket Attachments",
        "description": "Ask CVA to add attachments to the most recently created ticket",
        "goal": "CVA accepts attachments in Teams and acknowledges upload / associates with ticket",
        "initial_message": "I want to add an attachment to my latest ticket. Can you help?",
        "min_turns": 2, "max_turns": 4,
        "validations": ["handles_gracefully"],
        "priority": "critical",
        "requires_attachments": True,
        "attach_on_user_turn": 2,   # upload attachments when sending follow-up
    },
    {
        "id": "ATT-002", "name": "Retrieve Ticket Attachments",
        "category": "Ticket Attachments",
        "description": "Ask CVA to show/download attachments for the latest ticket",
        "goal": "CVA provides downloadable attachment option in Teams (or explains limitation)",
        "initial_message": "Can you show me the attachments for my latest ticket?",
        "min_turns": 1, "max_turns": 3,
        "validations": ["handles_gracefully"],
        "priority": "high",
    },
]


def get_all_scenarios():
    return TEST_SCENARIOS


def get_scenarios_by_category(c):
    return [s for s in TEST_SCENARIOS if c.lower() in s["category"].lower()]


def get_scenario_by_id(sid):
    return next((s for s in TEST_SCENARIOS if s["id"] == sid), None)


def get_categories():
    return list(set(s["category"] for s in TEST_SCENARIOS))
