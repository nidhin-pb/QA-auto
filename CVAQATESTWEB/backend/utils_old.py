"""
Utility functions for CVA QA Automation
"""
import os
import re
import json
import datetime
from typing import Optional


def ensure_dir(directory: str):
    """Create directory if it doesn't exist."""
    os.makedirs(directory, exist_ok=True)


def timestamp():
    """Get current timestamp string."""
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def timestamp_readable():
    """Get human-readable timestamp."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def sanitize_filename(name: str) -> str:
    """Remove invalid characters from filename."""
    return re.sub(r'[<>:"/\\|?*]', '_', name)


def extract_ticket_number(text: str) -> Optional[str]:
    """Extract INC or RITM ticket number from text."""
    # Match INC followed by digits
    inc_match = re.search(r'INC\d{7,10}', text, re.IGNORECASE)
    if inc_match:
        return inc_match.group(0).upper()

    # Match RITM followed by digits
    ritm_match = re.search(r'RITM\d{7,10}', text, re.IGNORECASE)
    if ritm_match:
        return ritm_match.group(0).upper()

    return None


def extract_all_ticket_numbers(text: str) -> list:
    """Extract all ticket numbers from text."""
    inc_matches = re.findall(r'INC\d{7,10}', text, re.IGNORECASE)
    ritm_matches = re.findall(r'RITM\d{7,10}', text, re.IGNORECASE)
    return [t.upper() for t in inc_matches + ritm_matches]


def contains_error_indicators(text: str) -> bool:
    """Check if response contains error indicators."""
    error_phrases = [
        "sorry, i can't",
        "i'm unable to",
        "error occurred",
        "something went wrong",
        "please try again",
        "i don't understand",
        "could not process",
        "failed to",
        "not available",
        "service unavailable",
    ]
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in error_phrases)


def contains_citation(text: str) -> bool:
    """Check if response contains document citations/references."""
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
    text_lower = text.lower()
    return any(indicator in text_lower for indicator in citation_indicators)


def contains_ticket_confirmation(text: str) -> bool:
    """Check if response confirms ticket creation."""
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
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in confirmation_phrases)


def contains_ticket_list(text: str) -> bool:
    """Check if response contains a list of tickets."""
    return bool(re.search(r'INC\d{7,10}', text, re.IGNORECASE)) or \
           bool(re.search(r'RITM\d{7,10}', text, re.IGNORECASE))


def contains_update_confirmation(text: str) -> bool:
    """Check if response confirms ticket update."""
    phrases = [
        "updated successfully",
        "has been updated",
        "ticket updated",
        "update confirmed",
        "changes have been",
    ]
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in phrases)


def contains_resolve_confirmation(text: str) -> bool:
    """Check if response confirms ticket resolution."""
    phrases = [
        "marked as resolved",
        "status: resolved",
        "has been resolved",
        "resolved successfully",
        "ticket is resolved",
    ]
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in phrases)


def contains_close_confirmation(text: str) -> bool:
    """Check if response confirms ticket closure."""
    phrases = [
        "closed successfully",
        "status: closed",
        "has been closed",
        "fully closed",
        "ticket closed",
    ]
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in phrases)


def contains_live_agent_handoff(text: str) -> bool:
    """Check if response indicates live agent handoff."""
    phrases = [
        "connect with",
        "live agent",
        "human agent",
        "transferring",
        "handover",
        "start chat handover",
        "agent will be with you",
        "servicenow agent",
    ]
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in phrases)


def contains_follow_up_question(text: str) -> bool:
    """Check if CVA is asking follow-up questions."""
    indicators = [
        "could you",
        "can you",
        "please provide",
        "please let me know",
        "would you like",
        "please specify",
        "tell me more",
        "what is",
        "which",
        "?",
    ]
    text_lower = text.lower()
    question_count = text.count("?")
    return question_count > 0 or any(ind in text_lower for ind in indicators)


def contains_service_catalog(text: str) -> bool:
    """Check if response contains service catalog items / request forms."""
    phrases = [
        "service catalog",
        "catalog item",
        "catalog forms",
        "available catalog forms",
        "request form",
        "install software",
        "complete this request",
        "select the appropriate",
        "select appropriate",
        "service request",
        "servicenow catalog",
        "open request form",
        "submit your request",
    ]
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in phrases)


def detect_response_language(text: str) -> str:
    """Simple language detection based on character sets."""
    # Check for common non-English characters
    if re.search(r'[\u4e00-\u9fff]', text):
        return "Chinese"
    if re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):
        return "Japanese"
    if re.search(r'[\uac00-\ud7af]', text):
        return "Korean"
    if re.search(r'[\u0600-\u06ff]', text):
        return "Arabic"
    if re.search(r'[\u0900-\u097f]', text):
        return "Hindi"
    if re.search(r'[áéíóúñ¿¡]', text, re.IGNORECASE):
        return "Spanish"
    if re.search(r'[àâçéèêëïîôùûüÿœæ]', text, re.IGNORECASE):
        return "French"
    if re.search(r'[äöüß]', text, re.IGNORECASE):
        return "German"
    return "English"
