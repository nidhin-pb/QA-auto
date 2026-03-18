class StructuredResultEnricher:
    @staticmethod
    def apply(result, validation: dict):
        if not result.scenario.get("execution_mode"):
            return result

        notes = validation.get("notes", []) or []
        failures = validation.get("failures", []) or []
        alternate = validation.get("alternate", False)
        alternate_reason = validation.get("alternate_reason", "") or ""

        result.alternate_outcome = bool(alternate)
        result.alternate_reason = alternate_reason

        if failures:
            result.notes = f"Structured validation failed: {failures[0]}"
        else:
            if alternate:
                result.notes = (
                    f"Structured workflow completed with warning: "
                    f"{alternate_reason or '; '.join(notes[:2])}"
                )
            else:
                result.notes = (
                    f"Structured validation passed: {'; '.join(notes[:2])}"
                    if notes else "Structured validation passed"
                )

        if alternate and result.status == "passed":
            result.final_status = "PASS_WITH_WARNING"

        return result
