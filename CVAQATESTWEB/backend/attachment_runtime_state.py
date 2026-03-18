class AttachmentRuntimeState:
    @staticmethod
    def ensure(result):
        if not hasattr(result, "attachment_upload_succeeded"):
            result.attachment_upload_succeeded = False
        if not hasattr(result, "attachment_uploaded_files"):
            result.attachment_uploaded_files = []
        return result
