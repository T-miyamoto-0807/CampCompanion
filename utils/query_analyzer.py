"""
ユーザーの自然言語入力を解析し、検索意図を抽出するモジュール
"""

import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# Gemini APIの設定
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# デバッグモードの設定
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Gemini APIの初期化
try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"Gemini APIの初期化中にエラーが発生しました: {str(e)}")


def analyze_query(query):
    """
    ユーザーの自然言語入力を解析し、検索意図を抽出する関数

    Args:
        query (str): ユーザーの入力テキスト

    Returns:
        dict: 抽出された検索意図
            - structured_query (str): 構造化された検索クエリ
            - location (str): 場所要素
            - features (list): 特徴要素のリスト
            - facilities (list): 施設要素のリスト
            - priorities (dict): 優先度情報
    """
    if not GEMINI_API_KEY:
        # APIキーがない場合は基本的な解析のみ実行
        return basic_query_analysis(query)

    try:
        # Geminiモデルの設定
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-lite",
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 1024,
            },
        )

        # プロンプトの作成
        prompt = f"""
        あなたはキャンプ場検索の専門家です。以下のユーザーの入力から、キャンプ場検索に関する意図を抽出してください。

        ユーザー入力: {query}

        以下の情報を抽出し、JSON形式で返してください：

        1. 場所要素（地名、山、川、湖など）
        2. 特徴要素（景色、雰囲気、対象者など）
        3. 施設要素（設備、アメニティなど）
        4. 優先度（どの要素が最も重要か）
        5. 構造化された検索クエリ（検索エンジンに最適化されたクエリ）

        回答は以下のJSON形式で返してください：
        ```json
        {{
          "structured_query": "最適化された検索クエリ",
          "location": "場所要素",
          "features": ["特徴要素1", "特徴要素2", ...],
          "facilities": ["施設要素1", "施設要素2", ...],
          "priorities": {{
            "location": 0-10の数値,
            "features": 0-10の数値,
            "facilities": 0-10の数値
          }}
        }}
        ```
        """

        # Gemini APIを呼び出し
        response = model.generate_content(prompt)
        response_text = response.text

        # JSONデータを抽出
        json_start = response_text.find("```json") + 7 if "```json" in response_text else 0
        json_end = response_text.find("```", json_start) if "```" in response_text[json_start:] else len(response_text)

        if json_start > 0 and json_end > json_start:
            json_text = response_text[json_start:json_end].strip()
        else:
            json_text = response_text

        # JSONデータをパース
        try:
            analysis_result = json.loads(json_text)
            # 戻り値が辞書型であることを確認
            if not isinstance(analysis_result, dict):
                if DEBUG:
                    print(f"解析結果が辞書型ではありません: {type(analysis_result)}")
                if isinstance(analysis_result, list) and analysis_result:
                    # リストの場合は最初の要素を使用（辞書型であれば）
                    if isinstance(analysis_result[0], dict):
                        analysis_result = analysis_result[0]
                    else:
                        # 辞書型に変換
                        analysis_result = basic_query_analysis(query)
                else:
                    # 辞書型に変換
                    analysis_result = basic_query_analysis(query)
            return analysis_result
        except json.JSONDecodeError:
            if DEBUG:
                print(f"JSON解析エラー: {json_text}")
            return basic_query_analysis(query)

    except Exception as e:
        if DEBUG:
            print(f"クエリ解析エラー: {str(e)}")
        return basic_query_analysis(query)


def basic_query_analysis(query):
    """
    基本的なクエリ解析を行う関数（APIが利用できない場合のフォールバック）

    Args:
        query (str): ユーザーの入力テキスト

    Returns:
        dict: 基本的な検索意図
    """
    # 場所キーワードのリスト
    location_keywords = [
        "北海道",
        "青森",
        "岩手",
        "宮城",
        "秋田",
        "山形",
        "福島",
        "茨城",
        "栃木",
        "群馬",
        "埼玉",
        "千葉",
        "東京",
        "神奈川",
        "新潟",
        "富山",
        "石川",
        "福井",
        "山梨",
        "長野",
        "岐阜",
        "静岡",
        "愛知",
        "三重",
        "滋賀",
        "京都",
        "大阪",
        "兵庫",
        "奈良",
        "和歌山",
        "鳥取",
        "島根",
        "岡山",
        "広島",
        "山口",
        "徳島",
        "香川",
        "愛媛",
        "高知",
        "福岡",
        "佐賀",
        "長崎",
        "熊本",
        "大分",
        "宮崎",
        "鹿児島",
        "沖縄",
        "富士山",
        "八ヶ岳",
        "日本アルプス",
        "尾瀬",
        "軽井沢",
    ]

    # 特徴キーワードのリスト
    feature_keywords = [
        "景色",
        "眺め",
        "見える",
        "静か",
        "人気",
        "穴場",
        "子供",
        "ファミリー",
        "カップル",
        "初心者",
        "ソロ",
        "ソロキャンプ",
        "グループ",
        "川遊び",
        "海",
        "山",
        "湖",
        "森",
    ]

    # 施設キーワードのリスト
    facility_keywords = [
        "トイレ",
        "シャワー",
        "温泉",
        "風呂",
        "電源",
        "Wi-Fi",
        "炊事場",
        "売店",
        "ドッグラン",
        "遊具",
        "バーベキュー",
    ]

    # 抽出結果
    location = ""
    features = []
    facilities = []

    # 場所の抽出
    for keyword in location_keywords:
        if keyword in query:
            location = keyword
            break

    # 特徴の抽出
    for keyword in feature_keywords:
        if keyword in query:
            features.append(keyword)

    # 施設の抽出
    for keyword in facility_keywords:
        if keyword in query:
            facilities.append(keyword)

    # 構造化クエリの作成
    structured_query = query
    if "キャンプ場" not in query:
        structured_query += " キャンプ場"

    # 優先度の設定（基本的な実装）
    priorities = {
        "location": 5 if location else 0,
        "features": 5 if features else 0,
        "facilities": 5 if facilities else 0,
    }

    return {
        "structured_query": structured_query,
        "location": location,
        "features": features,
        "facilities": facilities,
        "priorities": priorities,
    }
