from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import requests

from .config import ROOT_DIR, Settings


DEBUG_DIR = ROOT_DIR / "outputs"
DEBUG_JSON_PATH = DEBUG_DIR / "llm_last_response.json"
DEBUG_TEXT_PATH = DEBUG_DIR / "llm_last_response.txt"
DEBUG_REQUEST_PATH = DEBUG_DIR / "llm_last_request.json"
DEBUG_STATUS_PATH = DEBUG_DIR / "llm_last_status.json"
THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
FENCED_BLOCK_RE = re.compile(r"^```(?:markdown|md)?\s*(.*?)\s*```$", re.IGNORECASE | re.DOTALL)



def _save_debug(
    payload: dict[str, Any],
    raw_text: str = "",
    data: dict[str, Any] | None = None,
    *,
    endpoint: str = "",
    status_code: int | None = None,
    error: str = "",
    attempts: list[dict[str, Any]] | None = None,
    selected_model: str = "",
) -> None:
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    request_payload = dict(payload)
    if endpoint:
        request_payload["endpoint"] = endpoint
    DEBUG_REQUEST_PATH.write_text(json.dumps(request_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    DEBUG_TEXT_PATH.write_text(raw_text or "", encoding="utf-8")
    if data is not None:
        DEBUG_JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    status_payload: dict[str, Any] = {
        "ok": not error and (status_code is None or 200 <= status_code < 300),
        "status_code": status_code,
        "error": error,
    }
    if selected_model:
        status_payload["selected_model"] = selected_model
    if attempts is not None:
        status_payload["attempts"] = attempts
    DEBUG_STATUS_PATH.write_text(json.dumps(status_payload, ensure_ascii=False, indent=2), encoding="utf-8")



def _sanitize_model_text(text: str | None) -> str | None:
    if not isinstance(text, str):
        return None

    cleaned = THINK_BLOCK_RE.sub("", text).strip()
    fenced = FENCED_BLOCK_RE.match(cleaned)
    if fenced:
        cleaned = fenced.group(1).strip()

    return cleaned or None



def _text_from_content(content: Any) -> str | None:
    if isinstance(content, str):
        return _sanitize_model_text(content)

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            item_text = _text_from_content(item)
            if item_text:
                parts.append(item_text)
        return "\n".join(parts).strip() or None

    if isinstance(content, dict):
        for key in ("text", "content", "output_text"):
            value = content.get(key)
            item_text = _text_from_content(value)
            if item_text:
                return item_text
    return None



def _extract_content(data: dict[str, Any]) -> str | None:
    direct_text = _text_from_content(data.get("text")) or _text_from_content(data.get("output_text"))
    if direct_text:
        return direct_text

    choices = data.get("choices") or []
    if isinstance(choices, list) and choices:
        first_choice = choices[0] if isinstance(choices[0], dict) else {}
        for key in ("text", "message", "delta"):
            choice_text = _text_from_content(first_choice.get(key))
            if choice_text:
                return choice_text

    output = data.get("output") or data.get("outputs")
    output_text = _text_from_content(output)
    if output_text:
        return output_text

    candidates = data.get("candidates") or []
    if isinstance(candidates, list) and candidates:
        candidate = candidates[0] if isinstance(candidates[0], dict) else {}
        candidate_text = _text_from_content(candidate.get("content")) or _text_from_content(candidate.get("text"))
        if candidate_text:
            return candidate_text

    nested_data = data.get("data")
    if isinstance(nested_data, dict) and nested_data is not data:
        return _extract_content(nested_data)

    return None



def _build_payload(model: str, settings: Settings, system_prompt: str, user_prompt: str) -> dict[str, Any]:
    return {
        "model": model,
        "temperature": settings.temperature,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }



def generate_report(settings: Settings, system_prompt: str, user_prompt: str) -> str | None:
    endpoint = settings.base_url.rstrip("/") + "/chat/completions"

    if not settings.api_key or not settings.model:
        missing = "NEWS_API_KEY" if not settings.api_key else "NEWS_MODEL"
        payload = _build_payload(settings.model or "", settings, system_prompt, user_prompt)
        _save_debug(payload, endpoint=endpoint, error=f"Missing {missing}")
        return None

    headers = {
        "Authorization": f"Bearer {settings.api_key}",
        "Content-Type": "application/json",
    }

    attempts: list[dict[str, Any]] = []
    models_to_try = [settings.model, *settings.fallback_models]

    for model_name in models_to_try:
        payload = _build_payload(model_name, settings, system_prompt, user_prompt)
        try:
            response = requests.post(endpoint, headers=headers, json=payload, timeout=settings.timeout)
        except requests.RequestException as exc:
            attempts.append({"model": model_name, "ok": False, "error": f"{type(exc).__name__}: {exc}"})
            continue

        raw_text = response.text
        try:
            data = response.json()
        except ValueError:
            if response.ok:
                content = _sanitize_model_text(raw_text)
                if content:
                    _save_debug(payload, raw_text, endpoint=endpoint, status_code=response.status_code, attempts=attempts + [{"model": model_name, "ok": True}], selected_model=model_name)
                    return content
            attempts.append({"model": model_name, "ok": False, "status_code": response.status_code, "error": raw_text[:300]})
            continue

        content = _extract_content(data) if response.ok else None
        if response.ok and content:
            _save_debug(payload, raw_text, data, endpoint=endpoint, status_code=response.status_code, attempts=attempts + [{"model": model_name, "ok": True}], selected_model=model_name)
            return content

        attempts.append(
            {
                "model": model_name,
                "ok": False,
                "status_code": response.status_code,
                "error": (data.get("error") if isinstance(data, dict) else None) or raw_text[:300],
            }
        )

    final_payload = _build_payload(models_to_try[0], settings, system_prompt, user_prompt)
    final_error = attempts[-1]["error"] if attempts else "No model attempts were made"
    _save_debug(final_payload, endpoint=endpoint, error=str(final_error), attempts=attempts)
    return None
