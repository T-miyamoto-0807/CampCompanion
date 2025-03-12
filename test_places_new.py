import os
import json
from dotenv import load_dotenv
from utils.places_api_new import search_campsites_new, get_place_details_new, get_place_photo_new

# 環境変数の読み込み
load_dotenv()

# デバッグモードの設定
DEBUG = os.getenv("DEBUG", "True").lower() == "true"


def test_places_new_api():
    """
    Places API (New)のテスト関数
    """
    print("Places API (New)のテストを開始します...")

    # テストパラメータの設定
    query = "キャンプ場 関東"

    try:
        # キャンプ場の検索
        print(f"検索クエリ: {query}")
        results = search_campsites_new(query)

        print(f"検索結果数: {len(results)}")

        # 検索結果の表示
        for i, site in enumerate(results[:3]):  # 最初の3件のみ表示
            print(f"\n--- キャンプ場 {i+1} ---")
            print(f"名前: {site.get('name', '不明')}")
            print(f"住所: {site.get('address', '不明')}")
            print(f"評価: {site.get('rating', '不明')} ({site.get('user_ratings_total', 0)}件のレビュー)")
            print(f"場所ID: {site.get('place_id', '不明')}")

            # 詳細情報の取得
            if site.get("place_id"):
                try:
                    details = get_place_details_new(site["place_id"])

                    # 価格レベルの表示
                    price_level = details.get("priceLevel", "不明")
                    if price_level:
                        print(f"価格レベル: {price_level}")

                    # ウェブサイトの表示
                    website = details.get("websiteUri", "不明")
                    if website and website != "不明":
                        print(f"ウェブサイト: {website}")

                    # 電話番号の表示
                    phone = details.get("nationalPhoneNumber", "不明")
                    if phone and phone != "不明":
                        print(f"電話番号: {phone}")

                    # 営業時間の表示
                    if "regularOpeningHours" in details:
                        print("営業時間:")
                        for period in details["regularOpeningHours"].get("periods", []):
                            if "open" in period and "close" in period:
                                day_open = period["open"].get("day", "")
                                time_open = period["open"].get("hour", "") + ":" + period["open"].get("minute", "00")
                                day_close = period["close"].get("day", "")
                                time_close = period["close"].get("hour", "") + ":" + period["close"].get("minute", "00")
                                print(f"  {day_open}日 {time_open} - {day_close}日 {time_close}")

                    # 写真の表示
                    if "photos" in details:
                        photo = details["photos"][0]
                        photo_url = get_place_photo_new(photo["name"])
                        print(f"写真URL: {photo_url}")

                except Exception as e:
                    print(f"詳細情報の取得中にエラーが発生しました: {str(e)}")

            print("------------------------")

        print("\nPlaces API (New)のテストが完了しました。")

    except Exception as e:
        print(f"テスト中にエラーが発生しました: {str(e)}")


if __name__ == "__main__":
    test_places_new_api()
