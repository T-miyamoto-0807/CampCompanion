"""
APIキーと環境変数の設定を一元管理するモジュール
"""

import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai
import streamlit as st

# 環境変数の読み込み
load_dotenv()

# デバッグモードの設定
DEBUG = os.getenv("DEBUG", "true").lower() == "true"


# Streamlit Cloudの環境変数設定
def load_streamlit_secrets():
    """Streamlit Cloudのシークレットから環境変数を設定する関数"""
    try:
        # Streamlitのシークレットファイルが存在するか確認
        import os.path

        secrets_paths = [
            os.path.expanduser("~/.streamlit/secrets.toml"),
            os.path.join(os.getcwd(), ".streamlit/secrets.toml"),
        ]

        secrets_exist = any(os.path.isfile(path) for path in secrets_paths)

        if secrets_exist and hasattr(st, "secrets"):
            if "api_keys" in st.secrets:
                # StreamlitのSecretsから環境変数を設定
                os.environ["GEMINI_API_KEY"] = st.secrets["api_keys"]["GEMINI_API_KEY"]
                os.environ["OPENAI_API_KEY"] = st.secrets["api_keys"]["OPENAI_API_KEY"]
                os.environ["GOOGLE_CSE_ID"] = st.secrets["api_keys"]["GOOGLE_CSE_ID"]
                os.environ["GOOGLE_API_KEY"] = st.secrets["api_keys"]["GOOGLE_API_KEY"]
                os.environ["GOOGLE_PLACE_API_KEY"] = st.secrets["api_keys"]["GOOGLE_PLACE_API_KEY"]
                os.environ["MAPBOX_TOKEN"] = st.secrets["api_keys"]["MAPBOX_TOKEN"]

                # デバッグ設定
                if "settings" in st.secrets and "DEBUG" in st.secrets["settings"]:
                    os.environ["DEBUG"] = str(st.secrets["settings"]["DEBUG"]).lower()

                if DEBUG:
                    print("StreamlitCloudのSecretsから環境変数を設定しました")
                return True
        return False
    except Exception as e:
        if DEBUG:
            print(f"Secretsの読み込みエラー: {str(e)}")
        return False


# Streamlit Cloudのシークレットから環境変数を設定
streamlit_secrets_loaded = load_streamlit_secrets()

# APIキーの取得
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_PLACE_API_KEY = os.getenv("GOOGLE_PLACE_API_KEY")
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")

# APIキーが設定されていない場合の警告
if not GEMINI_API_KEY:
    if DEBUG:
        print("警告: GEMINI_API_KEYが設定されていません。.envファイルまたはStreamlit Secretsを確認してください。")

if not GOOGLE_PLACE_API_KEY:
    if DEBUG:
        print("警告: GOOGLE_PLACE_API_KEYが設定されていません。.envファイルまたはStreamlit Secretsを確認してください。")

# Gemini APIの初期化
try:
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        if DEBUG:
            print("Gemini APIを初期化しました")
except Exception as e:
    if DEBUG:
        print(f"Gemini APIの初期化中にエラーが発生しました: {str(e)}")


# APIキーの状態をチェックする関数
def check_api_keys():
    """
    APIキーの設定状態を確認し、結果を辞書で返す関数

    Returns:
        dict: APIキーの設定状態
    """
    return {
        "GEMINI_API_KEY": bool(GEMINI_API_KEY),
        "OPENAI_API_KEY": bool(OPENAI_API_KEY),
        "GOOGLE_CSE_ID": bool(GOOGLE_CSE_ID),
        "GOOGLE_API_KEY": bool(GOOGLE_API_KEY),
        "GOOGLE_PLACE_API_KEY": bool(GOOGLE_PLACE_API_KEY),
        "MAPBOX_TOKEN": bool(MAPBOX_TOKEN),
        "DEBUG": DEBUG,
        "STREAMLIT_SECRETS_LOADED": streamlit_secrets_loaded,
    }


# APIキーの状態をデバッグ出力
if DEBUG:
    api_status = check_api_keys()
    print("\n===== API設定状態 =====")
    for key, status in api_status.items():
        print(f"{key}: {'設定済み' if status else '未設定'}")
    print("=======================\n")
