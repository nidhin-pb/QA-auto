"""Configuration v2 (adds attachments staging)"""
from pydantic import BaseModel, Field


class TeamsConfig(BaseModel):
    email: str = ""
    password: str = ""
    teams_url: str = "https://teams.microsoft.com/v2/"
    cva_app_name: str = "IT Servicedesk AI"


class AIConfig(BaseModel):
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    bytez_api_key: str = ""          # set via UI/env/local config
    bytez_model: str = "openai/gpt-4o"
    bytez_fallback_models: list = Field(default_factory=lambda: ["openai/gpt-oss-20b", "Qwen/Qwen3-0.6B"])


class AppConfig(BaseModel):
    teams: TeamsConfig = TeamsConfig()
    ai: AIConfig = AIConfig()
    headless: bool = False

    screenshot_dir: str = "screenshots"
    report_dir: str = "reports"

    # NEW:
    attachments_dir: str = "attachments"
    staged_attachments: list = Field(default_factory=list)   # full local paths

    max_wait_for_response: int = 90
    message_check_interval: float = 2.0
    browser_slow_mo: int = 100


app_config = AppConfig()
