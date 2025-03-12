"""
並列検索を実行するモジュール
複数の検索APIを同時に呼び出し、結果を統合します
"""

import os
import json
import asyncio
import aiohttp
import requests
import streamlit as st
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from utils.places_api_new import (
    search_campsites_new,
    convert_places_to_app_format_new,
    get_place_details_new,
    get_place_photo_new,
    get_place_photos_new,
    get_nearby_campsites_new,
)
from utils.web_search import search_campsites_web, combine_search_results
from utils.query_analyzer import analyze_query
from utils.search_evaluator import evaluate_search_results, generate_search_summary
from utils.search_analyzer import analyze_search_results
from utils.gemini_api import get_gemini_response
from utils.geocoding import get_location_coordinates
import time
from typing import List, Dict, Any, Tuple, Optional
import concurrent.futures
import threading
import queue

# 環境変数の読み込み
load_dotenv()

# デバッグモードの設定
DEBUG = True  # デバッグモードを強制的に有効化

# スレッド間通信用のグローバル変数
if "global_progress_queue" not in globals():
    global_progress_queue = queue.Queue()


# 検索の進捗状況を報告する関数
def report_progress(message):
    """
    検索の進捗状況を報告する関数
    グローバル変数のキューを使用してスレッドセーフに実装

    Args:
        message (str): 進捗状況メッセージ
    """
    # デバッグ出力
    if DEBUG:
        print(f"\n===== 進捗状況の報告: '{message}' =====")

    # グローバル変数のキューを使用
    try:
        global global_progress_queue
        global_progress_queue.put(message)
    except Exception as e:
        if DEBUG:
            print(f"進捗報告エラー: {str(e)}")


def search_places_api(query):
    """
    Places APIで検索する関数

    Args:
        query (str): 検索クエリ

    Returns:
        list: キャンプ場データのリスト、またはエラー情報を含む辞書
    """
    try:
        if DEBUG:
            print(f"\n===== search_places_api: 検索クエリ: '{query}' =====")

        # Places APIで検索を実行
        if DEBUG:
            print(f"search_campsites_new を実行します...")
        places_data = search_campsites_new(query)
        if DEBUG:
            print(
                f"search_campsites_new が完了しました: {len(places_data) if places_data and 'places' in places_data else 0}件"
            )

        # エラーチェック
        if places_data and "error" in places_data:
            if DEBUG:
                print(f"Places API検索エラー: {places_data.get('error', '')}")
            return places_data

        # 結果をアプリケーションのフォーマットに変換
        if DEBUG:
            print(f"convert_places_to_app_format_new を実行します...")
        campsites = convert_places_to_app_format_new(places_data)
        if DEBUG:
            print(f"convert_places_to_app_format_new が完了しました: {len(campsites) if campsites else 0}件")

        return campsites
    except Exception as e:
        if DEBUG:
            print(f"Places API検索エラー: {str(e)}")
        return {"error": f"検索中にエラーが発生しました: {str(e)}"}


def search_web(query):
    """
    Web検索を実行する関数

    Args:
        query (str): 検索クエリ

    Returns:
        list: キャンプ場データのリスト
    """
    try:
        if DEBUG:
            print(f"\n===== search_web: 検索クエリ: '{query}' =====")

        # Web検索の実装（現在は空のリストを返す）
        return []
    except Exception as e:
        if DEBUG:
            print(f"Web検索エラー: {str(e)}")
        return []


def parallel_search(query, location=None):
    """
    複数のソースから並列検索を実行する関数

    Args:
        query (str): 検索クエリ
        location (dict, optional): 位置情報（緯度・経度）

    Returns:
        dict: 検索結果
    """
    if DEBUG:
        print(f"\n===== parallel_search: クエリ: '{query}' =====")
        print(f"位置情報: {location}")

    # 検索結果を格納する辞書
    search_results = {
        "campsites": [],
        "sources": [],
    }

    try:
        # Places APIで検索
        places_results = search_places_api(query)

        # エラーチェック
        if isinstance(places_results, list) and places_results:
            search_results["campsites"].extend(places_results)
            search_results["sources"].append("places_api")
            if DEBUG:
                print(f"Places API検索結果: {len(places_results)}件")
        elif isinstance(places_results, list) and not places_results:
            if DEBUG:
                print(f"Places API検索結果: 0件")
        else:
            if DEBUG:
                print(f"Places API検索エラー: {places_results}")

            # APIエラーがある場合は報告
            error_message = places_results.get("error", "")
            if error_message:
                if "503" in error_message or places_results.get("status_code") == 503:
                    report_progress(
                        "⚠️ Google Places APIが一時的に利用できません。しばらく時間をおいてから再度お試しください。"
                    )
                else:
                    report_progress(f"⚠️ 検索中にエラーが発生しました: {error_message}")

        # 位置情報がある場合は近くのキャンプ場も検索
        if location and "lat" in location and "lng" in location:
            try:
                nearby_results = get_nearby_campsites_new(
                    location["lat"], location["lng"], radius=50000, keyword="キャンプ場"
                )

                # 近くのキャンプ場を変換
                nearby_campsites = convert_places_to_app_format_new(nearby_results)

                if nearby_campsites:
                    # 重複を削除
                    existing_ids = [campsite.get("place_id", "") for campsite in search_results["campsites"]]
                    unique_nearby = [
                        campsite for campsite in nearby_campsites if campsite.get("place_id", "") not in existing_ids
                    ]

                    if unique_nearby:
                        search_results["campsites"].extend(unique_nearby)
                        if "nearby" not in search_results["sources"]:
                            search_results["sources"].append("nearby")

                        if DEBUG:
                            print(f"近くのキャンプ場検索結果: {len(unique_nearby)}件（重複削除後）")
            except Exception as e:
                if DEBUG:
                    print(f"近くのキャンプ場検索エラー: {str(e)}")

        # 重複を削除
        unique_campsites = []
        seen_ids = set()

        for campsite in search_results["campsites"]:
            place_id = campsite.get("place_id", "")
            if place_id and place_id not in seen_ids:
                seen_ids.add(place_id)
                unique_campsites.append(campsite)

        search_results["campsites"] = unique_campsites

        if DEBUG:
            print(f"重複削除後のキャンプ場: {len(unique_campsites)}件")
            print(f"検索ソース: {search_results['sources']}")

        # 検索結果がない場合はWeb検索を試みる
        if not search_results["campsites"]:
            try:
                web_results = search_web(query)
                if web_results:
                    search_results["campsites"].extend(web_results)
                    search_results["sources"].append("web")
                    if DEBUG:
                        print(f"Web検索結果: {len(web_results)}件")
            except Exception as e:
                if DEBUG:
                    print(f"Web検索エラー: {str(e)}")

        return search_results

    except Exception as e:
        if DEBUG:
            print(f"並列検索エラー: {str(e)}")
            import traceback

            print(traceback.format_exc())
        return search_results


def search_and_analyze(query, user_preferences=None, facilities_required=None):
    """
    検索とAI分析を実行する関数
    """
    if "current_progress" not in st.session_state:
        st.session_state.current_progress = ""

    # 進捗状況の報告
    report_progress("🔍 キャンプ場を検索しています...")

    # 検索クエリから位置情報を抽出
    location = None
    if DEBUG:
        print(f"\n===== parallel_search: クエリ: '{query}' =====")
        print(f"位置情報: {location}")

    # 検索を実行
    search_results = parallel_search(query, location)

    # 検索結果がない場合
    if not search_results or not search_results.get("campsites"):
        return {
            "results": [],
            "summary": "検索条件に合うキャンプ場が見つかりませんでした。",
            "featured_campsites": [],
            "popular_campsites": [],
        }

    # 検索結果を取得
    campsites = search_results.get("campsites", [])

    # 検索結果を評価
    report_progress("⭐ 検索結果を評価しています...")

    # クエリを解析
    query_analysis = analyze_query(query)

    # 検索結果を評価
    campsites_with_scores = evaluate_search_results(query, query_analysis, campsites)

    # 検索結果を整理
    report_progress("📊 検索結果を整理しています...")

    # スコアでソート
    sorted_campsites = sorted(campsites_with_scores, key=lambda x: x.get("score", 0), reverse=True)

    # 特集キャンプ場（スコアが高いもの）
    featured_campsites = [c for c in sorted_campsites if c.get("score", 0) >= 0.7][:3]

    # 人気キャンプ場（レビュー数が多いもの）
    popular_campsites = sorted(campsites_with_scores, key=lambda x: x.get("reviews_count", 0), reverse=True)[:3]

    if DEBUG:
        print(f"特集キャンプ場: {len(featured_campsites)}件")
        for i, camp in enumerate(featured_campsites[:3], 1):
            print(f"{i}. {camp.get('name')} - スコア: {camp.get('score')}")

        print(f"人気キャンプ場: {len(popular_campsites)}件")
        for i, camp in enumerate(popular_campsites[:3], 1):
            print(f"{i}. {camp.get('name')} - 口コミ: {camp.get('reviews_count')}件")

    # 写真を取得するキャンプ場のIDを特定（特集と人気のみ）
    display_ids = set()
    for camp in featured_campsites + popular_campsites:
        display_ids.add(camp.get("place_id"))

    if DEBUG:
        print(f"写真取得対象のキャンプ場: {len(display_ids)}件")

    # 写真取得を並列処理で行う
    with ThreadPoolExecutor(max_workers=min(10, len(display_ids))) as executor:
        # キャンプ場ごとに写真取得処理を実行
        future_to_campsite = {
            executor.submit(fetch_photos_for_campsite, camp): camp
            for camp in campsites_with_scores
            if camp.get("place_id") in display_ids
        }

        # 結果を取得
        for future in concurrent.futures.as_completed(future_to_campsite):
            campsite = future_to_campsite[future]
            try:
                photo_urls = future.result()
                # 写真URLをキャンプ場データに追加
                if photo_urls:
                    campsite["photo_urls"] = photo_urls
                    campsite["image_url"] = photo_urls[0] if photo_urls else ""
                    if DEBUG:
                        print(f"写真URL取得成功: {campsite.get('name')} - {len(photo_urls)}枚")
            except Exception as e:
                if DEBUG:
                    print(f"写真取得エラー ({campsite.get('name')}): {str(e)}")

    # 口コミ分析を行うキャンプ場を特定（特集と人気のみ）
    report_progress("📊 口コミを分析しています...")
    with ThreadPoolExecutor(max_workers=min(6, len(display_ids))) as executor:
        # キャンプ場ごとに口コミ分析を実行
        future_to_analysis = {
            executor.submit(analyze_campsite_reviews, camp, user_preferences): camp
            for camp in campsites_with_scores
            if camp.get("place_id") in display_ids
        }

        # 結果を取得
        for future in concurrent.futures.as_completed(future_to_analysis):
            campsite = future_to_analysis[future]
            try:
                analysis = future.result()
                # 分析結果をキャンプ場データに追加
                if analysis:
                    campsite["review_summary"] = analysis.get("summary", "")
                    campsite["ai_recommendation"] = analysis.get("recommendation", "")
                    if DEBUG:
                        print(f"口コミ分析成功: {campsite.get('name')}")
            except Exception as e:
                if DEBUG:
                    print(f"口コミ分析エラー ({campsite.get('name')}): {str(e)}")

    # 検索結果の要約を生成
    report_progress("📝 検索結果の要約を生成しています...")
    summary = generate_search_summary(query, query_analysis, campsites_with_scores)

    # 検索完了
    report_progress(f"✅ 検索が完了しました！{len(campsites_with_scores)}件のキャンプ場が見つかりました。")

    if DEBUG:
        print(f"検索結果: {len(campsites_with_scores)}件")
        print("検索が完了しました")

    return {
        "results": campsites_with_scores,
        "summary": summary,
        "featured_campsites": featured_campsites,
        "popular_campsites": popular_campsites,
    }


def fetch_photos_for_campsite(campsite):
    """キャンプ場の写真を取得する関数"""
    photo_urls = []
    default_image = "https://placehold.jp/24/3d4070/ffffff/300x200.png?text=No%20Image"

    try:
        place_id = campsite.get("place_id", "")

        # 詳細情報を取得して写真名を取得
        details = get_place_details_new(place_id)

        if DEBUG:
            print(f"[写真取得] キャンプ場: {campsite.get('name')}")
            print(f"[写真取得] 詳細情報取得: {'成功' if details else '失敗'}")

        # GoogleMapと公式サイトのURLを追加
        if details:
            if "googleMapsUri" in details:
                campsite["googleMapsUri"] = details["googleMapsUri"]
            if "websiteUri" in details:
                campsite["websiteUri"] = details["websiteUri"]

        # 写真名がある場合は写真を取得
        photo_names = []
        if details and "photos" in details:
            for photo in details["photos"]:
                if "name" in photo:
                    photo_names.append(photo["name"])

        if photo_names:
            if DEBUG:
                print(f"[Places API] 写真名を{len(photo_names)}枚取得: {place_id}")

            # 最大6枚まで取得
            for i, photo_name in enumerate(photo_names[:6]):
                try:
                    photo_url = get_place_photo_new(photo_name)
                    if photo_url:
                        photo_urls.append(photo_url)
                except Exception as e:
                    if DEBUG:
                        print(f"写真URL取得エラー ({i+1}枚目): {str(e)}")

        # 写真名がない場合は元の方法で取得
        if not photo_urls:
            photo_names = campsite.get("photo_names", [])
            if photo_names:
                # 最大6枚まで取得
                for i, photo_name in enumerate(photo_names[:6]):
                    try:
                        photo_url = get_place_photo_new(photo_name)
                        if photo_url:
                            photo_urls.append(photo_url)
                    except Exception as e:
                        if DEBUG:
                            print(f"写真URL取得エラー ({i+1}枚目): {str(e)}")

        if DEBUG:
            print(f"[写真取得] 取得した写真URL: {len(photo_urls)}枚")

        return photo_urls
    except Exception as e:
        if DEBUG:
            print(f"写真取得関数エラー: {str(e)}")
        return []


def analyze_campsite_reviews(campsite, user_preferences=None):
    """
    キャンプ場の口コミを分析する関数

    Args:
        campsite (dict): キャンプ場データ
        user_preferences (dict, optional): ユーザーの好み設定

    Returns:
        dict: 分析結果
    """
    if DEBUG:
        print(f"\n===== analyze_campsite_reviews: {campsite.get('name', '不明')} =====")
        print(f"ユーザー好み設定: {user_preferences}")

    # 分析結果の初期化
    analysis = {"summary": "", "features": [], "trends": [], "recommendation": ""}

    try:
        # ユーザー好みが指定されていない場合は空の辞書を使用
        if user_preferences is None:
            user_preferences = {}

        # Gemini APIを使った分析を試みる
        try:
            from utils.gemini_api import get_gemini_response
            import json

            # キャンプ場の基本情報
            name = campsite.get("name", "不明")
            description = campsite.get("description", "")
            rating = campsite.get("rating", 0)
            reviews_count = campsite.get("reviews_count", 0)
            facilities = campsite.get("facilities", [])
            features = campsite.get("features", [])

            # 口コミを取得
            reviews = campsite.get("reviews", [])

            # 口コミの内容を結合
            review_texts = []
            if reviews:
                for review in reviews:
                    review_text = review.get("text", "")
                    if review_text:
                        review_texts.append(review_text)

            # Gemini APIへのプロンプト作成
            prompt = f"""
            あなたは日本のキャンプ場に関する専門家です。以下のキャンプ場について、情報を分析して特徴を要約し、
            おすすめポイントを生成してください。

            キャンプ場名: {name}
            
            説明文: {description}
            
            評価: {rating}（{reviews_count}件の口コミ）
            
            特徴: {', '.join(features)}
            
            設備: {', '.join(facilities)}
            
            口コミ:
            {' '.join(review_texts[:5])}
            
            以下の情報を日本語で提供してください：
            1. このキャンプ場の特徴や雰囲気の要約（150文字程度）
            2. このキャンプ場の主な特徴（箇条書きで5つ）
            3. 口コミから見る傾向（箇条書きで5つ）
            4. おすすめポイント（150文字程度）
            
            回答は以下のJSON形式で返してください：
            ```json
            {{
              "summary": "キャンプ場の特徴や雰囲気の要約",
              "features": ["特徴1", "特徴2", "特徴3", "特徴4", "特徴5"],
              "trends": ["傾向1", "傾向2", "傾向3", "傾向4", "傾向5"],
              "recommendation": "おすすめポイント"
            }}
            ```
            """

            # Gemini APIを呼び出し
            response = get_gemini_response(prompt, temperature=0.2, max_output_tokens=1024)

            # JSONデータを抽出
            json_start = response.find("```json") + 7
            json_end = response.find("```", json_start)

            if json_start != -1 and json_end != -1:
                json_text = response[json_start:json_end].strip()
                gemini_analysis = json.loads(json_text)

                # 分析結果を設定
                analysis["summary"] = gemini_analysis.get("summary", "")
                analysis["features"] = gemini_analysis.get("features", [])
                analysis["trends"] = gemini_analysis.get("trends", [])
                analysis["recommendation"] = gemini_analysis.get("recommendation", "")

                if DEBUG:
                    print(f"Gemini APIによる分析結果:")
                    print(f"要約: {analysis['summary']}")
                    print(f"特徴: {analysis['features']}")
                    print(f"傾向: {analysis['trends']}")
                    print(f"おすすめ: {analysis['recommendation']}")

                return analysis

        except Exception as e:
            if DEBUG:
                print(f"Gemini API分析エラー: {str(e)}")
                print("ローカル分析にフォールバックします")

        # Gemini APIが使えない場合はローカル分析を実行
        # キャンプ場の基本情報
        name = campsite.get("name", "")
        rating = campsite.get("rating", 0)
        reviews_count = campsite.get("reviews_count", 0)
        facilities = campsite.get("facilities", [])
        features = campsite.get("features", [])
        description = campsite.get("description", "")

        # 口コミを取得
        reviews = campsite.get("reviews", [])

        # 口コミの内容を結合
        review_texts = []
        if reviews:
            for review in reviews:
                review_text = review.get("text", "")
                if review_text:
                    review_texts.append(review_text)

        # 基本情報から特徴を抽出
        extracted_features = []

        # 施設から特徴を抽出
        if facilities:
            extracted_features.extend(facilities[:5])

        # 特徴から特徴を抽出
        if features:
            extracted_features.extend(features[:5])

        # 説明文からキーワードを抽出
        if description:
            keywords = [
                "景色",
                "自然",
                "環境",
                "立地",
                "アクセス",
                "設備",
                "施設",
                "清潔",
                "きれい",
                "広い",
                "静か",
                "家族",
                "子供",
                "ペット",
                "テント",
                "キャンピングカー",
                "コテージ",
                "バンガロー",
                "温泉",
                "川",
                "海",
                "山",
                "湖",
                "森",
                "トイレ",
                "シャワー",
                "風呂",
                "炊事場",
                "売店",
                "薪",
                "焚き火",
                "BBQ",
                "バーベキュー",
            ]
            for keyword in keywords:
                if keyword in description:
                    extracted_features.append(keyword)

        # 重複を削除して特徴リストを作成
        unique_features = list(set(extracted_features))
        analysis["features"] = unique_features[:10]  # 最大10件

        # 口コミの傾向を生成
        trends = []

        # 評価に基づく傾向
        if rating >= 4.5:
            trends.append("評価が非常に高い")
        elif rating >= 4.0:
            trends.append("評価が高い")
        elif rating >= 3.5:
            trends.append("評価が良好")
        elif rating >= 3.0:
            trends.append("評価が平均的")
        else:
            trends.append("評価が平均以下")

        # 口コミ数に基づく傾向
        if reviews_count >= 1000:
            trends.append("非常に人気がある")
        elif reviews_count >= 500:
            trends.append("人気がある")
        elif reviews_count >= 100:
            trends.append("ある程度知られている")
        elif reviews_count >= 10:
            trends.append("口コミが少ない")
        else:
            trends.append("あまり知られていない")

        # 特徴に基づく傾向
        if "湖" in " ".join(unique_features) or "湖畔" in " ".join(unique_features):
            trends.append("湖畔の景色が魅力")
        if "山" in " ".join(unique_features):
            trends.append("山の景色が魅力")
        if "森" in " ".join(unique_features):
            trends.append("森の中の静かな環境")
        if "海" in " ".join(unique_features) or "ビーチ" in " ".join(unique_features):
            trends.append("海の近くの立地")
        if "温泉" in " ".join(unique_features):
            trends.append("温泉施設あり")
        if "子供" in " ".join(unique_features) or "ファミリー" in " ".join(unique_features):
            trends.append("家族連れに人気")
        if "ペット" in " ".join(unique_features):
            trends.append("ペット同伴可能")

        analysis["trends"] = trends

        # 口コミの要約を生成
        summary = f"{name}は"

        # 評価に基づく要約
        if rating >= 4.5:
            summary += "評価が非常に高く、多くの利用者から好評を得ています。"
        elif rating >= 4.0:
            summary += "評価が高く、利用者からの評判が良いキャンプ場です。"
        elif rating >= 3.5:
            summary += "一般的に良い評価を受けているキャンプ場です。"
        elif rating >= 3.0:
            summary += "平均的な評価を受けているキャンプ場です。"
        else:
            summary += "評価は平均以下ですが、"

        # 特徴に基づく要約
        if unique_features:
            summary += f" {', '.join(unique_features[:3])}などの特徴があります。"

        # 傾向に基づく要約
        if len(trends) > 2:
            summary += f" {trends[0]}で、{trends[1]}キャンプ場です。"

        analysis["summary"] = summary

        # おすすめポイントを生成
        recommendation = ""
        if rating >= 4.0 and unique_features:
            recommendation = f"評価が高く、特に{', '.join(unique_features[:3])}が充実したおすすめのキャンプ場です。"
        elif rating >= 3.5 and unique_features:
            recommendation = f"{', '.join(unique_features[:3])}が特徴的な、一般的に良い評価を受けているキャンプ場です。"
        else:
            recommendation = f"基本的な設備が整ったキャンプ場で、{', '.join(unique_features[:3] if unique_features else ['自然環境'])}が楽しめます。"

        analysis["recommendation"] = recommendation

        return analysis

    except Exception as e:
        if DEBUG:
            print(f"口コミ分析エラー: {str(e)}")
            import traceback

            print(traceback.format_exc())
        return analysis
