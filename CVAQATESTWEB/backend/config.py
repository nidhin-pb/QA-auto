"""Configuration (hotfix: restore Bytez key defaults + allow env override)"""
import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


class TeamsConfig(BaseModel):
    email: str = ""
    password: str = ""
    teams_url: str = "https://teams.microsoft.com/v2/"
    cva_app_name: str = "IT Servicedesk AI"


class AIConfig(BaseModel):
    # optional
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    # Bytez SDK key (ENV overrides file default)
    bytez_api_key: str = os.getenv("BYTEZ_API_KEY", "2c38c79903e0f2190ab2c6bdcb4b4474")
    bytez_api_key_2: str = os.getenv("BYTEZ_API_KEY_2", "")
    bytez_model: str = os.getenv("BYTEZ_MODEL", "openai/gpt-4o")
    bytez_fallback_models: list = ["openai/gpt-oss-20b", "Qwen/Qwen3-0.6B", "inference-net/Schematron-3B", "google/gemma-3-1b-it"]


class AppConfig(BaseModel):
    teams: TeamsConfig = TeamsConfig()
    ai: AIConfig = AIConfig()
    headless: bool = False
    screenshot_dir: str = "screenshots"
    report_dir: str = "reports"

    # optional attachment staging (keep if you already added)
    attachments_dir: str = "attachments"
    staged_attachments: list = []

    max_wait_for_response: int = 120
    message_check_interval: float = 2.0
    browser_slow_mo: int = 100


app_config = AppConfig()
