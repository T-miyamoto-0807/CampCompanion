"""
APIキーと環境変数の設定を一元管理するモジュール
"""

import os
import sys
from dotenv import load_dotenv
import streamlit as st

# 環境変数の読み込み
load_dotenv()

# デバッグモードの設定
DEBUG = os.getenv("DEBUG", "true").lower() == "true"


def load_streamlit_secrets():
    """Streamlit Cloudのシークレットから環境変数を設定する関数"""
    try:
        # st.secretsが存在するか確認
        if not hasattr(st, "secrets"):
            print("st.secretsが存在しません")
            return False

        # st.secretsにアクセスしようとしたときにFileNotFoundErrorが発生する可能性があるため、try-exceptで囲む
        try:
            # StreamlitCloudのシークレットから環境変数を設定
            if hasattr(st, "secrets"):
                # APIキーの設定
                if "GEMINI_API_KEY" in st.secrets:
                    os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
                if "OPENAI_API_KEY" in st.secrets:
                    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
                if "GOOGLE_CSE_ID" in st.secrets:
                    os.environ["GOOGLE_CSE_ID"] = st.secrets["GOOGLE_CSE_ID"]
                if "GOOGLE_API_KEY" in st.secrets:
                    os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]
                if "GOOGLE_PLACE_API_KEY" in st.secrets:
                    os.environ["GOOGLE_PLACE_API_KEY"] = st.secrets["GOOGLE_PLACE_API_KEY"]
                if "MAPBOX_TOKEN" in st.secrets:
                    os.environ["MAPBOX_TOKEN"] = st.secrets["MAPBOX_TOKEN"]

                # デバッグ設定
                if "DEBUG" in st.secrets:
                    os.environ["DEBUG"] = str(st.secrets["DEBUG"]).lower()

                print("StreamlitCloudのSecretsから環境変数を設定しました")
                return True
            return False
        except FileNotFoundError:
            print("Secretsファイルが見つかりません")
            return False
    except Exception as e:
        print(f"Secretsの読み込みエラー: {str(e)}")
        return False


# StreamlitCloudのシークレットから環境変数を設定
try:
    load_streamlit_secrets()
except Exception as e:
    print(f"StreamlitCloudの環境変数設定エラー: {str(e)}")


# APIキーの確認と警告表示
def check_api_keys():
    """必要なAPIキーが設定されているか確認し、警告を表示する関数"""
    if not os.environ.get("GEMINI_API_KEY"):
        print("警告: GEMINI_API_KEYが設定されていません。.envファイルに追加してください。")

    if not os.environ.get("GOOGLE_PLACE_API_KEY"):
        print("警告: GOOGLE_PLACE_API_KEYが設定されていません。.envファイルに追加してください。")

    if not os.environ.get("GOOGLE_API_KEY"):
        print("警告: GOOGLE_API_KEYが設定されていません。.envファイルに追加してください。")


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
