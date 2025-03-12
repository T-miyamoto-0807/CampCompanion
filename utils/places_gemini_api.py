import os
import json
import requests
from dotenv import load_dotenv
from utils.places_api_new import search_campsites_new, get_place_details_new, convert_places_to_app_format_new
from utils.gemini_api import search_campsites_gemini

# 環境変数の読み込み
load_dotenv()

# デバッグモードの設定
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# APIキーの取得
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_PLACE_API_KEY = os.getenv("GOOGLE_PLACE_API_KEY")

# APIキーが設定されていない場合のエラーメッセージ
if not GOOGLE_PLACE_API_KEY:
    print("警告: GOOGLE_PLACE_API_KEYが設定されていません。.envファイルに追加してください。")


def search_campsites_places_gemini(query):
    """
    Places APIとGemini APIを組み合わせてキャンプ場を検索する関数

    Args:
        query (str): 検索クエリ

    Returns:
        list: キャンプ場データのリスト
    """
    try:
        # まずPlaces APIで検索
        places_data = search_campsites_new(query)

        # Places APIの結果をアプリケーションのフォーマットに変換
        places_results = convert_places_to_app_format_new(places_data)

        # Places APIの結果が少ない場合はGemini APIで補完
        if len(places_results) < 3:
            # Gemini APIで検索
            gemini_results = search_campsites_gemini(query)

            # 重複を避けるために既存の結果のキャンプ場名をリストアップ
            existing_names = [site.get("name", "").lower() for site in places_results]

            # 重複しないGemini APIの結果を追加
            for site in gemini_results:
                if site.get("name", "").lower() not in existing_names:
                    places_results.append(site)
                    existing_names.append(site.get("name", "").lower())

                    # 最大10件まで
                    if len(places_results) >= 10:
                        break

        # 検索結果を評価順にソート
        places_results = sorted(places_results, key=lambda x: x.get("rating", 0), reverse=True)

        # Gemini APIを使用して検索結果を強化
        if places_results and GEMINI_API_KEY:
            enhance_search_results_with_gemini(places_results, query)

        return places_results

    except Exception as e:
        print(f"Error in search_campsites_places_gemini: {str(e)}")

        # エラーが発生した場合はGemini APIのみで検索
        try:
            return search_campsites_gemini(query)
        except Exception as gemini_error:
            print(f"Error in Gemini fallback: {str(gemini_error)}")
            return []


def enhance_search_results_with_gemini(campsites, query):
    """
    Gemini APIを使用して検索結果を強化する関数

    Args:
        campsites (list): キャンプ場データのリスト
        query (str): 検索クエリ

    Returns:
        None: 引数のcampsitesリストを直接更新
    """
    if not GEMINI_API_KEY:
        return

    # Gemini APIのエンドポイント
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key={GEMINI_API_KEY}"

    # 最初の3つのキャンプ場のみ強化
    for i, campsite in enumerate(campsites[:3]):
        # プロンプトの作成
        prompt = f"""
        あなたは日本のキャンプ場に関する専門家です。以下のキャンプ場について、ユーザーの検索条件に基づいて詳細な情報を提供してください。

        キャンプ場名: {campsite.get('name', '不明')}
        住所: {campsite.get('address', '不明')}
        
        ユーザーの検索条件: {query}
        
        以下の情報を日本語で提供してください：
        1. このキャンプ場の特徴や魅力（200文字程度）
        2. おすすめのアクティビティ（5つまで）
        3. 周辺の観光スポット（3つまで）
        4. ベストシーズン
        
        回答は以下のJSON形式で返してください：
        ```json
        {{
          "description": "キャンプ場の特徴や魅力の説明",
          "activities": ["アクティビティ1", "アクティビティ2"],
          "nearby_spots": ["観光スポット1", "観光スポット2"],
          "best_season": "ベストシーズンの説明"
        }}
        ```
        """

        # リクエストヘッダー
        headers = {"Content-Type": "application/json"}

        # リクエストボディ
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "topP": 0.8, "topK": 40, "maxOutputTokens": 2048},
        }

        try:
            # APIリクエスト
            response = requests.post(url, headers=headers, json=data)

            # レスポンスのステータスコードを確認
            if response.status_code != 200:
                continue

            # JSONレスポンスを解析
            response_data = response.json()

            # テキスト応答を抽出
            text = response_data["candidates"][0]["content"]["parts"][0]["text"]

            # JSONデータを抽出
            json_start = text.find("```json") + 7
            json_end = text.find("```", json_start)

            if json_start == -1 or json_end == -1:
                # JSON形式でない場合は、テキスト全体を解析
                json_text = text
            else:
                json_text = text[json_start:json_end].strip()

            # JSONデータをパース
            enhanced_data = json.loads(json_text)

            # キャンプ場データを強化
            if "description" in enhanced_data and not campsite.get("description"):
                campsite["description"] = enhanced_data["description"]

            if "activities" in enhanced_data:
                campsite["activities"] = enhanced_data["activities"]

            if "nearby_spots" in enhanced_data:
                campsite["nearby_spots"] = enhanced_data["nearby_spots"]

            if "best_season" in enhanced_data:
                campsite["best_season"] = enhanced_data["best_season"]

        except Exception as e:
            print(f"Error enhancing campsite {campsite.get('name', 'unknown')}: {str(e)}")
            continue


def get_price_level_text(price_level):
    """
    価格レベルを日本語のテキストに変換する関数

    Args:
        price_level (str): 価格レベル

    Returns:
        str: 価格レベルのテキスト
    """
    price_map = {
        "PRICE_LEVEL_FREE": "無料",
        "PRICE_LEVEL_INEXPENSIVE": "1,000円〜3,000円",
        "PRICE_LEVEL_MODERATE": "3,000円〜6,000円",
        "PRICE_LEVEL_EXPENSIVE": "6,000円〜10,000円",
        "PRICE_LEVEL_VERY_EXPENSIVE": "10,000円〜",
    }

    return price_map.get(price_level, "料金情報なし")


def extract_features_from_description(description):
    """
    説明文から特徴を抽出する関数

    Args:
        description (str): 説明文

    Returns:
        list: 特徴のリスト
    """
    # キャンプ場の一般的な特徴キーワード
    feature_keywords = [
        "オートキャンプ",
        "グランピング",
        "コテージ",
        "バンガロー",
        "テントサイト",
        "フリーサイト",
        "区画サイト",
        "温泉",
        "露天風呂",
        "シャワー",
        "トイレ",
        "電源",
        "Wi-Fi",
        "ペット",
        "釣り",
        "川遊び",
        "海水浴",
        "BBQ",
        "バーベキュー",
        "焚き火",
        "薪",
        "売店",
        "レストラン",
        "カフェ",
        "遊具",
        "アスレチック",
        "富士山",
        "山",
        "湖",
        "海",
        "川",
        "森",
        "高規格",
        "手ぶら",
        "初心者向け",
        "ファミリー",
    ]

    # 説明文から特徴を抽出
    features = []
    for keyword in feature_keywords:
        if keyword.lower() in description.lower():
            features.append(keyword)

    # 最大5つまでの特徴を返す
    return features[:5]


def get_place_photo(photo_reference, max_width=800):
    """
    Google Places APIを使用して場所の写真を取得するURLを生成する関数

    Args:
        photo_reference (str): 写真の参照ID
        max_width (int, optional): 写真の最大幅

    Returns:
        str: 写真のURL
    """
    if not GOOGLE_PLACE_API_KEY or not photo_reference:
        return None

    return f"https://places.googleapis.com/v1/{photo_reference}/media?maxWidthPx={max_width}&key={GOOGLE_PLACE_API_KEY}"
