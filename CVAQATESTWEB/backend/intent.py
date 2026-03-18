from enum import Enum

class Intent(Enum):
    GREETING = "greeting"
    OUT_OF_SCOPE = "out_of_scope"
    CREATE_TICKET = "create_ticket"
    UPDATE_TICKET = "update_ticket"
    STATUS_CHECK = "status_check"
    CLOSE_TICKET = "close_ticket"
    REOPEN_TICKET = "reopen_ticket"
    CATALOG = "catalog"
    TROUBLESHOOT = "troubleshoot"
    UNKNOWN = "unknown"
