"""
CVA QA Testing Automation Platform - Main FastAPI Application
"""
import os
import asyncio
import json
from typing import Optional, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from config import app_config
from test_engine import TestEngine
from test_scenarios import get_all_scenarios, get_categories
from websocket_manager import ws_manager
from utils import ensure_dir

# Create necessary directories
ensure_dir("screenshots")
ensure_dir("reports")

app = FastAPI(title="CVA QA Testing Automation", version="1.0.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global test engine instance
test_engine: Optional[TestEngine] = None


# ---- Request Models ----

class LoginRequest(BaseModel):
    email: str
    password: str
    headless: bool = False
    cva_app_name: str = "IT Servicedesk AI"


class RunTestsRequest(BaseModel):
    scenario_ids: Optional[List[str]] = None


# ---- API Endpoints ----

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/scenarios")
async def get_scenarios():
    """Get all available test scenarios."""
    scenarios = get_all_scenarios()
    categories = get_categories()
    return {
        "scenarios": scenarios,
        "categories": categories,
        "total": len(scenarios),
    }


@app.get("/api/goals")
async def get_goals():
    """Get test goals/objectives - used by frontend dashboard."""
    scenarios = get_all_scenarios()
    goals = []
    for s in scenarios:
        goals.append({
            "id": s["id"],
            "name": s["name"],
            "category": s["category"],
            "goal": s.get("goal", ""),
            "priority": s.get("priority", "medium"),
            "validations": s.get("validations", []),
        })
    return {"goals": goals, "total": len(goals)}


@app.post("/api/initialize")
async def initialize_engine(request: LoginRequest):
    """Initialize the test engine with Teams credentials."""
    global test_engine

    try:
        # Update config
        app_config.teams.email = request.email
        app_config.teams.password = request.password
        app_config.headless = request.headless
        app_config.teams.cva_app_name = request.cva_app_name

        # Create and initialize test engine
        test_engine = TestEngine()
        success = await test_engine.initialize(request.email, request.password)

        if success:
            return {"status": "success", "message": "Initialized and ready!"}
        else:
            raise HTTPException(status_code=500, detail="Failed to initialize. Check credentials.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/run-tests")
async def run_tests(request: RunTestsRequest):
    """Start running test scenarios."""
    global test_engine

    if not test_engine:
        raise HTTPException(status_code=400, detail="Engine not initialized. Call /api/initialize first.")

    if test_engine.is_running:
        raise HTTPException(status_code=400, detail="Tests are already running.")

    # Run tests in background
    asyncio.create_task(test_engine.run_all_tests(request.scenario_ids))

    return {"status": "started", "message": "Tests started. Watch live view for progress."}


@app.post("/api/run-journeys")
async def run_journeys():
    """Run Journey Mode - human-like multi-topic sessions."""
    global test_engine
    if not test_engine:
        raise HTTPException(status_code=400, detail="Engine not initialized.")
    if test_engine.is_running:
        raise HTTPException(status_code=400, detail="Already running.")

    asyncio.create_task(test_engine.run_journeys(sessions=2))
    return {"status": "started", "mode": "journeys", "sessions": 2}


@app.post("/api/stop-tests")
async def stop_tests():
    """Stop running tests."""
    global test_engine

    if test_engine and test_engine.is_running:
        await test_engine.stop_tests()
        return {"status": "stopping", "message": "Stopping tests..."}

    return {"status": "not_running", "message": "No tests currently running."}


@app.get("/api/results")
async def get_results():
    """Get current test results."""
    global test_engine

    if not test_engine:
        return {"results": [], "summary": {}}

    return test_engine.get_results_summary()


@app.get("/api/reports")
async def list_reports():
    """List available report files."""
    report_dir = app_config.report_dir
    if not os.path.exists(report_dir):
        return {"reports": []}

    files = [f for f in os.listdir(report_dir) if f.endswith(".xlsx")]
    files.sort(reverse=True)
    return {"reports": files}


@app.get("/api/reports/{filename}")
async def download_report(filename: str):
    """Download a report file."""
    filepath = os.path.join(app_config.report_dir, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Report not found")

    return FileResponse(
        filepath,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
    )


@app.post("/api/cleanup")
async def cleanup():
    """Cleanup resources."""
    global test_engine

    if test_engine:
        await test_engine.cleanup()
        test_engine = None

    return {"status": "cleaned", "message": "Resources cleaned up."}


# ---- WebSocket ----

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates to frontend."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, receive any commands from frontend
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ---- Serve Frontend (production) ----

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
