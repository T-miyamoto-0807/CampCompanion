"""
Web検索を使用してキャンプ場情報を取得するモジュール
"""

import os
import json
import requests
from dotenv import load_dotenv
import google.generativeai as genai

# 環境変数の読み込み
load_dotenv()

# APIキーの取得
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# デバッグモードの設定
DEBUG = os.getenv("DEBUG", "False").lower() == "true"


def search_campsites_web(query):
    """
    Web検索を使用してキャンプ場情報を検索する関数

    Args:
        query (str): 検索クエリ

    Returns:
        list: キャンプ場データのリスト
    """
    # APIキーが設定されていない場合はエラー
    if not GOOGLE_CSE_ID or not GOOGLE_API_KEY:
        return []

    # クエリに「キャンプ場」が含まれていない場合は追加
    if "キャンプ場" not in query and "camp" not in query.lower():
        query = f"{query} キャンプ場"

    # Google Custom Search APIのエンドポイント
    url = "https://www.googleapis.com/customsearch/v1"

    # リクエストパラメータ
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query,
        "num": 10,  # 最大10件の結果を取得
        "lr": "lang_ja",  # 日本語の結果のみ
        "gl": "jp",  # 日本のコンテンツを優先
    }

    try:
        # APIリクエストを送信
        response = requests.get(url, params=params)
        response.raise_for_status()  # エラーチェック

        # レスポンスをJSONとして解析
        data = response.json()

        # 検索結果がない場合は空のリストを返す
        if "items" not in data:
            return []

        # 検索結果をアプリケーションのフォーマットに変換
        campsites = []
        for item in data["items"]:
            # キャンプ場データを抽出（単一または複数）
            extracted_data = extract_campsite_data(item)
            if isinstance(extracted_data, list):
                campsites.extend(extracted_data)
            else:
                campsites.append(extracted_data)

        return campsites

    except Exception as e:
        return []


def extract_campsite_data(item):
    """
    検索結果からキャンプ場データを抽出する関数

    Args:
        item (dict): 検索結果の項目

    Returns:
        dict: キャンプ場データ
    """
    # タイトルと説明文を取得
    title = item.get("title", "")
    snippet = item.get("snippet", "")
    link = item.get("link", "")

    # キャンプ場名を抽出（タイトルから「公式」や「予約」などの文字を除去）
    name = title.split("|")[0].split("-")[0].strip()
    name = name.replace("公式", "").replace("予約", "").replace("サイト", "").strip()

    # 地域情報を抽出
    region = extract_region_from_text(title + " " + snippet)

    # 施設情報を抽出
    facilities = extract_facilities_from_text(snippet)

    # 特徴情報を抽出
    features = extract_features_from_text(snippet)

    # 画像URLを取得
    image_url = ""
    images = []

    # cse_imageから画像を取得
    if "pagemap" in item and "cse_image" in item["pagemap"]:
        try:
            img_src = item["pagemap"]["cse_image"][0].get("src", "")
            if img_src and isinstance(img_src, str) and img_src.strip() and img_src.startswith(("http://", "https://")):
                image_url = img_src
                images.append(image_url)
        except Exception as e:
            pass

    # cse_thumbnailから画像を取得
    if "pagemap" in item and "cse_thumbnail" in item["pagemap"]:
        try:
            thumbnail_url = item["pagemap"]["cse_thumbnail"][0].get("src", "")
            if (
                thumbnail_url
                and isinstance(thumbnail_url, str)
                and thumbnail_url.strip()
                and thumbnail_url.startswith(("http://", "https://"))
                and thumbnail_url not in images
            ):
                images.append(thumbnail_url)
        except Exception as e:
            pass

    # metatagsから画像を取得
    if "pagemap" in item and "metatags" in item["pagemap"]:
        try:
            for metatag in item["pagemap"]["metatags"]:
                # OGP画像
                og_image = metatag.get("og:image", "")
                if (
                    og_image
                    and isinstance(og_image, str)
                    and og_image.strip()
                    and og_image.startswith(("http://", "https://"))
                    and og_image not in images
                ):
                    images.append(og_image)

                # Twitter画像
                twitter_image = metatag.get("twitter:image", "")
                if (
                    twitter_image
                    and isinstance(twitter_image, str)
                    and twitter_image.strip()
                    and twitter_image.startswith(("http://", "https://"))
                    and twitter_image not in images
                ):
                    images.append(twitter_image)
        except Exception as e:
            pass

    # 画像が見つからない場合はデフォルト画像を設定
    if not image_url and images:
        image_url = images[0]
    elif not image_url:
        image_url = "https://via.placeholder.com/400x300?text=No+Image"

    # 画像URLの検証
    valid_images = []
    for img in images:
        if img and isinstance(img, str) and img.strip() and img.startswith(("http://", "https://")):
            valid_images.append(img)

    # キャンプ場データを構築
    campsite = {
        "name": name,
        "region": region,
        "address": "",  # Web検索からは正確な住所を取得できない
        "description": snippet,
        "rating": 0,  # Web検索からは評価を取得できない
        "reviews_count": 0,
        "facilities": facilities,
        "features": features,
        "image_url": image_url,
        "photos": valid_images[:5],  # 最大5枚の画像を保存
        "website": link,
        "source": "web_search",  # データソースを示すフラグ
    }

    return campsite


def extract_region_from_text(text):
    """
    テキストから地域情報を抽出する関数

    Args:
        text (str): テキスト

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

    # テキストから都道府県を抽出
    for prefecture in prefectures:
        if prefecture in text:
            return prefecture

    return ""


def extract_facilities_from_text(text):
    """
    テキストから施設情報を抽出する関数

    Args:
        text (str): テキスト

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

    # テキストから施設情報を抽出
    facilities = []
    for keyword in facility_keywords:
        if keyword in text:
            facilities.append(keyword)

    return facilities


def extract_features_from_text(text):
    """
    テキストから特徴情報を抽出する関数

    Args:
        text (str): テキスト

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

    # テキストから特徴情報を抽出
    features = []
    for keyword in feature_keywords:
        if keyword in text:
            features.append(keyword)

    return features


def combine_search_results(existing_results, new_results, max_results=15):
    """
    既存の検索結果と新しい検索結果を結合する関数

    Args:
        existing_results (list): 既存の検索結果
        new_results (list): 新しい検索結果
        max_results (int, optional): 最大結果数

    Returns:
        list: 結合された検索結果
    """
    # 既存の結果のキャンプ場名をリストアップ
    existing_names = [site.get("name", "").lower() for site in existing_results]

    # 重複検出用の辞書（キャンプ場名をキーとして、出現回数と元のインデックスを保存）
    campsite_occurrences = {}

    # 既存の結果を辞書に追加
    for i, site in enumerate(existing_results):
        name = site.get("name", "").lower()
        if name:
            if name in campsite_occurrences:
                campsite_occurrences[name]["count"] += 1
            else:
                campsite_occurrences[name] = {
                    "count": 1,
                    "index": i,
                    "source": site.get("source", ""),
                    "popularity_score": 0,  # 人気度スコア初期値
                }

    # 結合結果を格納するリスト
    combined_results = existing_results.copy()

    # 新しい結果を処理
    for site in new_results:
        name = site.get("name", "").lower()
        if not name:
            continue

        if name in campsite_occurrences:
            # 既存の結果と名前が一致する場合（重複）
            campsite_occurrences[name]["count"] += 1

            # 重複したキャンプ場の人気度スコアを増加
            campsite_occurrences[name]["popularity_score"] += 3

            # 既存の結果のインデックスを取得
            idx = campsite_occurrences[name]["index"]

            # 既存の結果に情報を追加
            combined_results[idx]["multiple_sources"] = True
            combined_results[idx]["occurrence_count"] = campsite_occurrences[name]["count"]
            combined_results[idx]["popularity_score"] = campsite_occurrences[name]["popularity_score"]

            # ソース情報を更新
            if "source" in combined_results[idx] and "source" in site:
                if site["source"] not in combined_results[idx]["source"]:
                    combined_results[idx]["source"] += f",{site['source']}"

            # 不足情報を補完
            for key, value in site.items():
                if key not in combined_results[idx] or not combined_results[idx][key]:
                    combined_results[idx][key] = value
        else:
            # 新しいキャンプ場の場合
            campsite_occurrences[name] = {
                "count": 1,
                "index": len(combined_results),
                "source": site.get("source", ""),
                "popularity_score": 0,
            }
            combined_results.append(site)

    # 人気度スコアに基づいてソート
    for i, site in enumerate(combined_results):
        name = site.get("name", "").lower()
        if name in campsite_occurrences:
            site["popularity_score"] = campsite_occurrences[name]["popularity_score"]

    # 人気度スコアでソート（降順）
    combined_results = sorted(combined_results, key=lambda x: x.get("popularity_score", 0), reverse=True)

    # 最大結果数に制限
    return combined_results[:max_results]


def enhance_article_summary(article, query):
    """
    Gemini APIを使用して記事の要約を改善する関数

    Args:
        article (dict): 記事情報
        query (str): 元の検索クエリ

    Returns:
        str: 改善された要約
    """
    try:
        # Gemini APIキーを取得
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            if DEBUG:
                print("GEMINI_API_KEYが設定されていません")
            return article["summary"]

        # Gemini APIの設定
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-pro")

        # 元の要約
        original_summary = article["summary"]
        title = article["title"]

        # プロンプトを作成
        prompt = f"""
        以下の記事タイトルと要約を、キャンプ場を探しているユーザーにとって有益な情報に焦点を当てて、
        より詳細で魅力的な日本語の要約（200文字程度）に書き直してください。
        
        検索クエリ: {query}
        記事タイトル: {title}
        元の要約: {original_summary}
        
        以下の点に注意して要約を作成してください：
        - キャンプ場の特徴や魅力を強調する
        - 具体的な情報（設備、アクセス、周辺環境など）を含める
        - 読みやすく、興味を引く文章にする
        - 日本語で書く
        - 200文字程度に収める
        
        要約のみを出力してください。
        """

        # Gemini APIを呼び出し
        response = model.generate_content(prompt)

        # レスポンスから要約を取得
        if response and hasattr(response, "text"):
            enhanced_summary = response.text.strip()
            if enhanced_summary:
                if DEBUG:
                    print(f"要約の改善に成功: {len(enhanced_summary)}文字")
                return enhanced_summary

        # 要約の改善に失敗した場合は元の要約を返す
        return original_summary

    except Exception as e:
        if DEBUG:
            print(f"要約改善エラー: {str(e)}")
        return article["summary"]


def search_related_articles(query, max_results=5, enhance_summaries=True):
    """
    キャンプ場に関連する記事やブログを検索する関数

    Args:
        query (str): 検索クエリ
        max_results (int): 最大結果数
        enhance_summaries (bool): 要約を改善するかどうか

    Returns:
        list: 関連記事のリスト（タイトル、URL、要約、ソースを含む）
    """
    # APIキーが設定されていない場合はエラー
    if not GOOGLE_CSE_ID or not GOOGLE_API_KEY:
        if DEBUG:
            print("APIキーが設定されていないため、関連記事検索ができません")
        return []

    # クエリにキャンプ関連のキーワードを追加
    search_query = f"{query} キャンプ場 特集 おすすめ"

    # Google Custom Search APIのエンドポイント
    url = "https://www.googleapis.com/customsearch/v1"

    # リクエストパラメータ
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": search_query,
        "num": max_results,  # 最大結果数
        "lr": "lang_ja",  # 日本語の結果のみ
        "gl": "jp",  # 日本のコンテンツを優先
    }

    try:
        if DEBUG:
            print(f"関連記事検索: クエリ='{search_query}'")

        # APIリクエスト
        response = requests.get(url, params=params)

        # レスポンスのステータスコードを確認
        if response.status_code != 200:
            if DEBUG:
                print(f"API Error: {response.status_code}")
                print(f"Response: {response.text}")
            return []

        # JSONレスポンスを解析
        data = response.json()

        # 検索結果がない場合
        if "items" not in data:
            if DEBUG:
                print("検索結果がありません")
            return []

        # 検索結果を処理
        articles = []
        for item in data["items"]:
            title = item.get("title", "")
            url = item.get("link", "")
            snippet = item.get("snippet", "")
            source = item.get("displayLink", "")

            # 記事情報を追加
            article = {"title": title, "url": url, "summary": snippet, "source": source}

            # メタデータがある場合は追加情報を取得
            if "pagemap" in item and "metatags" in item["pagemap"]:
                for metatag in item["pagemap"]["metatags"]:
                    # OGP説明文があれば要約として使用
                    if "og:description" in metatag and metatag["og:description"]:
                        article["summary"] = metatag["og:description"]

                    # 記事の公開日があれば追加
                    if "article:published_time" in metatag:
                        article["published_date"] = metatag["article:published_time"]

            articles.append(article)

        if DEBUG:
            print(f"関連記事検索結果: {len(articles)}件")

        # 要約の改善
        if enhance_summaries:
            if DEBUG:
                print("記事要約の改善を開始")

            for i, article in enumerate(articles):
                if DEBUG:
                    print(f"記事{i+1}の要約を改善中...")

                # 要約を改善
                article["summary"] = enhance_article_summary(article, query)

        return articles

    except Exception as e:
        if DEBUG:
            print(f"関連記事検索エラー: {str(e)}")
        return []
