import json
from datetime import datetime

HISTORY_FILE = "reports/history.json"

def record_run(results):
    summary = {
        "timestamp": str(datetime.now()),
        "total": len(results),
        "passed": sum(1 for r in results if getattr(r, 'final_status', r.status) == "PASS"),
        "failed": sum(1 for r in results if getattr(r, 'final_status', r.status) == "FAIL"),
    }

    try:
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
    except:
        history = []

    history.append(summary)

    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)
