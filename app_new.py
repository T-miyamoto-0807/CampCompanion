import streamlit as st
import os
from dotenv import load_dotenv
import pandas as pd
import folium
from streamlit_folium import folium_static
from utils.gemini_api import search_campsites_gemini, analyze_campsite_reviews
from utils.places_api_new import search_campsites_new, get_place_details_new, convert_places_to_app_format_new
from utils.places_gemini_api import search_campsites_places_gemini
from utils.integrated_search import search_campsites_integrated, enhance_search_results
from utils.query_analyzer import analyze_query
from utils.search_evaluator import evaluate_search_results, generate_search_summary
from utils.parallel_search import search_and_analyze
from components.results_display import render_results
from components.map_display import display_map
import time
import urllib.parse

# 環境変数の読み込み
load_dotenv()

# デバッグモードの設定
DEBUG = True  # デバッグモードを強制的に有効化

# ページ設定
st.set_page_config(
    page_title="CampCompanion - キャンプ場検索",
    page_icon="🏕️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSSスタイルの適用
st.markdown(
    """
    <style>
    .main {
        padding: 2rem;
        background-color: #f8f9fa;
    }
    .stApp {
        background-color: #f8f9fa;
    }
    h1, h2, h3 {
        color: #2c3e50;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 0.5rem 1rem;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .chat-message.user {
        background-color: #e6f3ff;
        border-left: 5px solid #2196F3;
    }
    .chat-message.assistant {
        background-color: #f0f0f0;
        border-left: 5px solid #4CAF50;
    }
    .message-content {
        margin-top: 0.5rem;
    }
    .sidebar .stButton>button {
        width: 100%;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# キャンプ場カードを表示する関数
def display_campsite_card(campsite):
    """キャンプ場のカード表示を行う関数"""
    # キャンプ場名
    st.markdown(f"### {campsite.get('name', '不明なキャンプ場')}")

    # 画像の表示
    try:
        image_url = campsite.get("image_url", "")
        default_image = "https://placehold.jp/24/3d4070/ffffff/300x200.png?text=No%20Image"

        if image_url:
            st.image(image_url, use_column_width=True)
        else:
            st.image(default_image, use_column_width=True)
    except Exception as e:
        if DEBUG:
            print(f"画像表示エラー: {str(e)}")
        st.image(default_image, use_column_width=True)

    # 評価と口コミ数
    rating = campsite.get("rating", 0)
    reviews_count = campsite.get("reviews_count", 0)
    if rating > 0:
        st.markdown(f"⭐ **{rating}** ({reviews_count}件の口コミ)")

    # 住所（短縮表示）
    address = campsite.get("address", "")
    if address:
        short_address = address[:30] + "..." if len(address) > 30 else address
        st.markdown(f"📍 {short_address}")

    # 詳細ボタン
    if st.button("詳細を見る", key=f"btn_{campsite.get('place_id', '')}"):
        st.session_state.selected_campsite = campsite
        st.rerun()


# キャンプ場の詳細を表示する関数
def display_campsite_details(campsite):
    """キャンプ場の詳細情報を表示する関数"""
    # キャンプ場の基本情報
    col1, col2 = st.columns([1, 2])

    with col1:
        # 写真の表示
        try:
            photo_urls = campsite.get("photo_urls", [])
            image_url = campsite.get("image_url", "")
            default_image = "https://placehold.jp/24/3d4070/ffffff/300x200.png?text=No%20Image"

            if DEBUG:
                print(f"写真URL: {photo_urls}")
                print(f"メイン画像URL: {image_url}")

            # 写真がある場合は表示
            if photo_urls and len(photo_urls) > 0:
                try:
                    # 複数の写真がある場合はスライダーで表示
                    if len(photo_urls) > 1:
                        # スライダーのタイトル
                        st.write("📷 写真ギャラリー")

                        # スライダーで選択した写真のインデックス
                        photo_index = st.slider(
                            "写真を選択",
                            0,
                            len(photo_urls) - 1,
                            0,
                            key=f"photo_slider_{campsite.get('place_id', '')}",
                        )

                        # 選択した写真を表示
                        try:
                            st.image(photo_urls[photo_index], use_column_width=True)
                            if DEBUG:
                                print(f"写真表示成功 ({photo_index + 1}/{len(photo_urls)}枚目)")
                        except Exception as e:
                            if DEBUG:
                                print(f"写真表示エラー: {str(e)}")
                            st.image(default_image, use_column_width=True)

                        # 写真の枚数を表示
                        st.caption(f"{photo_index + 1} / {len(photo_urls)} 枚目")
                    else:
                        # 1枚だけの場合は通常表示
                        st.image(photo_urls[0], use_column_width=True)
                        if DEBUG:
                            print(f"写真表示成功 (1枚のみ)")
                except Exception as e:
                    if DEBUG:
                        print(f"写真表示エラー: {str(e)}")
                    st.image(default_image, use_column_width=True)
            # メイン画像がある場合は表示
            elif image_url:
                try:
                    st.image(image_url, use_column_width=True)
                    if DEBUG:
                        print(f"メイン画像表示成功")
                except Exception as e:
                    if DEBUG:
                        print(f"メイン画像表示エラー: {str(e)}")
                    st.image(default_image, use_column_width=True)
            else:
                # 画像がない場合はデフォルト画像を表示
                st.image(default_image, use_column_width=True)
        except Exception as e:
            if DEBUG:
                print(f"写真表示全体エラー: {str(e)}")
            st.image(default_image, use_column_width=True)

        # ウェブサイトへのリンク
        website = campsite.get("website", "")
        if website:
            st.markdown(f"[🌐 公式サイトを見る]({website})")

    with col2:
        # 評価と口コミ数
        rating = campsite.get("rating", 0)
        reviews_count = campsite.get("reviews_count", 0)
        if rating > 0:
            st.markdown(f"### ⭐ {rating} ({reviews_count}件の口コミ)")

        # 住所
        address = campsite.get("address", "")
        if address:
            # Google Mapsへのリンクを作成
            maps_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(address)}"
            st.markdown(f"**📍 住所**: [{address}]({maps_url})")

        # 説明文
        description = campsite.get("description", "")
        if description:
            st.markdown(f"**📝 説明**:\n{description}")

        # 施設
        facilities = campsite.get("facilities", [])
        if facilities:
            st.markdown("**🚿 施設**:")
            st.markdown(", ".join([f"`{facility}`" for facility in facilities]))

        # 特徴
        features = campsite.get("features", [])
        if features:
            st.markdown("**✨ 特徴**:")
            st.markdown(", ".join([f"`{feature}`" for feature in features]))

        # AIのおすすめポイント
        ai_recommendation = campsite.get("ai_recommendation", "")
        if ai_recommendation:
            st.markdown(f"**🤖 AIのおすすめポイント**:\n{ai_recommendation}")

        # 口コミの分析
        review_summary = campsite.get("review_summary", "")
        if review_summary:
            st.markdown(f"**👥 口コミの分析**:\n{review_summary}")


def display_search_results():
    """検索結果を表示する関数"""
    # 検索が実行されていない場合は何も表示しない
    if "search_executed" not in st.session_state or not st.session_state.search_executed:
        return

    # 検索結果を取得
    search_results = st.session_state.campsites
    search_summary = st.session_state.summary
    featured_campsites = st.session_state.featured
    popular_campsites = st.session_state.popular

    # 検索結果がない場合
    if not search_results:
        st.warning("条件に合うキャンプ場が見つかりませんでした。検索条件を変更してお試しください。")
        return

    # 検索結果の要約を表示
    st.subheader("🔍 検索結果の要約")
    st.write(search_summary)

    # 特集キャンプ場を表示
    if featured_campsites:
        st.subheader("✨ おすすめキャンプ場")
        cols = st.columns(min(len(featured_campsites), 3))
        for i, campsite in enumerate(featured_campsites[:3]):
            with cols[i]:
                display_campsite_card(campsite)

    # 人気キャンプ場を表示
    if popular_campsites:
        st.subheader("🔥 人気のキャンプ場")
        cols = st.columns(min(len(popular_campsites), 3))
        for i, campsite in enumerate(popular_campsites[:3]):
            with cols[i]:
                display_campsite_card(campsite)

    # すべての検索結果を表示
    st.subheader(f"🏕️ すべてのキャンプ場 ({len(search_results)}件)")

    # 検索結果をソート
    sort_option = st.selectbox(
        "並び替え:",
        ["おすすめ順", "評価の高い順", "口コミの多い順", "名前順"],
        index=0,
    )

    # ソートオプションに基づいて検索結果をソート
    if sort_option == "おすすめ順":
        sorted_results = sorted(search_results, key=lambda x: x.get("score", 0), reverse=True)
    elif sort_option == "評価の高い順":
        sorted_results = sorted(search_results, key=lambda x: x.get("rating", 0), reverse=True)
    elif sort_option == "口コミの多い順":
        sorted_results = sorted(search_results, key=lambda x: x.get("reviews_count", 0), reverse=True)
    elif sort_option == "名前順":
        sorted_results = sorted(search_results, key=lambda x: x.get("name", ""))
    else:
        sorted_results = search_results

    # 検索結果を表示
    for i, campsite in enumerate(sorted_results):
        with st.expander(
            f"{i+1}. {campsite.get('name', '不明なキャンプ場')} - ⭐ {campsite.get('rating', 0)}/5.0 ({campsite.get('reviews_count', 0)}件の口コミ)"
        ):
            display_campsite_details(campsite)


# セッション状態の初期化
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "こんにちは！CampCompanionへようこそ。理想のキャンプ場を探すお手伝いをします。どんなキャンプ場をお探しですか？例えば「富士山が見える静かなキャンプ場を教えて」「ペット可で設備が充実したキャンプ場は？」などと質問してください。",
        }
    ]

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "campsites" not in st.session_state:
    st.session_state.campsites = []

if "search_performed" not in st.session_state:
    st.session_state.search_performed = False

if "show_results" not in st.session_state:
    st.session_state.show_results = False

if "search_in_progress" not in st.session_state:
    st.session_state.search_in_progress = False

if "current_progress" not in st.session_state:
    st.session_state.current_progress = ""

if "summary" not in st.session_state:
    st.session_state.summary = ""

if "featured" not in st.session_state:
    st.session_state.featured = []

if "popular" not in st.session_state:
    st.session_state.popular = []

# サイドバー
with st.sidebar:
    st.title("🏕️ 検索設定")

    # ユーザータイプの選択
    st.subheader("利用スタイル")
    user_type = st.radio(
        "どのような利用スタイルをお考えですか？",
        ["指定なし", "ソロキャンプ", "カップル", "ファミリー", "グループ"],
        index=0,
    )

    # 検索履歴をクリアするボタン
    if st.button("会話をリセット"):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "こんにちは！CampCompanionへようこそ。理想のキャンプ場を探すお手伝いをします。どんなキャンプ場をお探しですか？例えば「富士山が見える静かなキャンプ場を教えて」「ペット可で設備が充実したキャンプ場は？」などと質問してください。",
            }
        ]
        st.session_state.campsites = []
        st.session_state.search_performed = False
        st.session_state.current_progress = ""
        st.session_state.show_results = False
        st.rerun()

# チャット履歴の表示
for message in st.session_state.messages:
    with st.container():
        st.markdown(
            f"""
        <div class="chat-message {message['role']}">
            <div><strong>{'🧑‍💻 あなた' if message['role'] == 'user' else '🤖 CampCompanion AI'}</strong></div>
            <div class="message-content">{message['content']}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

# 検索進捗状況の表示
if (
    "search_in_progress" in st.session_state
    and st.session_state.search_in_progress
    and "current_progress" in st.session_state
):
    # デバッグ出力
    if DEBUG:
        print(f"\n===== 進捗状況の表示 =====")
        print(f"current_progress = '{st.session_state.current_progress}'")

    # 最後のメッセージがアシスタントのものであれば更新
    if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "assistant":
        # 最後のメッセージを更新
        st.session_state.messages[-1]["content"] = st.session_state.current_progress
        if DEBUG:
            print(f"最後のアシスタントメッセージを更新しました: '{st.session_state.current_progress}'")
    else:
        # 新しいアシスタントメッセージを追加
        st.session_state.messages.append({"role": "assistant", "content": st.session_state.current_progress})
        if DEBUG:
            print(f"新しいアシスタントメッセージを追加しました: '{st.session_state.current_progress}'")

    # 検索処理の実行
    if "search_executed" not in st.session_state or not st.session_state.search_executed:
        # デバッグ出力
        if DEBUG:
            print(f"\n===== 検索処理の実行 =====")
            print(f"search_in_progress = {st.session_state.search_in_progress}")
            print(f"search_query = {st.session_state.get('search_query', 'なし')}")

        # 検索実行フラグをセット
        st.session_state.search_executed = True

        try:
            # 最後のユーザー入力を取得
            user_input = st.session_state.get("search_query", "")
            if not user_input:
                if len(st.session_state.messages) >= 2 and st.session_state.messages[-2]["role"] == "user":
                    user_input = st.session_state.messages[-2]["content"]
                    if DEBUG:
                        print(f"ユーザー入力を取得: '{user_input}'")
                else:
                    # ユーザー入力がない場合は処理を中止
                    if DEBUG:
                        print("ユーザー入力が見つかりません")
                    st.error("検索クエリが見つかりません。もう一度お試しください。")
                    st.session_state.search_in_progress = False
                    st.session_state.search_executed = False
                    st.rerun()

            # 入力を解析して検索クエリを構築
            query = user_input

            # 利用スタイルを検索クエリに反映
            if user_type != "指定なし":
                # 既存のクエリに利用スタイルを追加
                query = f"{query} {user_type}向け"
                if DEBUG:
                    print(f"利用スタイルを反映したクエリ: '{query}'")

            # クエリを解析して検索意図を抽出
            if DEBUG:
                print(f"クエリを解析します: '{query}'")
            query_analysis = analyze_query(query)
            st.session_state.query_analysis = query_analysis
            if DEBUG:
                print(f"クエリ解析結果: {query_analysis}")

            # サイドバーの設定を反映
            preferences = {}
            facilities_required = []

            # 利用スタイルに基づく設定
            if user_type == "ソロキャンプ":
                preferences["静かな環境"] = 8
                preferences["プライバシー"] = 7
                preferences["ソロサイト"] = 9
                preferences["シャワー"] = 6
                preferences["電源"] = 6
            elif user_type == "カップル":
                preferences["景色が良い"] = 8
                preferences["プライバシー"] = 7
                preferences["温泉"] = 6
                preferences["シャワー"] = 6
                preferences["電源"] = 6
            elif user_type == "ファミリー":
                preferences["子供向け"] = 9
                preferences["遊具"] = 8
                preferences["安全"] = 7
                preferences["広いサイト"] = 6
                preferences["シャワー"] = 7
                preferences["電源"] = 7
                preferences["Wi-Fi"] = 5
            elif user_type == "グループ":
                preferences["広いサイト"] = 9
                preferences["バーベキュー"] = 8
                preferences["団体利用"] = 7
                preferences["シャワー"] = 6
                preferences["電源"] = 6

            if DEBUG:
                print(f"利用スタイル: {user_type}")
                print(f"好み設定: {preferences}")
                print(f"必須施設: {facilities_required}")

            # 検索を実行
            with st.spinner("🔍 キャンプ場を検索中..."):
                if DEBUG:
                    print(f"\n===== AI統合検索を実行します =====")
                    print(f"検索クエリ: {query}")
                    print(f"ユーザータイプ: {user_type}")
                    print(f"必須施設: {facilities_required}")

                # 検索を実行
                search_results = search_and_analyze(query, preferences, facilities_required)

                if DEBUG:
                    print(f"検索結果: {len(search_results.get('results', []))}件")

                # 検索結果を保存
                st.session_state.campsites = search_results.get("results", [])
                st.session_state.summary = search_results.get("summary", "")
                st.session_state.featured = search_results.get("featured_campsites", [])
                st.session_state.popular = search_results.get("popular_campsites", [])

                # 検索完了フラグを設定
                st.session_state.search_performed = True
                st.session_state.show_results = True
                st.session_state.search_in_progress = False

                if DEBUG:
                    print(f"検索が完了しました")
                    print(f"キャンプ場: {len(st.session_state.campsites)}件")
                    print(f"おすすめキャンプ場: {len(st.session_state.featured)}件")
                    print(f"人気キャンプ場: {len(st.session_state.popular)}件")

        except Exception as e:
            # エラーが発生した場合
            if DEBUG:
                print(f"検索処理エラー: {str(e)}")
                import traceback

                print(traceback.format_exc())
            # エラーメッセージをチャットに表示
            error_message = "検索中にエラーが発生しました。もう一度お試しください。"
            st.session_state.messages.append({"role": "assistant", "content": error_message})
            # 検索フラグをリセット
            st.session_state.search_in_progress = False
            st.session_state.search_executed = False
            st.rerun()

    # 自動更新（0.5秒ごと）
    time.sleep(0.5)
    st.rerun()

# ユーザー入力
user_input = st.chat_input("キャンプ場について質問してください...")

# ユーザーからの入力があった場合の処理
if user_input:
    # デバッグ出力
    if DEBUG:
        print(f"\n===== ユーザー入力: '{user_input}' =====")
        print("検索処理を開始します...")

    # ユーザーのメッセージをチャット履歴に追加
    st.session_state.messages.append({"role": "user", "content": user_input})

    # 検索開始メッセージを表示
    start_message = "🔎 キャンプ場を検索中です。少々お待ちください..."
    st.session_state.messages.append({"role": "assistant", "content": start_message})

    # 検索フラグをセット
    st.session_state.search_in_progress = True
    st.session_state.search_query = user_input

    # 検索実行フラグをリセット
    if "search_executed" in st.session_state:
        st.session_state.search_executed = False

    # 進捗状況の初期化
    st.session_state.current_progress = start_message

    # デバッグ出力
    if DEBUG:
        print(f"検索フラグをセット: search_in_progress = {st.session_state.search_in_progress}")
        print(f"検索実行フラグをリセット: search_executed = {st.session_state.get('search_executed', False)}")
        print(f"進捗状況を初期化: current_progress = '{st.session_state.current_progress}'")

    # 画面を更新して検索開始メッセージを表示
    st.rerun()

# 検索結果を表示（検索実行後）
if st.session_state.search_performed and st.session_state.campsites and st.session_state.show_results:
    # 検索結果がある場合
    if st.session_state.campsites:
        # 検索結果のタブを作成
        tab1, tab2 = st.tabs(["📋 検索結果", "🗺️ 地図"])

        with tab1:
            # 検索結果の表示
            display_search_results()

        with tab2:
            # 地図表示
            display_map(st.session_state.campsites)


# 検索実行関数
def execute_search():
    """検索を実行する関数"""
    # 検索クエリを取得
    query = st.session_state.search_query if "search_query" in st.session_state else ""

    # ユーザーの好み設定を取得
    preferences = {}
    if "preferences" in st.session_state:
        preferences = st.session_state.preferences

    # 必須施設を取得
    facilities_required = []
    if "facilities_required" in st.session_state:
        facilities_required = st.session_state.facilities_required

    # 検索クエリが空の場合は何もしない
    if not query:
        st.warning("検索クエリを入力してください。")
        return

    # 検索を実行
    with st.spinner("キャンプ場を検索しています..."):
        # 検索実行
        search_result = search_and_analyze(query, preferences, facilities_required)

        # 検索結果を表示
        if search_result.get("success", False):
            st.success(search_result.get("message", "検索が完了しました！"))
        else:
            st.error(search_result.get("message", "検索中にエラーが発生しました。"))


# メイン関数
def main():
    """メイン関数"""
    # メインコンテンツ
    st.title("🏕️ Camp Companion")
    st.subheader("自然の中での最高の体験を見つけよう！")

    # 進捗状況を表示
    if "current_progress" in st.session_state:
        progress_message = st.session_state.current_progress
        if progress_message:
            st.info(progress_message)

    # 検索結果を表示
    display_search_results()


# アプリケーションの実行
if __name__ == "__main__":
    main()
