import os
import json
import requests
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# デバッグモードの設定
DEBUG = True

# Google Places APIの設定
GOOGLE_PLACE_API_KEY = os.getenv("GOOGLE_PLACE_API_KEY")

# APIキーが設定されていない場合のエラーメッセージ
if not GOOGLE_PLACE_API_KEY:
    print("警告: GOOGLE_PLACE_API_KEYが設定されていません。.envファイルに追加してください。")

# Places API（新版）のユーティリティをインポート
from utils.places_api_new import (
    search_campsites_new,
    get_place_details_new,
    get_place_photo_new,
    get_nearby_campsites_new,
    convert_places_to_app_format_new,
)


def test_text_search():
    """
    Text Search（新版）APIをテストする関数
    """
    print("\n===== Text Search（新版）APIのテスト =====")
    try:
        # キャンプ場を検索
        query = "関東 キャンプ場 アクセスが良い"
        print(f"検索クエリ: {query}")

        results = search_campsites_new(query)

        print(f"検索結果: {len(results)}件のキャンプ場が見つかりました")

        # 最初の3件の結果を表示
        for i, campsite in enumerate(results[:3]):
            print(f"\n--- 結果 {i+1}: {campsite['name']} ---")
            print(f"住所: {campsite['address']}")
            print(f"短縮住所: {campsite['short_address']}")
            print(f"評価: {campsite['rating']} ({campsite['user_ratings_total']}件の評価)")
            print(f"タイプ: {campsite['primary_type_display_name']}")

            # アメニティ情報
            if campsite.get("amenities"):
                print("アメニティ:")
                for key, value in campsite["amenities"].items():
                    if value:
                        print(f"  - {key}: {value}")

            # アクセシビリティ情報
            if campsite.get("accessibility"):
                print("アクセシビリティ:")
                for key, value in campsite["accessibility"].items():
                    if value:
                        print(f"  - {key}: {value}")

            # 駐車場情報
            if campsite.get("parking_options"):
                print(f"駐車場オプション: {', '.join(campsite['parking_options'])}")

            # 支払い方法
            if campsite.get("payment_options"):
                print(f"支払い方法: {', '.join(campsite['payment_options'])}")

            # 写真情報
            if campsite.get("photos"):
                print(f"写真数: {len(campsite['photos'])}")
                if len(campsite["photos"]) > 0:
                    photo = campsite["photos"][0]
                    if "name" in photo:
                        print(f"写真名: {photo['name']}")

            print(f"Place ID: {campsite['place_id']}")

            # 詳細情報を取得するためのPlace IDを保存
            if i == 0:
                first_place_id = campsite["place_id"]

        return first_place_id

    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        return None


def test_place_details(place_id):
    """
    Place Details（新版）APIをテストする関数

    Args:
        place_id (str): 詳細情報を取得するPlace ID
    """
    print("\n===== Place Details（新版）APIのテスト =====")
    try:
        if not place_id:
            print("Place IDが指定されていません。")
            return

        print(f"Place ID: {place_id}")

        # 詳細情報を取得
        details = get_place_details_new(place_id)

        print(f"\n--- {details['name']}の詳細情報 ---")
        print(f"住所: {details['address']}")
        print(f"短縮住所: {details['short_address']}")
        print(f"評価: {details['rating']} ({details['user_ratings_total']}件の評価)")

        # 価格レベル
        if details.get("price_level"):
            print(f"価格レベル: {details['price_level']}")

        # ウェブサイト
        if details.get("website"):
            print(f"ウェブサイト: {details['website']}")

        # 電話番号
        if details.get("phone"):
            print(f"電話番号: {details['phone']}")

        # 営業時間
        if details.get("opening_hours") and details["opening_hours"].get("text"):
            print("営業時間:")
            for hour in details["opening_hours"]["text"]:
                print(f"  {hour}")

        # 副業時間
        if details.get("secondary_opening_hours"):
            print("副業時間:")
            for secondary in details["secondary_opening_hours"]:
                print(f"  タイプ: {secondary['type']}")
                if secondary["hours"].get("text"):
                    for hour in secondary["hours"]["text"]:
                        print(f"    {hour}")

        # アメニティ情報
        if details.get("amenities"):
            print("アメニティ:")
            for key, value in details["amenities"].items():
                if value:
                    print(f"  - {key}: {value}")

        # アクセシビリティ情報
        if details.get("accessibility"):
            print("アクセシビリティ:")
            for key, value in details["accessibility"].items():
                if value:
                    print(f"  - {key}: {value}")

        # 駐車場情報
        if details.get("parking_options"):
            print(f"駐車場オプション: {', '.join(details['parking_options'])}")

        # 支払い方法
        if details.get("payment_options"):
            print(f"支払い方法: {', '.join(details['payment_options'])}")

        # EV充電オプション
        if details.get("ev_charge_options"):
            print("EV充電オプション:")
            print(json.dumps(details["ev_charge_options"], ensure_ascii=False, indent=2))

        # レビュー
        if details.get("reviews"):
            print(f"\nレビュー ({len(details['reviews'])}件):")
            for i, review in enumerate(details["reviews"][:2]):  # 最初の2件のみ表示
                print(f"\nレビュー {i+1}:")
                print(f"投稿者: {review['name']}")
                print(f"評価: {review['rating']}")
                print(f"投稿日: {review['time']}")
                print(f"内容: {review['text'][:100]}...")  # 最初の100文字のみ表示

        # 写真
        if details.get("photos"):
            print(f"\n写真 ({len(details['photos'])}枚):")
            for i, photo in enumerate(details["photos"][:2]):  # 最初の2枚のみ表示
                if "name" in photo:
                    photo_url = get_place_photo_new(photo["name"])
                    print(f"写真 {i+1}: {photo_url[:100]}...")  # URLの最初の100文字のみ表示

        return details

    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        return None


def test_nearby_search():
    """
    Nearby Search（新版）APIをテストする関数
    """
    print("\n===== Nearby Search（新版）APIのテスト =====")
    try:
        # 東京の緯度経度
        latitude = 35.6895
        longitude = 139.6917
        radius = 50000  # 50km

        print(f"位置: 緯度={latitude}, 経度={longitude}, 半径={radius}m")

        # 近くのキャンプ場を検索
        results = get_nearby_campsites_new(latitude, longitude, radius)

        print(f"検索結果: {len(results)}件のキャンプ場が見つかりました")

        # 最初の3件の結果を表示
        for i, campsite in enumerate(results[:3]):
            print(f"\n--- 結果 {i+1}: {campsite['name']} ---")
            print(f"住所: {campsite['address']}")
            print(f"短縮住所: {campsite['short_address']}")
            print(f"評価: {campsite['rating']} ({campsite['user_ratings_total']}件の評価)")
            print(f"タイプ: {campsite['primary_type_display_name']}")

            # アメニティ情報
            if campsite.get("amenities"):
                print("アメニティ:")
                for key, value in campsite["amenities"].items():
                    if value:
                        print(f"  - {key}: {value}")

            # アクセシビリティ情報
            if campsite.get("accessibility"):
                print("アクセシビリティ:")
                for key, value in campsite["accessibility"].items():
                    if value:
                        print(f"  - {key}: {value}")

            print(f"Place ID: {campsite['place_id']}")

        return results

    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        return None


def test_convert_to_app_format():
    """
    Places API（新版）のデータをアプリケーションフォーマットに変換する機能をテストする関数
    """
    print("\n===== アプリケーションフォーマット変換のテスト =====")
    try:
        # キャンプ場を検索
        query = "関東 キャンプ場"
        results = search_campsites_new(query)

        if not results:
            print("検索結果がありません。")
            return

        # アプリケーションフォーマットに変換
        app_format_results = convert_places_to_app_format_new(results)

        print(f"変換結果: {len(app_format_results)}件のキャンプ場データが変換されました")

        # 最初の結果を表示
        if app_format_results:
            campsite = app_format_results[0]
            print(f"\n--- {campsite['name']}のアプリケーションフォーマット ---")
            print(f"住所: {campsite['address']}")
            print(f"短縮住所: {campsite['short_address']}")
            print(f"評価: {campsite['rating']}")
            print(f"料金: {campsite['price']}")

            if campsite.get("features"):
                print(f"特徴: {', '.join(campsite['features'])}")

            if campsite.get("amenities"):
                print(f"設備: {', '.join(campsite['amenities'])}")

            print(f"タイプ: {campsite['primary_type_display_name']}")

        return app_format_results

    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        return None


def main():
    """
    メイン関数
    """
    print("===== Places API（新版）機能テスト =====")

    # APIキーが設定されているか確認
    if not GOOGLE_PLACE_API_KEY:
        print("エラー: GOOGLE_PLACE_API_KEYが設定されていません。.envファイルに追加してください。")
        return

    # Text Search APIのテスト
    place_id = test_text_search()

    # Place Details APIのテスト
    if place_id:
        details = test_place_details(place_id)

    # Nearby Search APIのテスト
    nearby_results = test_nearby_search()

    # アプリケーションフォーマット変換のテスト
    app_format_results = test_convert_to_app_format()

    print("\n===== テスト完了 =====")


if __name__ == "__main__":
    main()
