import os
import smtplib
import logging
from datetime import datetime, timedelta
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def _make_period() -> str:
    end = datetime.now()
    start = end - timedelta(days=7)
    return f"{start.strftime('%Y/%m/%d')}〜{end.strftime('%Y/%m/%d')}"


def _connect(address: str, password: str) -> smtplib.SMTP:
    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
    server.ehlo()
    server.starttls()
    server.login(address, password)
    return server


def send_report(pdf_path: str, used_model: str, address: str, password: str) -> None:
    period = _make_period()

    msg = MIMEMultipart()
    msg["From"] = address
    msg["To"] = address
    msg["Subject"] = f"【週次AIレポート】{period}"

    body = (
        f"週次AIレポートをお届けします。\n\n"
        f"対象期間: {period}\n"
        f"使用モデル: {used_model}\n\n"
        f"添付のPDFをご確認ください。\n"
    )
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with open(pdf_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f'attachment; filename="{os.path.basename(pdf_path)}"',
    )
    msg.attach(part)

    with _connect(address, password) as server:
        server.sendmail(address, address, msg.as_string())

    logger.info("レポートメール送信完了")


def send_error(error_message: str, address: str, password: str) -> None:
    msg = MIMEMultipart()
    msg["From"] = address
    msg["To"] = address
    msg["Subject"] = "【週次AIレポート】エラーが発生しました"

    body = (
        "週次AIレポートの生成に失敗しました。\n\n"
        f"エラー内容:\n{error_message}\n\n"
        "GitHub Actions のログを確認してください。\n"
    )
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with _connect(address, password) as server:
            server.sendmail(address, address, msg.as_string())
        logger.info("エラーメール送信完了")
    except Exception as e:
        logger.error(f"エラーメール送信も失敗: {e}")
