class QAScoring:
    """
    QA scoring model for tester-facing reports.
    Score out of 100.
    """

    @staticmethod
    def calculate(result) -> dict:
        status = (getattr(result, "status", "") or "").lower()
        final_status = (getattr(result, "final_status", "") or "").upper()
        semantic_score = int(getattr(result, "semantic_score", 0) or 0)
        alternate = bool(getattr(result, "alternate_outcome", False))
        failure_type = (getattr(result, "failure_type", "") or "").lower()
        validations_failed = getattr(result, "validations_failed", []) or []
        goal_reason = (getattr(result, "goal_achieved_reason", "") or "").lower()
        notes = (getattr(result, "notes", "") or "").lower()

        # --- Skipped / blocked / unsupported ---
        if status == "skipped":
            display = "BLOCKED"
            auto_level = (getattr(result, "automation_level", "") or "").lower()
            if auto_level == "manual":
                display = "MANUAL"
            elif final_status in ("UNSUPPORTED", "BLOCKED", "MANUAL"):
                display = final_status

            return {
                "qa_score": 0,
                "qa_grade": "Not Tested",
                "display_status": display,
            }

        if status == "error":
            return {
                "qa_score": 0,
                "qa_grade": "Critical",
                "display_status": "ERROR",
            }

        # --- Base score by outcome ---
        if status == "failed":
            base = 20
        elif final_status == "PASS_WITH_WARNING":
            base = 65
        elif final_status == "PASS":
            base = 85
        else:
            base = 50

        # Semantic bonus (0-10 normalized)
        sem_bonus = min(max(semantic_score, 0), 10)
        score = base + sem_bonus

        # Penalties
        if alternate:
            score -= 10

        if "automation limitation" in failure_type:
            score -= 15

        if validations_failed:
            score -= min(len(validations_failed) * 10, 30)

        # Extra penalty for "unsupported feature" style passes
        if "not supported" in notes or "cannot access" in notes or "do not have access" in notes:
            score -= 15

        # Extra penalty for "generic structured response"
        if "generic structured response" in notes:
            score -= 10

        score = max(0, min(100, score))

        # Human-friendly grade
        if score >= 90:
            grade = "Excellent"
        elif score >= 75:
            grade = "Good"
        elif score >= 60:
            grade = "Fair"
        elif score >= 40:
            grade = "Poor"
        else:
            grade = "Critical"

        # Display status
        if final_status == "PASS_WITH_WARNING":
            display_status = "PASS_WITH_WARNING"
        elif status == "failed":
            display_status = "FAIL"
        elif final_status == "PASS":
            display_status = "PASS"
        else:
            display_status = status.upper()

        return {
            "qa_score": score,
            "qa_grade": grade,
            "display_status": display_status,
        }
