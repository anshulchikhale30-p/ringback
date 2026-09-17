import os

from dotenv import load_dotenv

load_dotenv()


def _get(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


class Settings:
    app_name: str = "RingBack AI"
    app_tagline: str = "Never miss revenue again. We call your missed callers back."

    assemblyai_api_key: str | None = _get("ASSEMBLYAI_API_KEY")
    assemblyai_voice: str = _get("ASSEMBLYAI_VOICE", "alba")
    analytics_model: str = _get("AAI_ANALYTICS_MODEL", "gemini-2.5-flash-lite")

    # The publicly reachable URL of THIS server (used for HTTP tool URLs that
    # AssemblyAI calls from its own servers). In production this is your
    # Render/Railway/Fly URL, e.g. https://ringback.onrender.com.
    public_base_url: str = _get("PUBLIC_BASE_URL", "").rstrip("/")

    agent_base_url: str = _get("AAI_AGENT_BASE_URL", "https://agents.assemblyai.com")
    llm_gateway_url: str = _get("AAI_LLM_GATEWAY_URL", "https://llm-gateway.assemblyai.com/v1")

    data_file: str = _get("RINGBACK_DATA_FILE", "data/store.json")
    token_ttl_seconds: int = int(_get("AAI_TOKEN_TTL", "300"))
    max_session_seconds: int = int(_get("AAI_MAX_SESSION", "900"))
    port: int = int(_get("PORT", "8000"))
    seed_demo: bool = _get("SEED_DEMO", "true").lower() == "true"

    # Rough average value of a single recovered call. Used only for the
    # "revenue saved" estimator on the demo dashboard.
    avg_call_value: int = int(_get("AVG_CALL_VALUE", "125"))


settings = Settings()