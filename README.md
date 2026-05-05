# 週次 AI レポート自動配信ツール

毎週月曜日 8:00（JST）に、直近1週間の LLM・生成 AI 関連ニュースを PDF にまとめて Gmail で自分宛に送信するツールです。

---

## セットアップ手順

### 1. GitHub リポジトリを作成する

1. [github.com](https://github.com) にログイン
2. 右上の「+」→「New repository」をクリック
3. Repository name を入力（例：`weekly-ai-report`）
4. **Private** を選択して「Create repository」

### 2. このコードを GitHub にアップロードする

ローカルで以下を実行（Git がインストールされている場合）：

```bash
cd weekly-ai-report
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/あなたのユーザー名/weekly-ai-report.git
git push -u origin main
```

Git を使いたくない場合は、GitHub の画面から「uploading an existing file」でファイルをドラッグ＆ドロップしてもOKです。

### 3. Gmail のアプリパスワードを取得する

1. [myaccount.google.com](https://myaccount.google.com) にアクセス
2. 「セキュリティ」→「2段階認証プロセス」を有効化（まだの場合）
3. 「2段階認証プロセス」ページ下部の「アプリパスワード」をクリック
4. アプリ名を適当に入力（例：`weekly-ai-report`）して「作成」
5. 表示された **16文字のパスワード**をメモする

### 4. GitHub Secrets を登録する

GitHub リポジトリの「Settings」→「Secrets and variables」→「Actions」→「New repository secret」で以下の3つを登録：

| Name | Value |
|------|-------|
| `GEMINI_API_KEY` | Gemini API キー |
| `GMAIL_ADDRESS` | Gmail アドレス（例：example@gmail.com） |
| `GMAIL_APP_PASSWORD` | 手順3で取得したアプリパスワード（スペースなし） |

---

## 実行方法

### 自動実行
毎週月曜日 8:00 JST に GitHub Actions が自動で実行します。

### 手動実行
1. GitHub リポジトリの「Actions」タブを開く
2. 左側の「Weekly AI Report」をクリック
3. 「Run workflow」ボタンをクリック→「Run workflow」

---

## レポートの構成

PDF は以下の4カテゴリに分類された 10 件程度のトピックで構成されます：

- **[NEW] 新サービス・プロダクトリリース** — 新しい AI モデル・サービスの発表
- **[LAB] 研究・技術動向** — 論文・技術的な進歩
- **[BIZ] 企業・業界動向** — 企業の動き・投資・規制
- **[INFO] その他注目トピック** — その他の重要ニュース

---

## ファイル構成

```
weekly-ai-report/
├── .github/workflows/weekly_report.yml  # GitHub Actions 定義
├── report/
│   ├── main.py          # エントリーポイント
│   ├── fetcher.py       # Gemini API でニュース収集
│   ├── generator.py     # PDF 生成
│   ├── mailer.py        # Gmail 送信
│   └── setup_fonts.py   # 日本語フォントのセットアップ
├── requirements.txt
└── README.md
```
