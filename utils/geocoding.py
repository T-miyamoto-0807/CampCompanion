import os
import requests
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# Google Maps APIキーの取得
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# デバッグモード
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")


def get_location_coordinates(place_name):
    """
    場所の名前から緯度経度を取得する関数

    Args:
        place_name (str): 場所の名前

    Returns:
        dict: 緯度経度情報 (latitude, longitude)
    """
    if DEBUG:
        print(f"[Geocoding] 位置情報取得: {place_name}")

    # APIキーが設定されていない場合はエラー
    if not GOOGLE_MAPS_API_KEY:
        if DEBUG:
            print("[Geocoding] APIキーが設定されていません")
        # デフォルトの位置情報（東京）を返す
        return {"latitude": 35.6812, "longitude": 139.7671}

    try:
        # Google Maps Geocoding APIのURL
        url = "https://maps.googleapis.com/maps/api/geocode/json"

        # リクエストパラメータ
        params = {"address": place_name, "key": GOOGLE_MAPS_API_KEY, "language": "ja", "region": "jp"}

        # APIリクエスト
        response = requests.get(url, params=params)

        # レスポンスのステータスコードを確認
        if response.status_code != 200:
            if DEBUG:
                print(f"[Geocoding] API Error: {response.status_code}")
                print(f"[Geocoding] Response: {response.text}")
            # デフォルトの位置情報（東京）を返す
            return {"latitude": 35.6812, "longitude": 139.7671}

        # JSONレスポンスを解析
        data = response.json()

        # 結果がない場合はデフォルト値を返す
        if data["status"] != "OK" or not data["results"]:
            if DEBUG:
                print(f"[Geocoding] 結果なし: {data['status']}")
            # デフォルトの位置情報（東京）を返す
            return {"latitude": 35.6812, "longitude": 139.7671}

        # 緯度経度を取得
        location = data["results"][0]["geometry"]["location"]

        # 緯度経度を返す
        return {"latitude": location["lat"], "longitude": location["lng"]}

    except Exception as e:
        if DEBUG:
            print(f"[Geocoding] エラー: {str(e)}")
        # デフォルトの位置情報（東京）を返す
        return {"latitude": 35.6812, "longitude": 139.7671}
