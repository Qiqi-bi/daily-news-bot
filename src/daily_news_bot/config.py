from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

from .models import SourceDef


ROOT_DIR = Path(__file__).resolve().parents[2]


@dataclass(slots=True)
class Settings:
    api_key: str
    base_url: str
    model: str
    fallback_models: tuple[str, ...]
    temperature: float
    timeout: int
    report_language: str
    top_events: int
    hours_back: int
    per_source_limit: int
    api_source_limit: int
    feishu_webhook_url: str
    feishu_app_id: str
    feishu_app_secret: str
    feishu_send_chat_id: str
    feishu_send_chat_name: str
    newsapi_key: str
    finnhub_api_key: str
    finnhub_news_categories: tuple[str, ...]
    alpha_vantage_api_key: str
    polygon_api_key: str
    marketaux_api_key: str


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().lstrip("\ufeff")
        value = value.strip().strip('"').strip("'")
        values[key] = value
    return values


def _pick(env_file_values: dict[str, str], key: str, default: str) -> str:
    runtime = os.getenv(key)
    if runtime is not None and runtime != "":
        return runtime
    file_value = env_file_values.get(key)
    if file_value is not None and file_value != "":
        return file_value
    return default


def _split_csv(value: str) -> tuple[str, ...]:
    items = [item.strip() for item in value.split(",") if item.strip()]
    deduped: list[str] = []
    for item in items:
        if item not in deduped:
            deduped.append(item)
    return tuple(deduped)


def load_settings() -> Settings:
    env_path = ROOT_DIR / ".env"

    if load_dotenv:
        load_dotenv(env_path)

    env_file_values = _read_env_file(env_path)
    model = _pick(env_file_values, "NEWS_MODEL", "deepseek-chat").strip()
    fallback_models = tuple(
        item for item in _split_csv(_pick(env_file_values, "NEWS_FALLBACK_MODELS", "")) if item != model
    )

    return Settings(
        api_key=_pick(env_file_values, "NEWS_API_KEY", "").strip(),
        base_url=_pick(env_file_values, "NEWS_BASE_URL", "https://api.deepseek.com").strip(),
        model=model,
        fallback_models=fallback_models,
        temperature=float(_pick(env_file_values, "NEWS_TEMPERATURE", "0.2")),
        timeout=int(_pick(env_file_values, "NEWS_TIMEOUT", "120")),
        report_language=_pick(env_file_values, "REPORT_LANGUAGE", "zh-CN").strip(),
        top_events=int(_pick(env_file_values, "TOP_EVENTS", "6")),
        hours_back=int(_pick(env_file_values, "HOURS_BACK", "18")),
        per_source_limit=int(_pick(env_file_values, "PER_SOURCE_LIMIT", "12")),
        api_source_limit=int(_pick(env_file_values, "API_SOURCE_LIMIT", "12")),
        feishu_webhook_url=_pick(env_file_values, "FEISHU_WEBHOOK_URL", "").strip(),
        feishu_app_id=_pick(env_file_values, "FEISHU_APP_ID", "").strip(),
        feishu_app_secret=_pick(env_file_values, "FEISHU_APP_SECRET", "").strip(),
        feishu_send_chat_id=(
            _pick(env_file_values, "FEISHU_SEND_CHAT_ID", "").strip()
            or _pick(env_file_values, "FEISHU_RECEIPT_CHAT_ID", "").strip()
        ),
        feishu_send_chat_name=(
            _pick(env_file_values, "FEISHU_SEND_CHAT_NAME", "").strip()
            or _pick(env_file_values, "FEISHU_RECEIPT_CHAT_NAME", "").strip()
        ),
        newsapi_key=_pick(env_file_values, "NEWSAPI_KEY", "").strip(),
        finnhub_api_key=_pick(env_file_values, "FINNHUB_API_KEY", "").strip(),
        finnhub_news_categories=_split_csv(
            _pick(env_file_values, "FINNHUB_NEWS_CATEGORIES", "general,forex,crypto,merger")
        ),
        alpha_vantage_api_key=_pick(env_file_values, "ALPHA_VANTAGE_API_KEY", "").strip(),
        polygon_api_key=_pick(env_file_values, "POLYGON_API_KEY", "").strip(),
        marketaux_api_key=_pick(env_file_values, "MARKETAUX_API_KEY", "").strip(),
    )


def load_sources(path: str | None = None) -> list[SourceDef]:
    source_path = Path(path) if path else ROOT_DIR / "config" / "sources.yaml"
    with source_path.open("r", encoding="utf-8") as file:
        payload = yaml.safe_load(file) or {}

    result: list[SourceDef] = []
    for item in payload.get("sources", []):
        result.append(
            SourceDef(
                name=item["name"],
                url=item["url"],
                category=item.get("category", "general"),
                region=item.get("region", "global"),
                weight=float(item.get("weight", 1.0)),
                official=bool(item.get("official", False)),
            )
        )
    return result
