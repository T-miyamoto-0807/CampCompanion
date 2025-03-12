import os
import google.generativeai as genai
import json
import requests
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# Gemini APIの設定
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# APIキーが設定されていない場合の警告
if not GEMINI_API_KEY:
    print("警告: GEMINI_API_KEYが設定されていません。.envファイルまたはStreamlit Secretsを確認してください。")

# Gemini APIの初期化
try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"Gemini APIの初期化中にエラーが発生しました: {str(e)}")


def get_gemini_response(prompt, temperature=0.7, max_output_tokens=2048):
    """
    Gemini APIを使用してプロンプトに対する応答を取得する関数

    Args:
        prompt (str): 送信するプロンプト
        temperature (float, optional): 生成の多様性を制御するパラメータ。デフォルトは0.7。
        max_output_tokens (int, optional): 生成するトークンの最大数。デフォルトは2048。

    Returns:
        str: Gemini APIからの応答テキスト

    Raises:
        Exception: API呼び出し中にエラーが発生した場合
    """
    try:
        # APIキーが設定されていない場合はエラーを発生させる
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEYが設定されていません。.envファイルに追加してください。")

        # Geminiモデルの設定
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-lite",
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
            },
        )

        # プロンプトを送信して応答を取得
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        raise Exception(f"Gemini API呼び出し中にエラーが発生しました: {str(e)}")


def get_camping_recommendations(preferences, num_recommendations=3):
    """
    ユーザーの好みに基づいてキャンプ場の推薦を取得する関数

    Args:
        preferences (str): ユーザーの好みや条件
        num_recommendations (int, optional): 推薦するキャンプ場の数。デフォルトは3。

    Returns:
        str: 推薦されたキャンプ場の情報
    """
    prompt = f"""
    あなたは日本のキャンプ場に詳しい専門家です。
    以下の条件に合うキャンプ場を{num_recommendations}つ提案してください。
    それぞれのキャンプ場について、名前、場所、特徴、おすすめポイントを簡潔に説明してください。
    
    ユーザーの希望条件:
    {preferences}
    
    回答形式:
    1. [キャンプ場名] - [場所]
       特徴: [簡潔な説明]
       おすすめポイント: [おすすめポイント]
    
    2. [キャンプ場名] - [場所]
       ...
    
    3. [キャンプ場名] - [場所]
       ...
    """

    return get_gemini_response(prompt)


def search_campsites_gemini(query):
    """
    Gemini APIを使用してキャンプ場を検索する関数

    Args:
        query (str): 検索クエリ

    Returns:
        list: キャンプ場データのリスト
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEYが設定されていません。.envファイルに追加してください。")

    # Gemini APIのエンドポイント
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key={GEMINI_API_KEY}"

    # プロンプトの作成
    prompt = f"""
    あなたは日本のキャンプ場に関する専門家です。以下の条件に合うキャンプ場を5つ探して、JSON形式で詳細情報を提供してください。

    検索条件: {query}

    各キャンプ場について、以下の情報を含めてください：
    - name: キャンプ場の名前
    - region: 地域（都道府県）
    - address: 住所
    - description: キャンプ場の特徴や魅力の説明（200文字程度）
    - rating: 評価（0〜5の数値、小数点第一位まで）
    - reviews_count: レビュー数（整数）
    - price: 料金の目安（文字列、例: "¥3,000〜/泊"）
    - facilities: 施設・設備のリスト（配列）
    - features: 特徴のリスト（配列）
    - location: 緯度・経度（lat, lngのオブジェクト）
    - reviews: レビュー情報の配列（各レビューはname, rating, text, timeを含む）

    回答は以下のJSON形式で返してください：
    ```json
    [
      {{
        "name": "キャンプ場名",
        "region": "地域",
        "address": "住所",
        "description": "説明",
        "rating": 4.5,
        "reviews_count": 100,
        "price": "¥3,000〜/泊",
        "facilities": ["トイレ", "シャワー", "電源"],
        "features": ["湖畔", "ペット可"],
        "location": {{"lat": 35.123, "lng": 139.456}},
        "reviews": [
          {{"name": "レビュー投稿者名", "rating": 5, "text": "レビュー内容", "time": "2023年10月"}}
        ]
      }}
    ]
    ```
    """

    # リクエストヘッダー
    headers = {"Content-Type": "application/json"}

    # リクエストボディ
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "topP": 0.8, "topK": 40, "maxOutputTokens": 2048},
    }

    try:
        # APIリクエスト
        response = requests.post(url, headers=headers, json=data)

        # レスポンスのステータスコードを確認
        if response.status_code != 200:
            print(f"API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return []

        # JSONレスポンスを解析
        response_data = response.json()

        # テキスト応答を抽出
        text = response_data["candidates"][0]["content"]["parts"][0]["text"]

        # JSONデータを抽出
        json_start = text.find("```json") + 7
        json_end = text.find("```", json_start)

        if json_start == -1 or json_end == -1:
            # JSON形式でない場合は、テキスト全体を解析
            json_text = text
        else:
            json_text = text[json_start:json_end].strip()

        # JSONデータをパース
        campsites = json.loads(json_text)

        return campsites

    except Exception as e:
        print(f"Error in search_campsites_gemini: {str(e)}")
        return []


def analyze_campsite_reviews(campsite, user_preferences):
    """
    キャンプ場の口コミを分析して特徴を要約し、ユーザーへのおすすめ理由を生成する関数

    Args:
        campsite (dict): キャンプ場データ
        user_preferences (dict): ユーザーの好み設定

    Returns:
        dict: 分析結果（summary, recommendation_reason）
    """
    if not GEMINI_API_KEY:
        return {"summary": "", "recommendation_reason": ""}

    # Gemini APIのエンドポイント
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key={GEMINI_API_KEY}"

    # キャンプ場の情報を収集
    name = campsite.get("name", "不明")
    description = campsite.get("description", "")
    reviews = campsite.get("reviews", [])
    features = campsite.get("features", [])
    facilities = campsite.get("facilities", [])

    # レビューテキストを抽出
    review_texts = []
    for review in reviews:
        if review.get("text"):
            review_texts.append(review.get("text"))

    # ユーザーの好みを文字列に変換
    preferences_text = ""
    for key, value in user_preferences.items():
        if value > 0:
            preferences_text += f"{key}: {value}/5, "

    # プロンプトの作成
    prompt = f"""
    あなたは日本のキャンプ場に関する専門家です。以下のキャンプ場について、口コミや説明文を分析して特徴を要約し、
    ユーザーの好みに基づいておすすめ理由を生成してください。

    キャンプ場名: {name}
    
    説明文: {description}
    
    特徴: {', '.join(features)}
    
    設備: {', '.join(facilities)}
    
    口コミ:
    {' '.join(review_texts[:5])}
    
    ユーザーの好み:
    {preferences_text}
    
    以下の情報を日本語で提供してください：
    1. このキャンプ場の特徴や雰囲気の要約（150文字程度）
    2. このユーザーにおすすめする理由（150文字程度）
    
    回答は以下のJSON形式で返してください：
    ```json
    {{
      "summary": "キャンプ場の特徴や雰囲気の要約",
      "recommendation_reason": "このユーザーにおすすめする理由"
    }}
    ```
    """

    # リクエストヘッダー
    headers = {"Content-Type": "application/json"}

    # リクエストボディ
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "topP": 0.8, "topK": 40, "maxOutputTokens": 1024},
    }

    try:
        # APIリクエスト
        response = requests.post(url, headers=headers, json=data)

        # レスポンスのステータスコードを確認
        if response.status_code != 200:
            print(f"API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return {"summary": "", "recommendation_reason": ""}

        # JSONレスポンスを解析
        response_data = response.json()

        # テキスト応答を抽出
        text = response_data["candidates"][0]["content"]["parts"][0]["text"]

        # JSONデータを抽出
        json_start = text.find("```json") + 7
        json_end = text.find("```", json_start)

        if json_start == -1 or json_end == -1:
            # JSON形式でない場合は、テキスト全体を解析
            json_text = text
        else:
            json_text = text[json_start:json_end].strip()

        # JSONデータをパース
        analysis_result = json.loads(json_text)

        return analysis_result

    except Exception as e:
        print(f"Error in analyze_campsite_reviews: {str(e)}")
        return {"summary": "", "recommendation_reason": ""}
