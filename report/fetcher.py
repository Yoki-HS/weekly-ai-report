import json
import re
import time
import logging
from datetime import datetime, timedelta

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]

MAX_RETRIES = 3
RETRY_WAIT = 2

CATEGORY_NAMES = [
    "新サービス・プロダクトリリース",
    "研究・技術動向",
    "企業・業界動向",
    "その他注目トピック",
]


def _get_tools(model: str) -> list:
    if "2.0" in model or "2.5" in model:
        return [types.Tool(google_search=types.GoogleSearch())]
    return [types.Tool(google_search_retrieval=types.GoogleSearchRetrieval())]


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

    # マークダウンコードブロックを除去
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = text.replace("```", "")

    # JSON配列を抽出
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        return json.loads(match.group())

    return json.loads(text)


def _normalize_category(raw: str) -> str:
    raw = raw.strip()
    if raw in CATEGORY_NAMES:
        return raw

    # 部分一致で最も近いカテゴリに寄せる
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

    last_error = None
    for model in MODELS:
        tools = _get_tools(model)
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"[{model}] 試行 {attempt}/{MAX_RETRIES}")
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(tools=tools),
                )
                topics = _extract_json(response.text)

                # カテゴリ名を正規化
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
