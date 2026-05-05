"""
GitHub Actions 実行時に日本語フォントを fonts/ ディレクトリへ配置するスクリプト。
1. Google Fonts GitHub からダウンロードを試みる
2. 失敗した場合はシステムフォント（fc-list）から探してコピー
3. それも失敗した場合はスキップ（PDF は ASCII フォントにフォールバック）
"""

import logging
import os
import shutil
import subprocess
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
FONTS_DIR = os.path.join(PROJECT_ROOT, "fonts")

FONT_URLS = {
    "NotoSansJP-Regular.ttf": (
        "https://github.com/google/fonts/raw/main"
        "/ofl/notosansjp/static/NotoSansJP-Regular.ttf"
    ),
    "NotoSansJP-Bold.ttf": (
        "https://github.com/google/fonts/raw/main"
        "/ofl/notosansjp/static/NotoSansJP-Bold.ttf"
    ),
}


def _download(filename: str, url: str, dest: str) -> bool:
    try:
        logger.info(f"ダウンロード中: {filename}")
        urllib.request.urlretrieve(url, dest)
        logger.info(f"ダウンロード成功: {filename}")
        return True
    except Exception as e:
        logger.warning(f"ダウンロード失敗 ({filename}): {e}")
        return False


def _find_system_font(bold: bool) -> str | None:
    try:
        style = "Bold" if bold else "Regular"
        result = subprocess.run(
            ["fc-list", f":lang=ja:style={style}", "--format=%{file}\n"],
            capture_output=True, text=True,
        )
        fonts = [f for f in result.stdout.strip().splitlines() if f]
        # NotoSansCJK を優先（Serifは除外）
        for f in fonts:
            if "NotoSansCJK" in f and "Serif" not in f:
                return f
        for f in fonts:
            if "NotoSans" in f and "Serif" not in f:
                return f
        for f in fonts:
            if "Noto" in f and "Serif" not in f:
                return f
        return fonts[0] if fonts else None
    except Exception:
        return None


def _write_ttc_index(dest: str, source: str) -> None:
    """TTC ファイルの場合、日本語サブフォントのインデックスをサイドカーファイルに保存。"""
    if not source.lower().endswith(".ttc"):
        return
    # NotoSansCJK TTC のサブフォント順: SC=0, TC=1, JP=2, KR=3
    idx = 2 if "NotoSansCJK" in source and "jp" not in source.lower() else 0
    idx_file = dest + ".ttc_idx"
    with open(idx_file, "w") as f:
        f.write(str(idx))
    logger.info(f"TTC subfontIndex={idx} を記録: {idx_file}")


def setup() -> None:
    os.makedirs(FONTS_DIR, exist_ok=True)

    for filename, url in FONT_URLS.items():
        dest = os.path.join(FONTS_DIR, filename)
        if os.path.exists(dest):
            logger.info(f"既存フォントをスキップ: {filename}")
            continue

        if _download(filename, url, dest):
            continue

        # フォールバック: システムフォント
        is_bold = "Bold" in filename
        system_font = _find_system_font(bold=is_bold)
        if system_font:
            shutil.copy(system_font, dest)
            _write_ttc_index(dest, system_font)
            logger.info(f"システムフォントを使用: {system_font} -> {filename}")
        else:
            logger.warning(f"フォントが見つかりませんでした: {filename}（ASCII フォールバック使用）")


if __name__ == "__main__":
    setup()
