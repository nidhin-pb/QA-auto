"""
CVA QA Testing Automation Platform - Main FastAPI Application (v2: attachments upload)
"""
import os
import asyncio
import json
from typing import Optional, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from pydantic import BaseModel

from config import app_config
from test_engine import TestEngine
from test_scenarios import get_all_scenarios, get_categories
from websocket_manager import ws_manager
from utils import ensure_dir, sanitize_filename
from excel_suite_loader import load_suite_from_bytes
from structured_family_filtering import StructuredFamilyFiltering
from structured_suite_loader import load_and_plan_structured_suite
from safe_structured_filters import get_safe_structured_subset, get_recommended_first_run_subset
from history import record_run

ensure_dir(app_config.screenshot_dir)
ensure_dir(app_config.report_dir)
ensure_dir(app_config.attachments_dir)

app = FastAPI(title="CVA QA Testing Automation", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

test_engine: Optional[TestEngine] = None
excel_suite = {"suite_name": "", "cases": [], "errors": []}
structured_suite = {
    "suite_name": "",
    "cases": [],
    "errors": [],
    "preview": [],
    "plan_summary": {},
    "sheet_summaries": [],
}


class LoginRequest(BaseModel):
    email: str
    password: str
    headless: bool = False
    cva_app_name: str = "IT Servicedesk AI"


class RunTestsRequest(BaseModel):
    scenario_ids: Optional[List[str]] = None


class RunStructuredSuiteRequest(BaseModel):
    scenario_ids: Optional[List[str]] = None
    modules: Optional[List[str]] = None
    families: Optional[List[str]] = None
    automation_levels: Optional[List[str]] = None
    execution_modes: Optional[List[str]] = None
    priorities: Optional[List[str]] = None
    limit: Optional[int] = None


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/scenarios")
async def get_scenarios():
    scenarios = get_all_scenarios()
    categories = get_categories()
    return {"scenarios": scenarios, "categories": categories, "total": len(scenarios)}


@app.get("/api/excel-suite")
async def get_excel_suite():
    return {
        "suite_name": excel_suite.get("suite_name", ""),
        "count": len(excel_suite.get("cases", [])),
        "errors": excel_suite.get("errors", []),
        "preview": [
            {
                "id": c["id"],
                "client": c.get("excel", {}).get("client", ""),
                "module": c.get("excel", {}).get("module", ""),
                "user_query": c.get("initial_message", "")[:120],
                "action": c.get("excel", {}).get("action", "")[:120],
                "source_kb": c.get("excel", {}).get("source_kb", ""),
                "tool_calling": c.get("excel", {}).get("tool_calling_queries", False),
            }
            for c in excel_suite.get("cases", [])[:50]
        ]
    }


@app.post("/api/excel-suite/upload")
async def upload_excel_suite(file: UploadFile = File(...)):
    raw = await file.read()
    parsed = load_suite_from_bytes(file.filename or "suite.xlsx", raw)

    excel_suite["suite_name"] = parsed["suite_name"]
    excel_suite["cases"] = parsed["cases"]
    excel_suite["errors"] = parsed["errors"]

    await ws_manager.send_log("info", f"Loaded Excel Suite: {excel_suite['suite_name']} cases={len(excel_suite['cases'])}")
    if excel_suite["errors"]:
        await ws_manager.send_log("warning", f"Excel Suite parse warnings: {excel_suite['errors']}")
    return {"status": "ok", "suite_name": excel_suite["suite_name"], "count": len(excel_suite["cases"]), "errors": excel_suite["errors"]}


@app.post("/api/run-excel-suite")
async def run_excel_suite():
    global test_engine
    if not test_engine:
        raise HTTPException(status_code=400, detail="Engine not initialized. Call /api/initialize first.")
    if test_engine.is_running:
        raise HTTPException(status_code=400, detail="Already running.")
    if not excel_suite.get("cases"):
        raise HTTPException(status_code=400, detail="No Excel suite loaded. Upload first.")

    asyncio.create_task(test_engine.run_custom_suite(excel_suite["cases"], suite_name=excel_suite.get("suite_name", "Excel Suite")))
    return {"status": "started", "mode": "excel_suite", "count": len(excel_suite["cases"])}


@app.post("/api/initialize")
async def initialize_engine(request: LoginRequest):
    global test_engine
    try:
        app_config.teams.email = request.email
        app_config.teams.password = request.password
        app_config.headless = request.headless
        app_config.teams.cva_app_name = request.cva_app_name

        test_engine = TestEngine()
        success = await test_engine.initialize(request.email, request.password)

        if success:
            return {"status": "success", "message": "Initialized and ready!"}
        raise HTTPException(status_code=500, detail="Failed to initialize. Check credentials.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/run-tests")
async def run_tests(request: RunTestsRequest):
    global test_engine
    if not test_engine:
        raise HTTPException(status_code=400, detail="Engine not initialized. Call /api/initialize first.")
    if test_engine.is_running:
        raise HTTPException(status_code=400, detail="Tests are already running.")
    asyncio.create_task(test_engine.run_all_tests(request.scenario_ids))
    return {"status": "started", "message": "Tests started. Watch live view for progress."}


@app.post("/api/stop-tests")
async def stop_tests():
    global test_engine
    if test_engine and test_engine.is_running:
        await test_engine.stop_tests()
        return {"status": "stopping", "message": "Stopping tests..."}
    return {"status": "not_running", "message": "No tests currently running."}


@app.get("/api/results")
async def get_results():
    global test_engine
    if not test_engine:
        return {"results": [], "summary": {}}
    return test_engine.get_results_summary()


@app.get("/api/reports")
async def list_reports():
    report_dir = app_config.report_dir
    if not os.path.exists(report_dir):
        return {"reports": []}
    files = [f for f in os.listdir(report_dir) if f.endswith(".xlsx")]
    files.sort(reverse=True)
    return {"reports": files}


@app.get("/api/reports/{filename}")
async def download_report(filename: str):
    filepath = os.path.join(app_config.report_dir, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(
        filepath,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
    )


# ------------------ NEW: Attachments staging ------------------

@app.get("/api/attachments")
async def list_attachments():
    # only return basenames for UI
    staged = app_config.staged_attachments or []
    return {
        "count": len(staged),
        "files": [{"name": os.path.basename(p), "path": p} for p in staged],
    }


@app.post("/api/attachments/upload")
async def upload_attachments(files: List[UploadFile] = File(...)):
    ensure_dir(app_config.attachments_dir)

    saved_paths = []
    for f in files[:2]:  # limit to 2 as per your requirement
        raw_name = f.filename or "attachment"
        safe_name = sanitize_filename(raw_name)
        out_path = os.path.join(app_config.attachments_dir, safe_name)

        # Avoid overwrite
        base, ext = os.path.splitext(out_path)
        i = 1
        while os.path.exists(out_path):
            out_path = f"{base}_{i}{ext}"
            i += 1

        content = await f.read()
        with open(out_path, "wb") as fp:
            fp.write(content)

        saved_paths.append(out_path)

    # stage globally for test run
    app_config.staged_attachments = saved_paths
    await ws_manager.send_log("info", f"Staged attachments: {', '.join(os.path.basename(p) for p in saved_paths)}")

    return {
        "status": "ok",
        "count": len(saved_paths),
        "files": [{"name": os.path.basename(p), "path": p} for p in saved_paths],
    }


@app.get("/api/structured-suite")
async def get_structured_suite():
    return {
        "suite_name": structured_suite.get("suite_name", ""),
        "count": len(structured_suite.get("cases", [])),
        "errors": structured_suite.get("errors", []),
        "plan_summary": structured_suite.get("plan_summary", {}),
        "sheet_summaries": structured_suite.get("sheet_summaries", []),
        "preview": structured_suite.get("preview", [])[:100],
    }


@app.post("/api/structured-suite/upload")
async def upload_structured_suite(file: UploadFile = File(...)):
    raw = await file.read()
    parsed = load_and_plan_structured_suite(file.filename or "structured_suite.xlsx", raw)

    structured_suite["suite_name"] = parsed["suite_name"]
    structured_suite["cases"] = parsed["legacy_cases"]   # current engine-compatible cases
    structured_suite["errors"] = parsed["errors"]
    structured_suite["preview"] = parsed["preview"]
    structured_suite["plan_summary"] = parsed["plan_summary"]
    structured_suite["sheet_summaries"] = parsed["sheet_summaries"]

    await ws_manager.send_log(
        "info",
        f"Loaded Structured Suite: {structured_suite['suite_name']} cases={len(structured_suite['cases'])}"
    )
    if structured_suite["errors"]:
        await ws_manager.send_log("warning", f"Structured Suite parse warnings: {structured_suite['errors']}")

    return {
        "status": "ok",
        "suite_name": structured_suite["suite_name"],
        "count": len(structured_suite["cases"]),
        "errors": structured_suite["errors"],
        "plan_summary": structured_suite["plan_summary"],
        "sheet_summaries": structured_suite["sheet_summaries"],
        "preview": structured_suite["preview"][:100],
    }


@app.get("/api/structured-suite/safe-subset")
async def get_structured_suite_safe_subset():
    cases = get_safe_structured_subset(structured_suite.get("cases", []))
    return {
        "suite_name": structured_suite.get("suite_name", ""),
        "count": len(cases),
        "preview": [
            {
                "id": c.get("id", ""),
                "name": c.get("name", ""),
                "priority": c.get("priority", ""),
                "execution_mode": c.get("execution_mode", ""),
                "automation_level": c.get("automation_level", ""),
                "family": c.get("family", "") or ((c.get("excel", {}) or {}).get("family", "")),
            }
            for c in cases[:50]
        ]
    }


@app.get("/api/structured-suite/recommended-first-run")
async def get_structured_suite_recommended_first_run():
    cases = get_recommended_first_run_subset(structured_suite.get("cases", []))
    return {
        "suite_name": structured_suite.get("suite_name", ""),
        "count": len(cases),
        "preview": [
            {
                "id": c.get("id", ""),
                "name": c.get("name", ""),
                "priority": c.get("priority", ""),
                "execution_mode": c.get("execution_mode", ""),
                "automation_level": c.get("automation_level", ""),
                "family": c.get("family", "") or ((c.get("excel", {}) or {}).get("family", "")),
            }
            for c in cases[:20]
        ]
    }


@app.post("/api/run-structured-suite")
async def run_structured_suite(request: RunStructuredSuiteRequest):
    global test_engine
    if not test_engine:
        raise HTTPException(status_code=400, detail="Engine not initialized. Call /api/initialize first.")
    if test_engine.is_running:
        raise HTTPException(status_code=400, detail="Already running.")
    if not structured_suite.get("cases"):
        raise HTTPException(status_code=400, detail="No structured suite loaded. Upload first.")

    cases = structured_suite["cases"][:]

    cases = StructuredFamilyFiltering.apply(
        cases,
        modules=request.modules,
        families=request.families,
        execution_modes=request.execution_modes,
        automation_levels=request.automation_levels,
        priorities=request.priorities,
    )

    if request.scenario_ids:
        wanted = set(request.scenario_ids)
        cases = [c for c in cases if c.get("id") in wanted]

    if request.limit and request.limit > 0:
        cases = cases[: request.limit]

    if not cases:
        raise HTTPException(status_code=400, detail="No structured scenarios matched the selected filters.")

    asyncio.create_task(
        test_engine.run_custom_suite(
            cases,
            suite_name=structured_suite.get("suite_name", "Structured Suite")
        )
    )
    return {
        "status": "started",
        "mode": "structured_suite",
        "count": len(cases),
        "filters": request.model_dump(),
    }


@app.get("/api/structured-suite/recommended-first-run-ids")
async def get_structured_suite_recommended_first_run_ids():
    cases = get_recommended_first_run_subset(structured_suite.get("cases", []))
    return {
        "suite_name": structured_suite.get("suite_name", ""),
        "scenario_ids": [c.get("id", "") for c in cases[:10]],
        "count": min(len(cases), 10),
    }


@app.get("/api/structured-suite/classification-summary")
async def get_structured_suite_classification_summary():
    cases = structured_suite.get("cases", []) or []

    modules = {}
    families = {}
    execution_modes = {}
    automation_levels = {}
    priorities = {}

    for c in cases:
        module = c.get("category", "") or "Unknown"
        family = c.get("family", "") or ((c.get("excel", {}) or {}).get("family", "")) or "generic"
        mode = c.get("execution_mode", "") or "unknown"
        level = c.get("automation_level", "") or "unknown"
        priority = c.get("priority", "") or "unknown"

        modules[module] = modules.get(module, 0) + 1
        families[family] = families.get(family, 0) + 1
        execution_modes[mode] = execution_modes.get(mode, 0) + 1
        automation_levels[level] = automation_levels.get(level, 0) + 1
        priorities[priority] = priorities.get(priority, 0) + 1

    return {
        "suite_name": structured_suite.get("suite_name", ""),
        "total": len(cases),
        "modules": modules,
        "families": families,
        "execution_modes": execution_modes,
        "automation_levels": automation_levels,
        "priorities": priorities,
    }


@app.post("/api/attachments/clear")
async def clear_attachments():
    app_config.staged_attachments = []
    await ws_manager.send_log("info", "Cleared staged attachments")
    return {"status": "ok", "count": 0, "files": []}


@app.post("/api/cleanup")
async def cleanup():
    global test_engine
    if test_engine:
        await test_engine.cleanup()
        test_engine = None
    return {"status": "cleaned", "message": "Resources cleaned up."}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


frontend_build = os.path.join(os.path.dirname(__file__), "..", "frontend", "build")
if os.path.exists(frontend_build):
    app.mount("/static", StaticFiles(directory=os.path.join(frontend_build, "static")), name="static")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = os.path.join(frontend_build, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_build, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
