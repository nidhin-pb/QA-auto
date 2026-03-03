"""
Utility functions for CVA QA Automation
"""
import os
import re
import datetime
from typing import Optional, List


def ensure_dir(directory: str):
    os.makedirs(directory, exist_ok=True)


def timestamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def timestamp_readable():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def sanitize_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", name)


def extract_ticket_number(text: str) -> Optional[str]:
    """Extract INC or RITM ticket number from text, avoiding example numbers like 'e.g. INCxxxx'."""
    if not text:
        return None

    low = text.lower()

    # Find all candidates with positions
    candidates = []
    for m in re.finditer(r'INC\d{7,10}', text, re.IGNORECASE):
        candidates.append(("INC", m))
    for m in re.finditer(r'RITM\d{7,10}', text, re.IGNORECASE):
        candidates.append(("RITM", m))

    for _, m in candidates:
        start = m.start()
        ctx = low[max(0, start - 25): start]  # context before ticket
        # Skip examples/prompts
        if "e.g" in ctx or "example" in ctx or "for example" in ctx:
            continue
        return m.group(0).upper()

    return None


def extract_all_ticket_numbers(text: str) -> list:
    inc_matches = re.findall(r"INC\d{7,10}", text or "", re.IGNORECASE)
    ritm_matches = re.findall(r"RITM\d{7,10}", text or "", re.IGNORECASE)
    return [t.upper() for t in inc_matches + ritm_matches]


def extract_urls_from_text(text: str) -> List[str]:
    if not text:
        return []
    # basic url regex
    urls = re.findall(r"https?://[^\s)>\]]+", text)
    # cleanup trailing punctuation
    cleaned = []
    for u in urls:
        u = u.strip().rstrip(".,;]")
        if u not in cleaned:
            cleaned.append(u)
    return cleaned


def is_kb_link(url: str) -> bool:
    if not url:
        return False
    u = url.lower()
    # Your KB links look like Azure blob + pdf/docx query string
    if "knowledgebasestaging.blob.core.windows.net" in u:
        return True
    if any(u.endswith(ext) or (ext in u) for ext in [".pdf", ".docx", ".doc", ".pptx", ".xlsx"]):
        return True
    return False


def has_kb_hyperlink(links: List[str], text: str = "") -> bool:
    links = links or []
    if any(is_kb_link(u) for u in links):
        return True
    # fallback: sometimes URL may appear in plain text
    for u in extract_urls_from_text(text or ""):
        if is_kb_link(u):
            return True
    return False


def contains_error_indicators(text: str) -> bool:
    """
    Detect bot/platform failures, not user-described errors.
    Avoid false positives like: 'error message says "Service Unavailable"'.
    """
    t = (text or "").lower()

    # If bot is clearly quoting/relaying a user's error message, don't treat as bot failure
    user_error_context = any(k in t for k in [
        "error message says", "error message:", "shows an error", "message saying",
        "it shows an error", "it says:", "the error says"
    ])

    # Strong bot/platform failure indicators
    platform_fail_phrases = [
        "sorry, i can't",
        "sorry, i cannot",
        "i'm unable to",
        "i am unable to",
        "i can't process",
        "i cannot process",
        "could not process",
        "something went wrong",
        "error occurred",
        "temporarily unavailable",
        "please try again later",
        "i don't understand",
    ]

    if any(p in t for p in platform_fail_phrases):
        return True

    # Only treat these as failures if NOT in user-error context
    weaker_phrases = [
        "service unavailable",
        "failed to",
        "not available",
    ]
    if (not user_error_context) and any(p in t for p in weaker_phrases):
        return True

    return False


def contains_citation(text: str) -> bool:
    citation_indicators = [
        "citation:",
        "reference:",
        "source:",
        "kb article",
        "knowledge base",
        ".pdf",
        ".docx",
        "sop",
        "see full",
        "official guide",
        "http",
        "view details",
    ]
    text_lower = (text or "").lower()
    return any(indicator in text_lower for indicator in citation_indicators)


def contains_ticket_confirmation(text: str) -> bool:
    confirmation_phrases = [
        "ticket has been created",
        "incident ticket",
        "incident number",
        "service request",
        "ticket details",
        "has been created",
        "successfully created",
        "your incident",
        "your request",
    ]
    text_lower = (text or "").lower()
    return any(phrase in text_lower for phrase in confirmation_phrases)


def contains_ticket_list(text: str) -> bool:
    return bool(re.search(r"INC\d{7,10}", text or "", re.IGNORECASE)) or bool(
        re.search(r"RITM\d{7,10}", text or "", re.IGNORECASE)
    )


def contains_update_confirmation(text: str) -> bool:
    phrases = [
        "updated successfully",
        "has been updated",
        "ticket updated",
        "update confirmed",
        "changes have been",
    ]
    text_lower = (text or "").lower()
    return any(phrase in text_lower for phrase in phrases)


def contains_resolve_confirmation(text: str) -> bool:
    phrases = [
        "marked as resolved",
        "status: resolved",
        "has been resolved",
        "resolved successfully",
        "ticket is resolved",
    ]
    text_lower = (text or "").lower()
    return any(phrase in text_lower for phrase in phrases)


def contains_close_confirmation(text: str) -> bool:
    phrases = [
        "closed successfully",
        "status: closed",
        "has been closed",
        "fully closed",
        "ticket closed",
    ]
    text_lower = (text or "").lower()
    return any(phrase in text_lower for phrase in phrases)


def contains_live_agent_handoff(text: str) -> bool:
    """
    NOTE: We'll refine validation logic in TestEngine (Part 3)
    because 'no agents available' should not be a pass for real handoff.
    """
    phrases = [
        "start chat handover",
        "transferring",
        "handover started",
        "connecting you",
        "connecting to an agent",
    ]
    text_lower = (text or "").lower()
    return any(phrase in text_lower for phrase in phrases)


def contains_service_catalog(text: str) -> bool:
    phrases = [
        "service catalog",
        "catalog item",
        "request form",
        "install software",
        "complete this request",
        "service request",
        "servicenow catalog",
        "submit your request",
        "adobe acrobat",
    ]
    text_lower = (text or "").lower()
    return any(phrase in text_lower for phrase in phrases)


def detect_response_language(text: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", text or ""):
        return "Chinese"
    if re.search(r"[\u3040-\u309f\u30a0-\u30ff]", text or ""):
        return "Japanese"
    if re.search(r"[\uac00-\ud7af]", text or ""):
        return "Korean"
    if re.search(r"[\u0600-\u06ff]", text or ""):
        return "Arabic"
    if re.search(r"[\u0900-\u097f]", text or ""):
        return "Hindi"
    if re.search(r"[áéíóúñ¿¡]", text or "", re.IGNORECASE):
        return "Spanish"
    if re.search(r"[àâçéèêëïîôùûüÿœæ]", text or "", re.IGNORECASE):
        return "French"
    if re.search(r"[äöüß]", text or "", re.IGNORECASE):
        return "German"
    return "English"
