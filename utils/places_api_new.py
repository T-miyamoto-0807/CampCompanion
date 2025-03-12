import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime
import functools
import time

# 環境変数の読み込み
load_dotenv()

# デバッグモードの設定
DEBUG = True  # デバッグモードを強制的に有効化

# Google Places APIの設定
GOOGLE_PLACE_API_KEY = os.getenv("GOOGLE_PLACE_API_KEY")

# APIキーが設定されていない場合の警告
if not GOOGLE_PLACE_API_KEY:
    print("警告: GOOGLE_PLACE_API_KEYが設定されていません。.envファイルまたはStreamlit Secretsを確認してください。")

# 写真URLのキャッシュ
photo_cache = {}


# 写真取得関数をキャッシュ化
@functools.lru_cache(maxsize=128)
def get_place_photo_new(photo_name):
    """
    写真名から写真URLを取得する関数（新しいPlaces API用）
    """
    # キャッシュにある場合はキャッシュから返す
    if photo_name in photo_cache:
        return photo_cache[photo_name]

    try:
        # APIキーを取得
        api_key = os.getenv("GOOGLE_PLACE_API_KEY")
        if not api_key:
            print("[Places API] APIキーが設定されていません")
            return None

        # 写真名からURLを取得
        if DEBUG:
            print(f"[Places API] 写真URL取得: {photo_name}")

        # 新しいPhoto APIを使用
        base_url = f"https://places.googleapis.com/v1/{photo_name}/media"
        headers = {"X-Goog-Api-Key": api_key}

        if DEBUG:
            print(f"[Places API] 新しいPhoto APIを使用: {base_url[:40]}...")
            print(f"[Places API] ヘッダー: {headers}")

        # 直接URLを返す（リダイレクトを含む）
        # 写真URLを生成する際に、maxHeightPxとmaxWidthPxを指定して、適切なサイズの画像を取得
        photo_url = f"{base_url}?key={api_key}&maxHeightPx=800&maxWidthPx=800"

        if DEBUG:
            print(f"[Places API] 写真URL生成: {photo_url[:50]}...")

        # 実際にリクエストを送信して、リダイレクト先のURLを取得
        try:
            response = requests.head(photo_url, allow_redirects=True)
            if response.status_code == 200:
                final_url = response.url
                # キャッシュに保存
                photo_cache[photo_name] = final_url
                return final_url
            else:
                if DEBUG:
                    print(f"[Places API] 写真URL取得エラー: ステータスコード {response.status_code}")
                return photo_url  # エラーの場合でも元のURLを返す
        except Exception as redirect_error:
            if DEBUG:
                print(f"[Places API] リダイレクト取得エラー: {str(redirect_error)}")
            # エラーが発生した場合は元のURLを返す
            photo_cache[photo_name] = photo_url
            return photo_url

    except Exception as e:
        if DEBUG:
            print(f"[Places API] 写真取得エラー: {str(e)}")
        return None


# 複数の写真を取得する関数
@functools.lru_cache(maxsize=32)
def get_place_photos_new(place_id, max_photos=6):
    """
    場所IDから複数の写真URLを取得する関数（新しいPlaces API用）
    """
    # キャッシュキー
    cache_key = f"photos_{place_id}"
    if cache_key in photo_cache:
        return photo_cache[cache_key]

    try:
        # 詳細情報を取得
        details = get_place_details_new(place_id)
        if not details or "photos" not in details:
            return []

        # 写真名のリストを取得
        photo_names = details.get("photos", [])
        if not photo_names:
            return []

        # 写真URLのリストを取得
        photo_urls = []
        for photo_name in photo_names[:max_photos]:
            photo_url = get_place_photo_new(photo_name)
            if photo_url:
                photo_urls.append(photo_url)

        # キャッシュに保存
        photo_cache[cache_key] = photo_urls

        return photo_urls

    except Exception as e:
        if DEBUG:
            print(f"[Places API] 複数写真取得エラー: {str(e)}")
        return []


def search_campsites_new(query, location=None, radius=50000):
    """
    Places API (New)を使用してキャンプ場を検索する関数

    Args:
        query (str): 検索クエリ
        location (dict, optional): 位置情報（緯度・経度）
        radius (int, optional): 検索半径（メートル）

    Returns:
        dict: 検索結果
    """
    if DEBUG:
        print(f"\n===== search_campsites_new =====")
        print(f"検索クエリ: '{query}'")
        print(f"location: {location}, radius: {radius}")
        print(f"GOOGLE_PLACE_API_KEY: {'設定済み' if GOOGLE_PLACE_API_KEY else '未設定'}")
        print(f"GOOGLE_PLACE_API_KEY長さ: {len(GOOGLE_PLACE_API_KEY) if GOOGLE_PLACE_API_KEY else 0}")

    # APIキーが設定されていない場合はエラー
    if not GOOGLE_PLACE_API_KEY:
        error_msg = "APIキーが設定されていません。StreamlitCloudのSecretsまたは.envファイルを確認してください。"
        if DEBUG:
            print(f"[Places API] エラー: {error_msg}")
        return {"error": error_msg}

    try:
        # ベースURL
        base_url = "https://places.googleapis.com/v1/places:searchText"

        # ヘッダー
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": GOOGLE_PLACE_API_KEY,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.shortFormattedAddress,places.location,places.rating,places.userRatingCount,places.types,places.primaryType,places.photos,places.id,places.businessStatus,places.priceLevel,places.internationalPhoneNumber,places.websiteUri",
        }

        # リクエストボディ
        body = {
            "textQuery": f"{query} キャンプ場",  # 「キャンプ場」を明示的に追加
            "languageCode": "ja",
            "regionCode": "JP",
            "maxResultCount": 20,
        }

        # 位置情報が指定されている場合は追加
        if location and "lat" in location and "lng" in location:
            body["locationBias"] = {
                "circle": {
                    "center": {
                        "latitude": location["lat"],
                        "longitude": location["lng"],
                    },
                    "radius": radius,
                }
            }

        if DEBUG:
            print(f"[Places API] APIリクエスト: {base_url}")
            print(f"[Places API] リクエストヘッダー: {headers}")
            print(f"[Places API] リクエストボディ: {json.dumps(body, ensure_ascii=False)}")

        # APIリクエスト
        response = requests.post(base_url, headers=headers, json=body)

        # レスポンスのステータスコードを確認
        if DEBUG:
            print(f"[Places API] レスポンスステータス: {response.status_code}")
            print(f"[Places API] レスポンスヘッダー: {dict(response.headers)}")
            try:
                print(f"[Places API] レスポンス内容: {json.dumps(response.json(), ensure_ascii=False)[:500]}...")
            except:
                print(f"[Places API] レスポンス内容: {response.text[:500]}...")

        if response.status_code != 200:
            error_message = f"API Error: {response.status_code}"
            if DEBUG:
                print(f"[Places API] エラー: {response.status_code} - {response.text}")

            # 503エラー（サービス一時停止）の場合
            if response.status_code == 503:
                return {
                    "error": "Google Places APIが一時的に利用できません。しばらく時間をおいてから再度お試しください。",
                    "status_code": 503,
                }

            # 401エラー（認証エラー）の場合
            if response.status_code == 401:
                return {
                    "error": "Google Places APIの認証に失敗しました。APIキーを確認してください。",
                    "status_code": 401,
                }

            # 403エラー（権限エラー）の場合
            if response.status_code == 403:
                return {
                    "error": "Google Places APIへのアクセス権限がありません。APIキーの権限設定を確認してください。",
                    "status_code": 403,
                }

            # その他のエラー
            return {"error": error_message, "response_text": response.text[:500]}

        # JSONレスポンスを解析
        data = response.json()

        # 検索結果がない場合
        if "places" not in data or not data["places"]:
            if DEBUG:
                print("[Places API] 検索結果: 0件")
            return {"places": []}

        if DEBUG:
            print(f"[Places API] 検索結果: {len(data.get('places', []))}件")

        return data

    except Exception as e:
        if DEBUG:
            print(f"[Places API] 例外発生: {str(e)}")
            import traceback

            print(traceback.format_exc())
        return {"error": str(e)}


def get_place_details_new(place_id):
    """
    Places API (New)を使用して特定の場所の詳細情報を取得する

    Args:
        place_id (str): 場所のID

    Returns:
        dict: 場所の詳細情報
    """
    try:
        api_key = os.getenv("GOOGLE_PLACE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_PLACE_API_KEYが設定されていません")

        # ベースURL
        base_url = f"https://places.googleapis.com/v1/places/{place_id}"

        # リクエストヘッダー
        headers = {
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "id,displayName,formattedAddress,shortFormattedAddress,location,types,nationalPhoneNumber,internationalPhoneNumber,rating,userRatingCount,googleMapsUri,websiteUri,regularOpeningHours,priceLevel,photos,reviews.rating,reviews.text,reviews.publishTime,reviews.authorAttribution,businessStatus,editorialSummary,paymentOptions,accessibilityOptions,parkingOptions",
            "X-Goog-LanguageCode": "ja",  # 言語を日本語に設定
        }

        # クエリパラメータ
        params = {"languageCode": "ja", "regionCode": "JP"}  # 言語コードを追加  # 地域コードを追加

        if DEBUG:
            print(f"[Places API] 詳細情報取得リクエスト: {place_id}")
            print(f"[Places API] ヘッダー: {headers}")

        # APIリクエスト
        response = requests.get(base_url, headers=headers, params=params)

        # レスポンスのステータスコードを確認
        if response.status_code != 200:
            print(f"API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return {"error": f"API Error: {response.status_code}"}

        # JSONレスポンスを解析
        data = response.json()

        # デバッグ: レスポンスの構造を確認
        if DEBUG:
            print(f"[Places API] 詳細情報取得成功: {place_id}")
            if "photos" in data:
                print(f"[Places API] 写真情報: {len(data['photos'])}枚")
                # 写真情報の構造を確認
                if len(data["photos"]) > 0:
                    print(f"[Places API] 写真1の情報: {data['photos'][0].keys()}")
            else:
                print(f"[Places API] 写真情報なし")
                print(f"[Places API] 詳細情報のキー: {data.keys()}")

        return data

    except Exception as e:
        print(f"Error in get_place_details_new: {str(e)}")
        return {"error": str(e)}


def get_nearby_campsites_new(latitude, longitude, radius=50000, keyword="キャンプ場"):
    """
    Places API (New)を使用して指定された位置の近くのキャンプ場を検索する

    Args:
        latitude (float): 緯度
        longitude (float): 経度
        radius (int, optional): 検索半径（メートル）
        keyword (str, optional): 検索キーワード

    Returns:
        dict: 検索結果
    """
    try:
        api_key = os.getenv("GOOGLE_PLACE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_PLACE_API_KEYが設定されていません")

        # ベースURL
        base_url = "https://places.googleapis.com/v1/places:searchNearby"

        # リクエストヘッダー
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.shortFormattedAddress,places.location,places.rating,places.userRatingCount,places.types,places.primaryType,places.primaryTypeDisplayName,places.id,places.photos",
            "X-Goog-LanguageCode": "ja",  # 言語を日本語に設定
        }

        # リクエストボディ
        request_body = {
            "languageCode": "ja",  # 言語コードを追加
            "regionCode": "JP",  # 地域コードを追加
            "locationRestriction": {
                "circle": {"center": {"latitude": latitude, "longitude": longitude}, "radius": radius}
            },
            "includedTypes": ["campground"],  # キャンプ場のみに絞り込む
            "maxResultCount": 20,
        }

        # キーワードが指定されている場合は追加
        if keyword:
            request_body["textQuery"] = keyword

        # APIリクエスト
        response = requests.post(base_url, headers=headers, json=request_body)

        # レスポンスのステータスコードを確認
        if response.status_code != 200:
            return {"error": f"API Error: {response.status_code}", "places": []}

        # JSONレスポンスを解析
        data = response.json()

        # 結果がない場合
        if "places" not in data:
            return {"places": []}

        return data

    except Exception as e:
        return {"error": str(e), "places": []}


def convert_places_to_app_format_new(places_data):
    """
    Places API (New)の検索結果をアプリケーションのフォーマットに変換する

    Args:
        places_data (dict): Places APIの検索結果

    Returns:
        list: アプリケーションのフォーマットに変換されたキャンプ場データのリスト
    """
    if DEBUG:
        print(f"\n===== convert_places_to_app_format_new =====")

    # エラーチェック
    if not places_data or isinstance(places_data, str) or "error" in places_data:
        if DEBUG:
            print(f"[Places API] データ変換エラー: {places_data}")
        return []

    # places_dataが辞書型でない場合はエラー
    if not isinstance(places_data, dict):
        if DEBUG:
            print(f"[Places API] データ型エラー: {type(places_data)}")
        return []

    # 検索結果がない場合は空のリストを返す
    if "places" not in places_data or not places_data["places"]:
        if DEBUG:
            print(f"[Places API] 検索結果なし")
        return []

    # 検索結果を変換
    campsites = []
    for place in places_data["places"]:
        try:
            # 基本情報を取得
            place_id = place.get("id", "")
            name = place.get("displayName", {}).get("text", "")

            # 名前がない場合はスキップ
            if not name:
                continue

            # 詳細情報を取得
            details = get_place_details_new(place_id)

            # 詳細情報がない場合は基本情報のみで作成
            if not details:
                if DEBUG:
                    print(f"[Places API] 詳細情報なし: {name}")

                # 基本情報のみで作成
                campsite = {
                    "place_id": place_id,
                    "name": name,
                    "rating": place.get("rating", 0),
                    "reviews_count": place.get("userRatingCount", 0),
                    "address": place.get("formattedAddress", ""),
                    "location": place.get("location", {}),
                    "photos": [],
                    "photo_urls": [],
                    "image_url": "",
                    "facilities": [],
                    "features": [],
                    "description": "",
                    "website": "",
                    "phone": "",
                    "price_level": place.get("priceLevel", ""),
                    "business_status": place.get("businessStatus", ""),
                    "source": "places_api_new",
                }

                campsites.append(campsite)
                continue

            # 詳細情報から施設と特徴を抽出
            facilities = []
            features = []

            # 施設情報を抽出
            if "amenities" in details:
                for amenity in details["amenities"]:
                    facilities.append(amenity)

            # 特徴情報を抽出
            if "aboutThisPlace" in details and "highlights" in details["aboutThisPlace"]:
                for highlight in details["aboutThisPlace"]["highlights"]:
                    features.append(highlight)

            # 説明文を抽出
            description = ""
            if "aboutThisPlace" in details and "summary" in details["aboutThisPlace"]:
                description = details["aboutThisPlace"]["summary"]

            # 写真情報を抽出（写真名だけを保存）
            photos = []
            if "photos" in details:
                for photo in details["photos"][:6]:  # 最大6枚まで取得
                    photo_name = photo.get("name")
                    if photo_name:
                        photos.append(photo_name)

                if DEBUG:
                    print(f"[Places API] 写真名を{len(photos)}枚取得: {place_id}")

            # キャンプ場情報を作成
            campsite = {
                "place_id": place_id,
                "name": name,
                "rating": details.get("rating", place.get("rating", 0)),
                "reviews_count": details.get("userRatingCount", place.get("userRatingCount", 0)),
                "address": details.get("formattedAddress", place.get("formattedAddress", "")),
                "location": details.get("location", place.get("location", {})),
                "photos": photos,
                "photo_urls": [],  # 写真URLは後で取得
                "image_url": "",  # 画像URLは後で設定
                "facilities": facilities,
                "features": features,
                "description": description,
                "website": details.get("websiteUri", ""),
                "phone": details.get("internationalPhoneNumber", ""),
                "price_level": details.get("priceLevel", place.get("priceLevel", "")),
                "business_status": details.get("businessStatus", place.get("businessStatus", "")),
                "source": "places_api_new",
            }

            # 口コミデータを追加
            if "reviews" in details:
                reviews = []
                for review in details["reviews"]:
                    review_data = {
                        "rating": review.get("rating", 0),
                        "text": review.get("text", {}).get("text", ""),
                        "time": review.get("publishTime", ""),
                        "author": review.get("authorAttribution", {}).get("displayName", ""),
                    }
                    reviews.append(review_data)
                campsite["reviews"] = reviews
            else:
                campsite["reviews"] = []

            campsites.append(campsite)

        except Exception as e:
            if DEBUG:
                print(f"[Places API] データ変換エラー: {str(e)}")
                import traceback

                print(traceback.format_exc())
            continue

    if DEBUG:
        print(f"[Places API] 変換結果: {len(campsites)}件")

    return campsites


def extract_payment_options(payment_options):
    """
    支払いオプションを抽出する関数

    Args:
        payment_options (dict): 支払いオプション情報

    Returns:
        list: 支払いオプションのリスト
    """
    options = []

    if payment_options.get("acceptsCreditCards", False):
        options.append("credit_card")

    if payment_options.get("acceptsDebitCards", False):
        options.append("debit_card")

    if payment_options.get("acceptsCashOnly", False):
        options.append("cash_only")

    if payment_options.get("acceptsNfc", False):
        options.append("nfc")

    return options


def extract_parking_options(parking_options):
    """
    駐車場オプションを抽出する関数

    Args:
        parking_options (dict): 駐車場オプション情報

    Returns:
        list: 駐車場オプションのリスト
    """
    options = []

    if parking_options.get("freeParking", False):
        options.append("free_parking")

    if parking_options.get("paidParking", False):
        options.append("paid_parking")

    if parking_options.get("freeStreetParking", False):
        options.append("free_street_parking")

    if parking_options.get("valetParking", False):
        options.append("valet_parking")

    if parking_options.get("freeGarageParking", False):
        options.append("free_garage_parking")

    if parking_options.get("paidGarageParking", False):
        options.append("paid_garage_parking")

    return options


def format_opening_hours(opening_hours):
    """
    営業時間情報をフォーマットする関数

    Args:
        opening_hours (dict): 営業時間情報

    Returns:
        dict: フォーマットされた営業時間情報
    """
    if not opening_hours:
        return {}

    formatted_hours = {}

    # 営業時間のテキスト
    if "weekdayDescriptions" in opening_hours:
        formatted_hours["text"] = opening_hours["weekdayDescriptions"]

    # 営業中かどうか
    if "openNow" in opening_hours:
        formatted_hours["open_now"] = opening_hours["openNow"]

    # 各曜日の営業時間
    if "periods" in opening_hours:
        formatted_hours["periods"] = opening_hours["periods"]

    return formatted_hours


def format_reviews(reviews):
    """
    レビュー情報をフォーマットする関数

    Args:
        reviews (list): レビュー情報のリスト

    Returns:
        list: フォーマットされたレビュー情報のリスト
    """
    if not reviews:
        return []

    formatted_reviews = []

    for review in reviews:
        # 投稿日時を日本語フォーマットに変換
        publish_time = review.get("publishTime", "")
        formatted_time = ""
        if publish_time:
            try:
                from datetime import datetime

                dt = datetime.fromisoformat(publish_time.replace("Z", "+00:00"))
                formatted_time = dt.strftime("%Y年%m月%d日")
            except Exception as e:
                formatted_time = publish_time

        # レビュー情報を整形
        formatted = {
            "name": review.get("authorAttribution", {}).get("displayName", "匿名ユーザー"),
            "photo_url": review.get("authorAttribution", {}).get("photoUri", ""),
            "rating": review.get("rating", 0),
            "text": review.get("text", {}).get("text", "レビューなし"),
            "time": formatted_time,
        }
        formatted_reviews.append(formatted)

    return formatted_reviews
