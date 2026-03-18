from typing import Dict, List


class AttachmentReplyGuard:
    """
    Prevents AI from inventing ticket numbers or file names in attachment flows.
    """

    @staticmethod
    def build_reply(scenario: Dict, cva_response: str, ticket_id: str = "", uploaded_files: List[str] = None, upload_succeeded: bool = False) -> str:
        uploaded_files = uploaded_files or []
        cva = (cva_response or "").lower()

        if not upload_succeeded:
            # Before actual upload success, do NOT claim upload happened
            if any(x in cva for x in ["upload", "drag and drop", "attachment icon", "attach file", "upload from this device"]):
                return ""
            return ""

        names = ", ".join([p.split("/")[-1] for p in uploaded_files]) if uploaded_files else "the uploaded file"

        if "ticket number" in cva or "which incident" in cva or "which ticket" in cva:
            return f"The incident number is {ticket_id}."

        if "file name" in cva or "which file" in cva:
            return f"The file name is {names}. Please attach it to ticket {ticket_id}."

        return f"I uploaded {names}. Please attach it to ticket {ticket_id} and confirm."
