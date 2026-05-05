import json
import re
import time
import logging
from datetime import datetime, timedelta

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# 自動取得できなかった場合のフォールバックリスト（新しい順）
FALLBACK_MODELS = [
    "gemini-2.5-flash-preview-04-17",
    "gemini-2.5-pro-exp-03-25",
    "gemini-2.0-flash-001",
    "gemini-2.0-flash-lite-001",
]

MAX_RETRIES = 3
RETRY_WAIT = 2

CATEGORY_NAMES = [
    "New Services & Products",
    "Research & Technology",
    "Business & Industry",
    "Other Notable Topics",
]


def _discover_models(client: genai.Client) -> list[str]:
    """APIキーで使えるGeminiモデルを動的に取得して優先順にソート。"""
    try:
        names = []
        for m in client.models.list():
            model_id = m.name.replace("models/", "")
            # generateContent 対応のGeminiモデルのみ
            if "gemini" not in model_id:
                continue
            if any(x in model_id for x in ["embedding", "aqa", "imagen", "veo"]):
                continue
            names.append(model_id)

        def _priority(name: str) -> tuple:
            # バージョン（大きいほど新しい）
            ver = 0.0
            for v in ["2.5", "2.0", "1.5", "1.0"]:
                if v in name:
                    ver = float(v)
                    break
            # flash > pro（コスト優先）
            speed = 0 if "flash" in name else 1
            # プレビュー・実験版は後回し
            stable = 0 if any(x in name for x in ["preview", "exp", "latest"]) else -1
            return (-ver, speed, stable)

        names.sort(key=_priority)
        logger.info(f"利用可能なモデル（上位5件）: {names[:5]}")
        return names if names else FALLBACK_MODELS

    except Exception as e:
        logger.warning(f"モデル一覧の取得失敗: {e} — フォールバックリストを使用")
        return FALLBACK_MODELS


def _build_prompt(start_date: str, end_date: str) -> str:
    return f"""Collect the most important news about LLMs, generative AI, and AI services from the past week ({start_date} to {end_date}).

Summarize 10 topics across these 4 categories:
1. New Services & Products (new AI models, services, or feature releases)
2. Research & Technology (papers, technical advances, benchmark results)
3. Business & Industry (company moves, partnerships, investments, regulations)
4. Other Notable Topics (important AI news that doesn't fit above)

Each topic must include:
- title (concise English title)
- category (use one of the 4 exact category names above)
- summary (1-2 sentences in English)
- url (a real, working URL)

Return ONLY a JSON array with no markdown code fences or explanation:
[
  {{
    "category": "New Services & Products",
    "title": "Topic title",
    "summary": "Short summary.",
    "url": "https://..."
  }}
]"""


def _extract_json(text: str) -> list:
    text = text.strip()
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = text.replace("```", "")
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(text)


def _normalize_category(raw: str) -> str:
    raw = raw.strip()
    if raw in CATEGORY_NAMES:
        return raw
    raw_lower = raw.lower()
    for cat in CATEGORY_NAMES:
        if any(word.lower() in raw_lower for word in cat.split() if len(word) > 3):
            return cat
    return "Other Notable Topics"


def fetch_topics(api_key: str) -> tuple[list[dict], str]:
    client = genai.Client(api_key=api_key)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    prompt = _build_prompt(
        start_date.strftime("%Y/%m/%d"),
        end_date.strftime("%Y/%m/%d"),
    )

    models = _discover_models(client)
    tools = [types.Tool(google_search=types.GoogleSearch())]

    last_error = None
    for model in models:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"[{model}] 試行 {attempt}/{MAX_RETRIES}")
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(tools=tools),
                )
                topics = _extract_json(response.text)

                for t in topics:
                    t["category"] = _normalize_category(t.get("category", ""))
                    t.setdefault("url", "")

                logger.info(f"[{model}] 成功 — {len(topics)} 件取得")
                return topics, model

            except Exception as e:
                last_error = e
                logger.warning(f"[{model}] attempt {attempt} 失敗: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_WAIT)

        logger.warning(f"[{model}] 全試行失敗、次のモデルへ移行")

    raise RuntimeError(f"全モデルで失敗。最後のエラー: {last_error}")
