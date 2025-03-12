"""
検索結果の評価と改善を行うモジュール
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


def evaluate_search_results(query, query_analysis, campsites, max_results=5):
    """
    検索結果を評価し、ユーザーの意図に合致する結果を優先する関数

    Args:
        query (str): ユーザーの入力テキスト
        query_analysis (dict): クエリ解析結果
        campsites (list): 検索結果のキャンプ場リスト
        max_results (int, optional): 評価する最大結果数

    Returns:
        list: 評価・ランク付けされたキャンプ場リスト
    """
    if DEBUG:
        print(
            f"evaluate_search_results内: query型={type(query)}, query_analysis型={type(query_analysis)}, campsites型={type(campsites)}"
        )
        if isinstance(campsites, list) and campsites:
            print(f"campsites[0]型={type(campsites[0])}")

    if not GEMINI_API_KEY or not campsites:
        return campsites

    try:
        # 評価対象のキャンプ場を制限（処理時間短縮のため）
        target_campsites = campsites[:max_results]

        # Geminiモデルの設定
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-lite",
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 1024,
            },
        )

        # キャンプ場データをJSON文字列に変換
        campsites_json = json.dumps(
            [
                {
                    "name": site.get("name", ""),
                    "description": site.get("description", ""),
                    "features": site.get("features", []),
                    "facilities": site.get("facilities", []),
                    "region": site.get("region", ""),
                    "rating": site.get("rating", 0),
                }
                for site in target_campsites
            ],
            ensure_ascii=False,
        )

        # プロンプトの作成
        prompt = f"""
        あなたはキャンプ場検索の専門家です。以下のユーザーの検索意図と検索結果を評価し、
        ユーザーの意図に最も合致するキャンプ場をランク付けしてください。

        ユーザーの検索クエリ: {query}

        検索意図の分析:
        - 場所要素: {query_analysis.get("location", "") if isinstance(query_analysis, dict) else ""}
        - 特徴要素: {", ".join(query_analysis.get("features", []) if isinstance(query_analysis, dict) else [])}
        - 施設要素: {", ".join(query_analysis.get("facilities", []) if isinstance(query_analysis, dict) else [])}
        - 優先度: {json.dumps(query_analysis.get("priorities", {}) if isinstance(query_analysis, dict) else {}, ensure_ascii=False)}

        # 利用スタイルのキーワードを抽出
        利用スタイル: {"ソロキャンプ" if "ソロキャンプ" in query or ("ソロ" in query_analysis.get("features", []) if isinstance(query_analysis, dict) else False) else 
                    "カップル" if "カップル" in query or ("カップル" in query_analysis.get("features", []) if isinstance(query_analysis, dict) else False) else
                    "ファミリー" if "ファミリー" in query or ("家族" in query_analysis.get("features", []) if isinstance(query_analysis, dict) else False) or ("子供" in query_analysis.get("features", []) if isinstance(query_analysis, dict) else False) else
                    "グループ" if "グループ" in query or ("グループ" in query_analysis.get("features", []) if isinstance(query_analysis, dict) else False) else "指定なし"}

        検索結果のキャンプ場:
        {campsites_json}

        各キャンプ場について、以下の評価を行ってください：
        1. ユーザーの検索意図との合致度（0-10）
        2. 推薦理由（なぜこのキャンプ場がユーザーの意図に合致するか）
        3. 合致しない場合の理由
        4. 利用スタイルとの適合性も考慮してください

        回答は以下のJSON形式で返してください：
        ```json
        [
          {{
            "index": 0,
            "name": "キャンプ場名",
            "match_score": 8,
            "recommendation_reason": "このキャンプ場をおすすめする理由",
            "mismatch_reason": "意図に合致しない点（あれば）"
          }},
          ...
        ]
        ```

        インデックスは元の検索結果の順序（0から始まる）を示します。
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
            evaluation_results = json.loads(json_text)

            # 評価結果を元のキャンプ場データに追加
            for eval_result in evaluation_results:
                index = eval_result.get("index", 0)
                if 0 <= index < len(target_campsites):
                    # 元のスコアを保持
                    original_score = target_campsites[index].get("score", 0)
                    match_score = eval_result.get("match_score", 0)

                    # 両方のスコアを組み合わせる（元のスコアを優先）
                    combined_score = original_score + (match_score / 10)  # match_scoreは0-10なので、0-1のスケールに調整

                    target_campsites[index]["match_score"] = match_score
                    target_campsites[index]["score"] = round(combined_score, 1)  # 元のスコアフィールドを更新
                    target_campsites[index]["recommendation_reason"] = eval_result.get("recommendation_reason", "")
                    target_campsites[index]["mismatch_reason"] = eval_result.get("mismatch_reason", "")

            # スコアでソート（match_scoreではなく）
            sorted_campsites = sorted(target_campsites, key=lambda x: x.get("score", 0), reverse=True)

            # 評価していないキャンプ場を追加
            if len(campsites) > max_results:
                sorted_campsites.extend(campsites[max_results:])

            return sorted_campsites

        except json.JSONDecodeError:
            if DEBUG:
                print(f"JSON解析エラー: {json_text}")
            return campsites

    except Exception as e:
        if DEBUG:
            print(f"検索結果評価エラー: {str(e)}")
        return campsites


def generate_search_summary(
    query,
    query_analysis,
    campsites,
    max_results=3,
    perfect_match_campsites=None,
    popular_campsites=None,
    top_rated_campsites=None,
):
    """
    検索結果の要約を生成する関数

    Args:
        query (str): ユーザーの入力テキスト
        query_analysis (dict): クエリ解析結果
        campsites (list): 検索結果のキャンプ場リスト
        max_results (int, optional): 要約に含める最大結果数
        perfect_match_campsites (list, optional): ユーザーにぴったりのキャンプ場リスト
        popular_campsites (list, optional): 人気のキャンプ場リスト
        top_rated_campsites (list, optional): 評価の高いキャンプ場リスト

    Returns:
        str: 検索結果の要約テキスト
    """
    if not GEMINI_API_KEY or not campsites:
        return ""

    try:
        # 要約対象のキャンプ場を制限（処理時間短縮のため）
        target_campsites = campsites[:max_results]

        # Geminiモデルの設定
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-lite",
            generation_config={
                "temperature": 0.4,
                "max_output_tokens": 1024,
            },
        )

        # キャンプ場データをJSON文字列に変換
        campsites_json = json.dumps(
            [
                {
                    "name": site.get("name", ""),
                    "description": site.get("description", ""),
                    "features": site.get("features", []),
                    "facilities": site.get("facilities", []),
                    "region": site.get("region", ""),
                    "rating": site.get("rating", 0),
                    "reviews_count": site.get("reviews_count", 0),
                    "review_summary": site.get("review_summary", ""),
                    "ai_recommendation_reason": site.get("ai_recommendation_reason", ""),
                }
                for site in target_campsites
            ],
            ensure_ascii=False,
        )

        # グループ分けしたキャンプ場データも変換
        perfect_match_json = "[]"
        popular_json = "[]"
        top_rated_json = "[]"

        if perfect_match_campsites:
            perfect_match_json = json.dumps(
                [
                    {
                        "name": site.get("name", ""),
                        "region": site.get("region", ""),
                        "rating": site.get("rating", 0),
                        "reviews_count": site.get("reviews_count", 0),
                        "score": site.get("score", 0),
                        "recommendation_reason": site.get("recommendation_reason", ""),
                    }
                    for site in perfect_match_campsites
                ],
                ensure_ascii=False,
            )

        if popular_campsites:
            popular_json = json.dumps(
                [
                    {
                        "name": site.get("name", ""),
                        "region": site.get("region", ""),
                        "rating": site.get("rating", 0),
                        "reviews_count": site.get("reviews_count", 0),
                    }
                    for site in popular_campsites
                ],
                ensure_ascii=False,
            )

        if top_rated_campsites:
            top_rated_json = json.dumps(
                [
                    {
                        "name": site.get("name", ""),
                        "region": site.get("region", ""),
                        "rating": site.get("rating", 0),
                        "reviews_count": site.get("reviews_count", 0),
                    }
                    for site in top_rated_campsites
                ],
                ensure_ascii=False,
            )

        # プロンプトの作成
        prompt = f"""
        あなたはキャンプ場検索の専門家です。以下のユーザーの検索クエリと検索結果に基づいて、
        検索結果の要約を生成してください。

        ユーザーの検索クエリ: {query}

        検索意図の分析:
        - 場所要素: {query_analysis.get("location", "") if isinstance(query_analysis, dict) else ""}
        - 特徴要素: {", ".join(query_analysis.get("features", []) if isinstance(query_analysis, dict) else [])}
        - 施設要素: {", ".join(query_analysis.get("facilities", []) if isinstance(query_analysis, dict) else [])}
        - 優先度: {json.dumps(query_analysis.get("priorities", {}) if isinstance(query_analysis, dict) else {}, ensure_ascii=False)}

        # 利用スタイルのキーワードを抽出
        利用スタイル: {"ソロキャンプ" if "ソロキャンプ" in query or ("ソロ" in query_analysis.get("features", []) if isinstance(query_analysis, dict) else False) else 
                    "カップル" if "カップル" in query or ("カップル" in query_analysis.get("features", []) if isinstance(query_analysis, dict) else False) else
                    "ファミリー" if "ファミリー" in query or ("家族" in query_analysis.get("features", []) if isinstance(query_analysis, dict) else False) or ("子供" in query_analysis.get("features", []) if isinstance(query_analysis, dict) else False) else
                    "グループ" if "グループ" in query or ("グループ" in query_analysis.get("features", []) if isinstance(query_analysis, dict) else False) else "指定なし"}

        検索結果のキャンプ場:
        {campsites_json}
        
        ユーザーにぴったりのキャンプ場3選:
        {perfect_match_json}
        
        人気のキャンプ場3選:
        {popular_json}
        
        評価の高いキャンプ場3選:
        {top_rated_json}

        以下の内容を含む要約を生成してください：
        1. 検索結果の概要（何件見つかったか、どのような特徴があるかなど）
        2. ユーザーにぴったりのキャンプ場3選とその理由
        3. 人気のキャンプ場3選の紹介
        4. 評価の高いキャンプ場3選の紹介
        5. 利用スタイルに合わせたおすすめポイント
        6. ユーザーの検索意図に対する回答

        要約は日本語で、会話的な口調で作成してください。マークダウン形式で見やすく整形してください。
        各セクションには適切な見出しを付けてください。
        """

        # Gemini APIを呼び出し
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        if DEBUG:
            print(f"検索要約生成エラー: {str(e)}")
        return ""
