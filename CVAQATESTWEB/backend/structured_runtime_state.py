class StructuredRuntimeState:
    """
    Small helper to persist structured validation/goal metadata on TestResult.
    """

    @staticmethod
    def ensure(result):
        if not hasattr(result, "structured_family"):
            result.structured_family = ""
        if not hasattr(result, "alternate_outcome"):
            result.alternate_outcome = False
        if not hasattr(result, "alternate_reason"):
            result.alternate_reason = ""
        if not hasattr(result, "goal_achieved_reason"):
            result.goal_achieved_reason = ""
        return result
