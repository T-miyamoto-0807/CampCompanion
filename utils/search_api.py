import os
import requests
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# Google Custom Search APIの設定
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

# APIキーが設定されていない場合のエラーメッセージ
if not GOOGLE_API_KEY:
    print("警告: GOOGLE_API_KEYが設定されていません。.envファイルに追加してください。")

if not GOOGLE_CSE_ID:
    print("警告: GOOGLE_CSE_IDが設定されていません。.envファイルに追加してください。")


def search_campsite_info(query, num_results=5):
    """
    Google Custom Search APIを使用してキャンプ場に関する情報を検索する関数

    Args:
        query (str): 検索クエリ（例: 'キャンプ場名 公式サイト'）
        num_results (int, optional): 取得する結果の数

    Returns:
        list: 検索結果のリスト
    """
    try:
        # APIキーとCSE IDが設定されていない場合はエラーを発生させる
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEYが設定されていません。.envファイルに追加してください。")

        if not GOOGLE_CSE_ID:
            raise ValueError("GOOGLE_CSE_IDが設定されていません。.envファイルに追加してください。")

        # リクエストURLの構築
        base_url = "https://www.googleapis.com/customsearch/v1"
        params = {"q": query, "key": GOOGLE_API_KEY, "cx": GOOGLE_CSE_ID, "num": num_results}

        # リクエストの送信
        response = requests.get(base_url, params=params)
        data = response.json()

        # エラーチェック
        if "error" in data:
            raise Exception(f"Google Custom Search APIエラー: {data['error']['message']}")

        # 検索結果の抽出
        search_results = []
        for item in data.get("items", []):
            result = {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "displayLink": item.get("displayLink", ""),
            }
            search_results.append(result)

        return search_results

    except Exception as e:
        # エラーが発生した場合は例外を再発生させる
        raise Exception(f"情報の検索中にエラーが発生しました: {str(e)}")


def search_official_site(campsite_name):
    """
    キャンプ場の公式サイトを検索する関数

    Args:
        campsite_name (str): キャンプ場の名前

    Returns:
        dict: 公式サイトの情報
    """
    query = f"{campsite_name} 公式サイト キャンプ場"
    results = search_campsite_info(query, num_results=3)

    if results:
        return results[0]  # 最も関連性の高い結果を返す

    return None


def search_review_sites(campsite_name):
    """
    キャンプ場の口コミサイトを検索する関数

    Args:
        campsite_name (str): キャンプ場の名前

    Returns:
        list: 口コミサイトの情報のリスト
    """
    query = f"{campsite_name} 口コミ レビュー キャンプ場"
    return search_campsite_info(query, num_results=3)


def search_related_info(campsite_name, info_type="アクセス"):
    """
    キャンプ場に関連する特定の情報を検索する関数

    Args:
        campsite_name (str): キャンプ場の名前
        info_type (str, optional): 検索する情報の種類（例: 'アクセス', '設備', '料金'）

    Returns:
        list: 関連情報の検索結果
    """
    query = f"{campsite_name} {info_type} キャンプ場"
    return search_campsite_info(query, num_results=3)
