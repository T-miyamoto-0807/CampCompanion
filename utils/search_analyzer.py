"""
Geminiを使用して検索結果を分析するモジュール
"""

import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# Gemini APIの設定
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# デバッグモードの設定
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Gemini APIの初期化
try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"Gemini APIの初期化中にエラーが発生しました: {str(e)}")


def analyze_search_results(query, raw_results):
    """
    検索結果をGeminiで分析する関数

    Args:
        query (str): ユーザーの検索クエリ
        raw_results (list): 生の検索結果データ

    Returns:
        dict: 分析結果
            - structured_results (list): 構造化された検索結果
            - featured_campsites (list): 特集されているキャンプ場
            - summary (str): 検索結果の要約
    """
    if DEBUG:
        print(f"analyze_search_results内: query型={type(query)}, raw_results型={type(raw_results)}")
        if isinstance(raw_results, list) and raw_results:
            print(f"raw_results[0]型={type(raw_results[0])}")

    if not GEMINI_API_KEY or not raw_results:
        return {"structured_results": raw_results, "featured_campsites": [], "summary": ""}

    try:
        # Geminiモデルの設定
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-lite",
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 2048,
            },
        )

        # 検索結果をJSON文字列に変換（最大5件）
        results_json = json.dumps(raw_results[:5], ensure_ascii=False)

        # プロンプトの作成
        prompt = f"""
        あなたはキャンプ場検索の専門家です。以下の検索クエリと検索結果を分析して、
        より構造化された情報を提供してください。

        検索クエリ: {query}

        検索結果:
        {results_json}

        以下の情報を抽出・分析してJSON形式で返してください：

        1. 構造化された検索結果：各キャンプ場の情報を整理し、不足している情報があれば補完してください。
        2. 特集されているキャンプ場：検索結果に含まれる有名または特集されているキャンプ場のリスト。
        3. 検索結果の要約：ユーザーの検索意図に基づいた検索結果の要約。

        回答は以下のJSON形式で返してください：
        ```json
        {{
          "structured_results": [
            {{
              "name": "キャンプ場名",
              "region": "地域",
              "description": "説明（補完または改善されたもの）",
              "features": ["特徴1", "特徴2", ...],
              "facilities": ["施設1", "施設2", ...],
              "highlights": "このキャンプ場の特筆すべき点",
              "best_for": "このキャンプ場が最適な利用者層や目的"
            }},
            ...
          ],
          "featured_campsites": ["有名キャンプ場1", "有名キャンプ場2", ...],
          "summary": "検索結果の要約文"
        }}
        ```
        """

        # Gemini APIを呼び出し
        response = model.generate_content(prompt)
        response_text = response.text

        # JSONデータを抽出
        json_start = response_text.find("```json") + 7 if "```json" in response_text else 0
        json_end = response_text.find("```", json_start) if "```" in response_text[json_start:] else len(response_text)

        if json_start > 0 and json_end > json_start:
            json_text = response_text[json_start:json_end].strip()
        else:
            json_text = response_text

        # JSONデータをパース
        try:
            analysis_result = json.loads(json_text)

            # 元の検索結果と分析結果をマージ
            structured_results = merge_with_original_results(raw_results, analysis_result.get("structured_results", []))

            return {
                "structured_results": structured_results,
                "featured_campsites": analysis_result.get("featured_campsites", []),
                "summary": analysis_result.get("summary", ""),
            }
        except json.JSONDecodeError:
            if DEBUG:
                print(f"JSON解析エラー: {json_text}")
            return {"structured_results": raw_results, "featured_campsites": [], "summary": ""}

    except Exception as e:
        if DEBUG:
            print(f"検索結果分析エラー: {str(e)}")
        return {"structured_results": raw_results, "featured_campsites": [], "summary": ""}


def merge_with_original_results(original_results, analyzed_results):
    """
    元の検索結果と分析結果をマージする関数

    Args:
        original_results (list): 元の検索結果
        analyzed_results (list): 分析された検索結果

    Returns:
        list: マージされた検索結果
    """
    # 分析結果が空の場合は元の結果をそのまま返す
    if not analyzed_results:
        return original_results

    # 分析結果のキャンプ場名をキーとした辞書を作成
    analyzed_dict = {result.get("name", "").lower(): result for result in analyzed_results if result.get("name")}

    # マージ結果を格納するリスト
    merged_results = []

    # 元の結果をループ
    for original in original_results:
        name = original.get("name", "").lower()

        # 分析結果に同じ名前のキャンプ場がある場合
        if name in analyzed_dict:
            analyzed = analyzed_dict[name]

            # 元の結果をコピー
            merged = original.copy()

            # 分析結果から情報を追加・更新
            if analyzed.get("description") and (
                not original.get("description")
                or len(analyzed.get("description", "")) > len(original.get("description", ""))
            ):
                merged["description"] = analyzed.get("description")

            if analyzed.get("features"):
                if not merged.get("features"):
                    merged["features"] = []
                # 重複を避けながら追加
                for feature in analyzed.get("features", []):
                    if feature not in merged["features"]:
                        merged["features"].append(feature)

            if analyzed.get("facilities"):
                if not merged.get("facilities"):
                    merged["facilities"] = []
                # 重複を避けながら追加
                for facility in analyzed.get("facilities", []):
                    if facility not in merged["facilities"]:
                        merged["facilities"].append(facility)

            # 新しいフィールドを追加
            if analyzed.get("highlights"):
                merged["highlights"] = analyzed.get("highlights")

            if analyzed.get("best_for"):
                merged["best_for"] = analyzed.get("best_for")

            merged_results.append(merged)

            # 処理済みの分析結果を削除
            del analyzed_dict[name]
        else:
            # 分析結果に対応するキャンプ場がない場合はそのまま追加
            merged_results.append(original)

    # 残りの分析結果（元の結果にはなかった新しいキャンプ場）を追加
    for name, analyzed in analyzed_dict.items():
        # 最低限必要なフィールドを持つ新しいキャンプ場データを作成
        new_campsite = {
            "name": analyzed.get("name", ""),
            "region": analyzed.get("region", ""),
            "description": analyzed.get("description", ""),
            "features": analyzed.get("features", []),
            "facilities": analyzed.get("facilities", []),
            "highlights": analyzed.get("highlights", ""),
            "best_for": analyzed.get("best_for", ""),
            "source": "gemini_analysis",  # ソースを示すフラグ
            "rating": 0,
            "reviews_count": 0,
        }
        merged_results.append(new_campsite)

    return merged_results


def extract_featured_campsites(query, search_results):
    """
    検索結果から特集されているキャンプ場を抽出する関数

    Args:
        query (str): 検索クエリ
        search_results (list): 検索結果

    Returns:
        list: 特集されているキャンプ場のリスト
    """
    # Geminiを使用して分析
    analysis_result = analyze_search_results(query, search_results)

    # 特集されているキャンプ場を取得
    featured_campsites = analysis_result.get("featured_campsites", [])

    # 構造化された検索結果を取得
    structured_results = analysis_result.get("structured_results", search_results)

    # 要約を取得
    summary = analysis_result.get("summary", "")

    return {"featured_campsites": featured_campsites, "structured_results": structured_results, "summary": summary}
