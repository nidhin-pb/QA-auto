import re
from validators.base_validator import BaseValidator


def normalize_kb(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())


class NetworkValidator(BaseValidator):
    def validate(self, result, conversation):
        bot_reply = (result.actual_first_reply or "").lower()
        kb_links = getattr(result, "kb_links_found", [])

        # Basic VPN troubleshooting detection with normalized KB comparison
        if "vpn" in bot_reply and any("vpn" in normalize_kb(link) for link in kb_links):
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
