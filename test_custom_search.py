"""
Google Custom Search APIのテストスクリプト
"""

import os
import json
import requests
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# APIキーの取得
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

print(f"GOOGLE_CSE_ID: {GOOGLE_CSE_ID}")
print(f"GOOGLE_API_KEY: {GOOGLE_API_KEY[:10]}...")  # セキュリティのため一部のみ表示


def test_custom_search_api():
    """
    Google Custom Search APIをテストする関数
    """
    if not GOOGLE_CSE_ID or not GOOGLE_API_KEY:
        print("エラー: Google Custom Search APIのキーが設定されていません。")
        return

    # テスト用のクエリ
    query = "富士山 キャンプ場"

    # Google Custom Search APIのエンドポイント
    url = "https://www.googleapis.com/customsearch/v1"

    # リクエストパラメータ
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query,
        "num": 3,  # テスト用に3件のみ取得
        "lr": "lang_ja",  # 日本語の結果のみ
        "gl": "jp",  # 日本のコンテンツを優先
    }

    try:
        # APIリクエスト
        print(f"リクエスト送信中: {url}?q={query}&cx={GOOGLE_CSE_ID}&...")
        response = requests.get(url, params=params)

        # レスポンスのステータスコードを確認
        print(f"ステータスコード: {response.status_code}")

        if response.status_code != 200:
            print(f"エラー: {response.status_code}")
            print(f"レスポンス: {response.text}")
            return

        # JSONレスポンスを解析
        data = response.json()

        # 検索情報を表示
        if "searchInformation" in data:
            search_info = data["searchInformation"]
            print(f"検索結果数: {search_info.get('totalResults', '不明')}")
            print(f"検索時間: {search_info.get('searchTime', '不明')} 秒")

        # 検索結果がない場合
        if "items" not in data:
            print("検索結果がありません。")
            return

        # 検索結果を表示
        print("\n検索結果:")
        for i, item in enumerate(data["items"]):
            print(f"\n{i+1}. {item.get('title', '不明')}")
            print(f"   URL: {item.get('link', '不明')}")
            print(f"   スニペット: {item.get('snippet', '不明')[:100]}...")

        print("\nテスト成功: Google Custom Search APIが正常に動作しています。")

    except Exception as e:
        print(f"エラー: {str(e)}")


if __name__ == "__main__":
    test_custom_search_api()
