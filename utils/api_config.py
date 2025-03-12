"""
APIキーと環境変数の設定を一元管理するモジュール
"""

import os
import sys
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# デバッグモードの設定
DEBUG = os.getenv("DEBUG", "true").lower() == "true"


# APIキーの確認と警告表示
def check_api_keys():
    """必要なAPIキーが設定されているか確認し、警告を表示する関数"""
    if not os.environ.get("GEMINI_API_KEY"):
        print(
            "警告: GEMINI_API_KEYが設定されていません。.envファイルまたはStreamlitCloudの環境変数に追加してください。"
        )

    if not os.environ.get("GOOGLE_PLACE_API_KEY"):
        print(
            "警告: GOOGLE_PLACE_API_KEYが設定されていません。.envファイルまたはStreamlitCloudの環境変数に追加してください。"
        )

    if not os.environ.get("GOOGLE_API_KEY"):
        print(
            "警告: GOOGLE_API_KEYが設定されていません。.envファイルまたはStreamlitCloudの環境変数に追加してください。"
        )


# APIキーの確認
check_api_keys()

# デバッグ情報の表示
if DEBUG:
    print("環境変数の設定:")
    print(
        f"GEMINI_API_KEY: {'設定済み' if 'GEMINI_API_KEY' in os.environ and os.environ['GEMINI_API_KEY'] else '未設定'}"
    )
    print(
        f"OPENAI_API_KEY: {'設定済み' if 'OPENAI_API_KEY' in os.environ and os.environ['OPENAI_API_KEY'] else '未設定'}"
    )
    print(f"GOOGLE_CSE_ID: {'設定済み' if 'GOOGLE_CSE_ID' in os.environ and os.environ['GOOGLE_CSE_ID'] else '未設定'}")
    print(
        f"GOOGLE_API_KEY: {'設定済み' if 'GOOGLE_API_KEY' in os.environ and os.environ['GOOGLE_API_KEY'] else '未設定'}"
    )
    print(
        f"GOOGLE_PLACE_API_KEY: {'設定済み' if 'GOOGLE_PLACE_API_KEY' in os.environ and os.environ['GOOGLE_PLACE_API_KEY'] else '未設定'}"
    )
    print(f"MAPBOX_TOKEN: {'設定済み' if 'MAPBOX_TOKEN' in os.environ and os.environ['MAPBOX_TOKEN'] else '未設定'}")
    print(f"DEBUG: {DEBUG}")

# Gemini APIの初期化
try:
    if "GEMINI_API_KEY" in os.environ and os.environ["GEMINI_API_KEY"]:
        import google.generativeai as genai

        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        print("Gemini APIを初期化しました")
    else:
        print("Gemini APIキーが設定されていないため、初期化をスキップします")
except Exception as e:
    print(f"Gemini API初期化エラー: {str(e)}")

# 他のモジュールからインポートするための変数をエクスポート
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_PLACE_API_KEY = os.environ.get("GOOGLE_PLACE_API_KEY", "")
MAPBOX_TOKEN = os.environ.get("MAPBOX_TOKEN", "")
