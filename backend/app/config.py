from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.enums import App, ConnectorMode, ReasoningMode

ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SURGE_", env_file=".env", extra="ignore")

    version: str = "0.2.0"
    database_url: str = f"sqlite:///{ROOT_DIR / 'surge.db'}"

    connector_mode: ConnectorMode = ConnectorMode.DEMO
    sheets_mode: ConnectorMode | None = None
    github_mode: ConnectorMode | None = None
    slack_mode: ConnectorMode | None = None

    reasoning_mode: str = "auto"  # auto | llm | heuristic
    # Free-tier hybrid reasoning. The primary provider's model chain is tried first; the secondary's
    # chain is only used once every primary model is rate limited, exhausted or failing.
    llm_primary: str = "groq"  # groq | gemini
    groq_api_key: str = Field(
        default="", validation_alias=AliasChoices("SURGE_GROQ_API_KEY", "GROQ_API_KEY", "groq_api_key")
    )
    gemini_api_key: str = Field(
        default="", validation_alias=AliasChoices("SURGE_GEMINI_API_KEY", "GEMINI_API_KEY", "gemini_api_key")
    )
    groq_models: str = "openai/gpt-oss-120b,openai/gpt-oss-20b,qwen/qwen3.8-27b,qwen/qwen3.6-27b"
    gemini_models: str = "gemini-3.8-flash,gemini-3.7-flash,gemini-3.6-flash"
    llm_reasoning_effort: str = "low"
    llm_timeout_s: float = 45.0
    llm_rate_limit_cooldown_s: float = 20.0
    llm_quota_cooldown_s: float = 3600.0
    llm_error_cooldown_s: float = 15.0
    llm_max_wait_s: float = 8.0

    firebase_project_id: str = Field(
        default="", validation_alias=AliasChoices("SURGE_FIREBASE_PROJECT_ID", "FIREBASE_PROJECT_ID")
    )

    demo_scenario: str = "checkout_regression_01"
    # Simulated provider round-trip latency for DEMO connectors; disclosed via /api/connectors.
    demo_latency_ms: int = 350

    tool_timeout_s: float = 15.0
    tool_max_retries: int = 2
    retry_base_delay_s: float = 0.25
    investigation_timeout_s: float = 600.0
    max_tool_calls: int = 14

    cors_origins: str = (
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
    )
    max_request_bytes: int = 64_000
    secret_key: str = ""
    frontend_url: str = "http://localhost:3000"
    public_base_url: str = "http://localhost:8000"

    scenarios_dir: Path = ROOT_DIR / "evaluation" / "scenarios"
    worlds_dir: Path = ROOT_DIR / "evaluation" / "worlds"
    reports_dir: Path = ROOT_DIR / "evaluation" / "reports"

    github_token: str = ""
    github_repo: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""

    slack_bot_token: str = ""
    slack_user_token: str = ""
    slack_channels: str = ""
    slack_client_id: str = ""
    slack_client_secret: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_access_token: str = ""
    google_refresh_token: str = ""
    sheets_spreadsheet_id: str = ""
    sheets_tab: str = "metrics_hourly"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def slack_channel_list(self) -> list[str]:
        return [c.strip() for c in self.slack_channels.split(",") if c.strip()]

    @property
    def groq_model_list(self) -> list[str]:
        return [m.strip() for m in self.groq_models.split(",") if m.strip()]

    @property
    def gemini_model_list(self) -> list[str]:
        return [m.strip() for m in self.gemini_models.split(",") if m.strip()]

    def mode_for(self, app: App | str) -> ConnectorMode:
        override = getattr(self, f"{App(app).value}_mode", None)
        return override or self.connector_mode

    def resolved_reasoning_mode(self) -> ReasoningMode:
        if self.reasoning_mode == ReasoningMode.LLM:
            return ReasoningMode.LLM
        if self.reasoning_mode == ReasoningMode.HEURISTIC:
            return ReasoningMode.HEURISTIC
        return ReasoningMode.LLM if (self.groq_api_key or self.gemini_api_key) else ReasoningMode.HEURISTIC


@lru_cache
def get_settings() -> Settings:
    return Settings()
