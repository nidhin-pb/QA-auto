class StructuredResultFixer:
    """
    Keeps status/final_status aligned for structured scenarios.
    """

    @staticmethod
    def normalize(result):
        if result.status == "passed":
            result.final_status = "PASS"

        elif result.status == "failed":
            result.final_status = "FAIL"

        elif result.status == "skipped":
            if not result.final_status or result.final_status in ("PASS", "FAIL"):
                result.final_status = "SKIPPED"

        elif result.status == "error":
            result.final_status = "ERROR"

        return result
