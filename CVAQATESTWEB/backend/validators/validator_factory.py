from validators.greeting_validator import GreetingValidator
from validators.out_of_scope_validator import OutOfScopeValidator
from validators.ticket_validator import TicketValidator
from validators.catalog_validator import CatalogValidator
from validators.network_validator import NetworkValidator
from validators.rule_based_validator import RuleBasedValidator
from validators.base_validator import BaseValidator


class ValidatorFactory:

    @staticmethod
    def get_validator(module_name: str, scenario: dict = None):
        scenario = scenario or {}

        # If scenario has explicit rule set, prefer generic rule engine
        validations = scenario.get("validations") or []
        if validations:
            return RuleBasedValidator()

        module = (module_name or "").lower()

        if "greeting" in module:
            return GreetingValidator()

        if "out-of-scope" in module or "out of scope" in module:
            return OutOfScopeValidator()

        if "ticket" in module:
            return TicketValidator()

        if "catalog" in module:
            return CatalogValidator()

        if "network" in module:
            return NetworkValidator()

        return BaseValidator()
