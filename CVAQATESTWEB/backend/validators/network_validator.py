from validators.base_validator import BaseValidator


class NetworkValidator(BaseValidator):
    def validate(self, result, conversation):
        bot_reply = (result.actual_first_reply or "").lower()
        kb_links = getattr(result, "kb_links_found", [])

        # Basic VPN troubleshooting detection
        if "vpn" in bot_reply and any("vpn" in link.lower() for link in kb_links):
            return {
                "passed": True,
                "failures": [],
                "notes": ["VPN troubleshooting + KB link validated"]
            }

        return {
            "passed": False,
            "failures": ["VPN troubleshooting steps or KB link missing"],
            "notes": []
        }
