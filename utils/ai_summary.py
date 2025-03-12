import os
from dotenv import load_dotenv
from utils.gemini_api import get_gemini_response
import openai

# 環境変数の読み込み
load_dotenv()

# OpenAI APIの設定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# APIキーが設定されていない場合のエラーメッセージ
if not OPENAI_API_KEY:
    print("警告: OPENAI_API_KEYが設定されていません。.envファイルに追加してください。")
else:
    # OpenAI APIの初期化
    openai.api_key = OPENAI_API_KEY


def summarize_reviews_with_gemini(reviews, max_reviews=5):
    """
    Gemini APIを使用してキャンプ場の口コミを要約する関数

    Args:
        reviews (list): 口コミのリスト
        max_reviews (int, optional): 要約する口コミの最大数

    Returns:
        str: 口コミの要約
    """
    if not reviews:
        return "口コミがありません。"

    # 要約するレビューの数を制限
    reviews_to_summarize = reviews[:max_reviews]

    # レビューテキストの抽出
    review_texts = []
    for review in reviews_to_summarize:
        rating = review.get("rating", "評価なし")
        text = review.get("text", "").strip()
        if text:
            review_texts.append(f"評価: {rating}★\n{text}")

    if not review_texts:
        return "有効な口コミがありません。"

    # プロンプトの作成
    prompt = f"""
    あなたは日本のキャンプ場に詳しい専門家です。
    以下のキャンプ場の口コミを分析して、簡潔に要約してください。
    良い点と改善点を明確にし、このキャンプ場の特徴を3〜5つのポイントにまとめてください。
    
    口コミ:
    {"\n\n".join(review_texts)}
    
    要約形式:
    【良い点】
    - ポイント1
    - ポイント2
    ...
    
    【改善点・注意点】
    - ポイント1
    - ポイント2
    ...
    
    【総評】
    このキャンプ場の特徴と全体的な評価を2〜3文で。
    """

    try:
        # Gemini APIを使用して要約を取得
        summary = get_gemini_response(prompt)
        return summary
    except Exception as e:
        return f"口コミの要約中にエラーが発生しました: {str(e)}"


def summarize_reviews_with_openai(reviews, max_reviews=5):
    """
    OpenAI APIを使用してキャンプ場の口コミを要約する関数

    Args:
        reviews (list): 口コミのリスト
        max_reviews (int, optional): 要約する口コミの最大数

    Returns:
        str: 口コミの要約
    """
    if not reviews:
        return "口コミがありません。"

    if not OPENAI_API_KEY:
        return "OpenAI APIキーが設定されていません。"

    # 要約するレビューの数を制限
    reviews_to_summarize = reviews[:max_reviews]

    # レビューテキストの抽出
    review_texts = []
    for review in reviews_to_summarize:
        rating = review.get("rating", "評価なし")
        text = review.get("text", "").strip()
        if text:
            review_texts.append(f"評価: {rating}★\n{text}")

    if not review_texts:
        return "有効な口コミがありません。"

    # プロンプトの作成
    prompt = f"""
    あなたは日本のキャンプ場に詳しい専門家です。
    以下のキャンプ場の口コミを分析して、簡潔に要約してください。
    良い点と改善点を明確にし、このキャンプ場の特徴を3〜5つのポイントにまとめてください。
    
    口コミ:
    {"\n\n".join(review_texts)}
    
    要約形式:
    【良い点】
    - ポイント1
    - ポイント2
    ...
    
    【改善点・注意点】
    - ポイント1
    - ポイント2
    ...
    
    【総評】
    このキャンプ場の特徴と全体的な評価を2〜3文で。
    """

    try:
        # OpenAI APIを使用して要約を取得
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたは日本のキャンプ場に詳しい専門家です。"},
                {"role": "user", "content": prompt},
            ],
        )

        summary = response.choices[0].message.content
        return summary
    except Exception as e:
        return f"口コミの要約中にエラーが発生しました: {str(e)}"


def generate_campsite_recommendation(preferences, location=None):
    """
    ユーザーの好みに基づいてキャンプ場の推薦を生成する関数

    Args:
        preferences (str): ユーザーの好みや条件
        location (str, optional): 場所の指定（例: '東京', '北海道'）

    Returns:
        str: 推薦されたキャンプ場の情報
    """
    location_text = f"場所: {location}" if location else ""

    prompt = f"""
    あなたは日本のキャンプ場に詳しい専門家です。
    以下の条件に合うキャンプ場を3つ提案してください。
    それぞれのキャンプ場について、名前、場所、特徴、おすすめポイントを簡潔に説明してください。
    
    ユーザーの希望条件:
    {preferences}
    {location_text}
    
    回答形式:
    1. [キャンプ場名] - [場所]
       特徴: [簡潔な説明]
       おすすめポイント: [おすすめポイント]
    
    2. [キャンプ場名] - [場所]
       ...
    
    3. [キャンプ場名] - [場所]
       ...
    """

    try:
        # Gemini APIを使用して推薦を取得
        recommendation = get_gemini_response(prompt)
        return recommendation
    except Exception as e:
        return f"キャンプ場の推薦生成中にエラーが発生しました: {str(e)}"


def generate_campsite_plan(campsite_name, duration, group_type, preferences):
    """
    キャンプ場での滞在計画を生成する関数

    Args:
        campsite_name (str): キャンプ場の名前
        duration (str): 滞在期間（例: '1泊2日', '2泊3日'）
        group_type (str): グループタイプ（例: '家族', 'カップル', '友人'）
        preferences (str): その他の好みや条件

    Returns:
        str: 生成されたキャンプ計画
    """
    prompt = f"""
    あなたは日本のキャンプ場に詳しい専門家です。
    以下の条件に基づいて、{campsite_name}での{duration}のキャンプ計画を作成してください。
    
    条件:
    - 滞在期間: {duration}
    - グループ: {group_type}
    - 希望/条件: {preferences}
    
    回答形式:
    【1日目】
    - 午前: [アクティビティや行動の提案]
    - 午後: [アクティビティや行動の提案]
    - 夕方/夜: [アクティビティや行動の提案]
    
    【2日目】
    - 午前: [アクティビティや行動の提案]
    - 午後: [アクティビティや行動の提案]
    - 夕方/夜: [アクティビティや行動の提案]
    
    （3日目以降も同様に）
    
    【持ち物リスト】
    - 必須アイテム: [リスト]
    - あると便利なもの: [リスト]
    - 季節に応じたアイテム: [リスト]
    
    【おすすめのアクティビティ】
    - [アクティビティ1]: [簡単な説明]
    - [アクティビティ2]: [簡単な説明]
    - [アクティビティ3]: [簡単な説明]
    """

    try:
        # Gemini APIを使用して計画を取得
        plan = get_gemini_response(prompt)
        return plan
    except Exception as e:
        return f"キャンプ計画の生成中にエラーが発生しました: {str(e)}"


def generate_packing_list(camp_style, duration, season, group_type, special_needs=None):
    """
    キャンプの持ち物リストを生成する関数

    Args:
        camp_style (str): キャンプスタイル（例: 'テント', 'グランピング', 'オートキャンプ'）
        duration (str): 滞在期間（例: '1泊2日', '2泊3日'）
        season (str): 季節（例: '春', '夏', '秋', '冬'）
        group_type (str): グループタイプ（例: '家族', 'カップル', '友人'）
        special_needs (str, optional): 特別な要望や条件

    Returns:
        str: 生成された持ち物リスト
    """
    special_needs_text = f"\n特別な要望: {special_needs}" if special_needs else ""

    prompt = f"""
    あなたは日本のキャンプに詳しい専門家です。
    以下の条件に基づいて、キャンプの持ち物リストを作成してください。
    
    条件:
    - キャンプスタイル: {camp_style}
    - 滞在期間: {duration}
    - 季節: {season}
    - グループ: {group_type}{special_needs_text}
    
    回答形式:
    【必須アイテム】
    - カテゴリ1（シェルター・寝具など）
      * アイテム1
      * アイテム2
      ...
    
    - カテゴリ2（調理器具など）
      * アイテム1
      * アイテム2
      ...
    
    【あると便利なもの】
    - カテゴリ1
      * アイテム1
      * アイテム2
      ...
    
    【{season}のキャンプにおける注意点】
    - 注意点1
    - 注意点2
    ...
    
    【{group_type}向けの特別なアドバイス】
    - アドバイス1
    - アドバイス2
    ...
    """

    try:
        # Gemini APIを使用して持ち物リストを取得
        packing_list = get_gemini_response(prompt)
        return packing_list
    except Exception as e:
        return f"持ち物リストの生成中にエラーが発生しました: {str(e)}"
