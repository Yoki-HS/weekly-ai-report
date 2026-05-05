import logging
import os
import sys
from datetime import datetime

# report/ ディレクトリを import パスに追加（直接実行時用）
sys.path.insert(0, os.path.dirname(__file__))

from fetcher import fetch_topics
from generator import generate_pdf
from mailer import send_error, send_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    gemini_api_key = os.environ["GEMINI_API_KEY"]
    gmail_address = os.environ["GMAIL_ADDRESS"]
    gmail_app_password = os.environ["GMAIL_APP_PASSWORD"]

    pdf_path = f"ai_report_{datetime.now().strftime('%Y%m%d')}.pdf"

    try:
        logger.info("=== 週次AIレポート生成開始 ===")

        logger.info("ニュース収集中...")
        topics, used_model = fetch_topics(gemini_api_key)
        logger.info(f"{len(topics)} 件取得（モデル: {used_model}）")

        logger.info("PDF生成中...")
        generate_pdf(topics, used_model, pdf_path)

        logger.info("メール送信中...")
        send_report(pdf_path, used_model, gmail_address, gmail_app_password)

        logger.info("=== 完了 ===")

    except Exception as e:
        logger.error(f"エラー発生: {e}", exc_info=True)
        send_error(str(e), gmail_address, gmail_app_password)
        sys.exit(1)

    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            logger.info(f"一時ファイル削除: {pdf_path}")


if __name__ == "__main__":
    main()
