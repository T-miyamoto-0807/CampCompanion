import os
from dotenv import load_dotenv
from utils.places_gemini_api import search_campsites_with_places_gemini

# 環境変数の読み込み
load_dotenv()

# デバッグモードを有効化
os.environ["DEBUG"] = "True"


def test_places_gemini_api():
    """Places Gemini APIをテストする関数"""
    print("Places Gemini APIのテストを開始します...")

    try:
        # テスト用のパラメータ
        query = "高規格"
        region = "関東"
        amenities = ["シャワー", "電源"]

        print(f"検索条件: キーワード={query}, 地域={region}, 設備={amenities}")

        # Places Gemini APIを使用してキャンプ場を検索
        results = search_campsites_with_places_gemini(query, region, amenities)

        # 結果の表示
        print(f"\n検索結果: {len(results)}件のキャンプ場が見つかりました\n")

        # 各キャンプ場の情報を表示
        for i, campsite in enumerate(results, 1):
            print(f"===== キャンプ場 {i} =====")
            print(f"名前: {campsite['name']}")
            print(f"住所: {campsite['address']}")
            print(f"料金: {campsite['price']}")
            print(
                f"特徴: {', '.join(campsite['features']) if isinstance(campsite['features'], list) else campsite['features']}"
            )
            print(
                f"説明: {campsite['description'][:100]}..."
                if len(campsite["description"]) > 100
                else campsite["description"]
            )
            print(f"予約方法: {campsite.get('reservation', '情報なし')}")
            print(f"緯度経度: {campsite.get('latitude', 0)}, {campsite.get('longitude', 0)}")
            print(
                f"設備: シャワー({'あり' if campsite.get('has_shower') else 'なし'}), "
                f"電源({'あり' if campsite.get('has_electricity') else 'なし'}), "
                f"ペット({'可' if campsite.get('pet_friendly') else '不可'}), "
                f"温泉({'あり' if campsite.get('has_hot_spring') else 'なし'}), "
                f"Wi-Fi({'あり' if campsite.get('has_wifi') else 'なし'})"
            )
            print()

        print("Places Gemini APIのテストが正常に完了しました。")
        return True

    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        return False


if __name__ == "__main__":
    test_places_gemini_api()
