class TeamsAttachmentDebugger:
    @staticmethod
    def summarize_failure() -> str:
        return (
            "Attachment upload failed before file preview appeared in Teams. "
            "Likely selector/path mismatch in current Teams UI (+ -> Attach file -> Upload from this device)."
        )
