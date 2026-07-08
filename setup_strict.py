import os
import subprocess

repo = "/Users/ah/CascadeProjects/quotepath-repro-strict"
files = [
    ("設計書_画面一覧.xlsx", b"PK\x03\x04\x14\x00\x00\x00\x08\x00placeholder xlsx binary content"),
    ("海上入出荷実績_設計書.md", "海上コンテナの入出荷実績を管理する設計書です。"),
    ("01_技術スタック選定.md", "本プロジェクトで採用する技術スタックの選定理由を記載します。"),
    ("画面設計/README.md", "# 画面設計\n\n画面一覧と画面遷移の説明。"),
    ("テスト計画書.md", "単体テスト、結合テスト、E2E テストの計画。"),
    ("データモデル設計.md", "ER 図とテーブル定義。"),
    ("画面遷移図_全体.md", "アプリケーション全体の画面遷移図。"),
    ("エラー処理設計書.md", "例外処理とエラーコードの設計。"),
    ("認証認可設計書.md", "OAuth2 / JWT を使った認証認可設計。"),
    ("ログ設計書.md", "ログ出力方針とフォーマット。"),
    ("バッチ設計書.md", "夜間バッチの処理フロー。"),
    ("外部連携設計書.md", "外部システムとの連携 IF 設計。"),
    ("操作マニュアル.md", "エンドユーザ向け操作マニュアル。"),
    ("運用設計書.md", "監視、アラート、バックアップ運用設計。"),
    ("メイン処理.py", "def main():\n    print('メイン処理')\n"),
    ("共通関数.py", "def helper():\n    return 42\n"),
]

for path, content in files:
    full = os.path.join(repo, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    if isinstance(content, bytes):
        with open(full, "wb") as f:
            f.write(content)
    else:
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
    subprocess.run(["git", "add", path], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", f"Add {path}", "--", path], cwd=repo, check=True)

print("Done: strict repo populated, one commit per file, zero ASCII-named files.")
