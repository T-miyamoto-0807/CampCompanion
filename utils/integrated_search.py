import os
from dotenv import load_dotenv
from utils.places_api_new import search_campsites_new, convert_places_to_app_format_new
from utils.web_search import search_campsites_web, combine_search_results

# 環境変数の読み込み
load_dotenv()

# デバッグモードの設定
DEBUG = os.getenv("DEBUG", "False").lower() == "true"


def search_campsites_integrated(query, use_web_search=True, max_results=15):
    """
    Places APIとWeb検索を統合した検索を行う関数

    Args:
        query (str): 検索クエリ
        use_web_search (bool, optional): Web検索を使用するかどうか
        max_results (int, optional): 最大結果数

    Returns:
        list: キャンプ場データのリスト
    """
    results = []

    try:
        # 1. Places APIで検索
        places_data = search_campsites_new(query)
        places_results = convert_places_to_app_format_new(places_data)

        # 検索結果を統合
        results = places_results

        # 2. Web検索で補完
        if use_web_search and len(results) < max_results:
            try:
                web_results = search_campsites_web(query)
                results = combine_search_results(results, web_results, max_results)
            except ImportError:
                # web_searchモジュールがない場合はスキップ
                if DEBUG:
                    print("web_search module not found, skipping web search")
                pass
            except Exception as e:
                if DEBUG:
                    print(f"Error in web search: {str(e)}")
                pass

        # 3. 評価でソート
        results = sorted(results, key=lambda x: x.get("rating", 0), reverse=True)

        # 最大結果数に制限
        return results[:max_results]

    except Exception as e:
        print(f"Error in search_campsites_integrated: {str(e)}")
        return results


def enhance_search_results(campsites, query):
    """
    検索結果を強化する関数
    不足している情報を補完し、検索結果の質を向上させる

    Args:
        campsites (list): キャンプ場データのリスト
        query (str): 検索クエリ

    Returns:
        list: 強化されたキャンプ場データのリスト
    """
    enhanced_results = []

    for site in campsites:
        # 地域情報が不足している場合は推測
        if not site.get("region") and site.get("address"):
            site["region"] = extract_region_from_address(site["address"])

        # 説明文が不足している場合は生成
        if not site.get("description") and site.get("name"):
            site["description"] = generate_description(site, query)

        # 施設情報が不足している場合は推測
        if not site.get("facilities") and site.get("description"):
            site["facilities"] = extract_facilities_from_description(site["description"])

        # 特徴情報が不足している場合は推測
        if not site.get("features") and site.get("description"):
            site["features"] = extract_features_from_description(site["description"])

        enhanced_results.append(site)

    return enhanced_results


def extract_region_from_address(address):
    """
    住所から地域情報を抽出する関数

    Args:
        address (str): 住所

    Returns:
        str: 抽出された地域情報
    """
    # 都道府県のリスト
    prefectures = [
        "北海道",
        "青森県",
        "岩手県",
        "宮城県",
        "秋田県",
        "山形県",
        "福島県",
        "茨城県",
        "栃木県",
        "群馬県",
        "埼玉県",
        "千葉県",
        "東京都",
        "神奈川県",
        "新潟県",
        "富山県",
        "石川県",
        "福井県",
        "山梨県",
        "長野県",
        "岐阜県",
        "静岡県",
        "愛知県",
        "三重県",
        "滋賀県",
        "京都府",
        "大阪府",
        "兵庫県",
        "奈良県",
        "和歌山県",
        "鳥取県",
        "島根県",
        "岡山県",
        "広島県",
        "山口県",
        "徳島県",
        "香川県",
        "愛媛県",
        "高知県",
        "福岡県",
        "佐賀県",
        "長崎県",
        "熊本県",
        "大分県",
        "宮崎県",
        "鹿児島県",
        "沖縄県",
    ]

    # 住所から都道府県を抽出
    for prefecture in prefectures:
        if prefecture in address:
            return prefecture

    return ""


def generate_description(site, query):
    """
    キャンプ場の説明文を生成する関数

    Args:
        site (dict): キャンプ場データ
        query (str): 検索クエリ

    Returns:
        str: 生成された説明文
    """
    name = site.get("name", "")
    region = site.get("region", "")
    features = site.get("features", [])
    facilities = site.get("facilities", [])

    description = f"{name}は"

    if region:
        description += f"{region}にある"

    description += "キャンプ場です。"

    if features:
        description += f"特徴としては{', '.join(features[:3])}などがあります。"

    if facilities:
        description += f"設備には{', '.join(facilities[:3])}などが整っています。"

    if query and "キャンプ場" not in query:
        description += f"{query}に関連したキャンプ体験ができる場所です。"

    return description


def extract_facilities_from_description(description):
    """
    説明文から施設情報を抽出する関数

    Args:
        description (str): 説明文

    Returns:
        list: 抽出された施設情報のリスト
    """
    # キャンプ場の一般的な施設キーワード
    facility_keywords = [
        "トイレ",
        "シャワー",
        "炊事場",
        "売店",
        "レンタル",
        "電源",
        "Wi-Fi",
        "温泉",
        "コインランドリー",
        "ドッグラン",
        "遊具",
        "バーベキュー",
        "BBQ",
        "焚き火",
    ]

    # 説明文から施設情報を抽出
    facilities = []
    for keyword in facility_keywords:
        if keyword in description:
            facilities.append(keyword)

    return facilities


def extract_features_from_description(description):
    """
    説明文から特徴情報を抽出する関数

    Args:
        description (str): 説明文

    Returns:
        list: 抽出された特徴情報のリスト
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
        "ペット",
        "釣り",
        "川遊び",
        "海水浴",
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

    # 説明文から特徴情報を抽出
    features = []
    for keyword in feature_keywords:
        if keyword in description:
            features.append(keyword)

    return features
