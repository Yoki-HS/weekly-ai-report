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
    "新サービス・プロダクトリリース",
    "研究・技術動向",
    "企業・業界動向",
    "その他注目トピック",
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
    return f"""直近1週間（{start_date}〜{end_date}）のLLM・生成AI・AIサービスに関する重要なニュースを収集してください。

以下の4カテゴリに分けて、合計10件のトピックをまとめてください：
1. 新サービス・プロダクトリリース（新しいAIモデル、サービス、機能のリリース）
2. 研究・技術動向（論文、技術的な進歩、ベンチマーク結果など）
3. 企業・業界動向（企業の動き、提携、投資、規制など）
4. その他注目トピック（上記に当てはまらない重要なAIニュース）

各トピックに含めること：
- タイトル（日本語）
- カテゴリ名（上記4つのいずれかを正確に）
- 要約（1〜2文、日本語）
- 参照URL（実在するURLを必ず含める）

以下のJSON配列のみを返してください。マークダウンのコードブロックや説明文は不要です：
[
  {{
    "category": "新サービス・プロダクトリリース",
    "title": "タイトル",
    "summary": "要約文",
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
    for cat in CATEGORY_NAMES:
        if any(keyword in raw for keyword in cat.split("・")):
            return cat
    return "その他注目トピック"


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
