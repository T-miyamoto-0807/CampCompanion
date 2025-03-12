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
from utils.web_search import search_related_articles as web_search_articles
from utils.api_config import load_streamlit_secrets, DEBUG
from components.results_display import render_results
from components.map_display import display_map
import time
import urllib.parse
import asyncio
import threading
import concurrent.futures
import queue

# StreamlitCloudの環境変数設定
load_streamlit_secrets()

# ローカル環境変数の読み込み
load_dotenv()

# デバッグ情報の表示
if DEBUG:
    print("環境変数の設定:")
    print(f"GEMINI_API_KEY: {'設定済み' if 'GEMINI_API_KEY' in os.environ else '未設定'}")
    print(f"OPENAI_API_KEY: {'設定済み' if 'OPENAI_API_KEY' in os.environ else '未設定'}")
    print(f"GOOGLE_CSE_ID: {'設定済み' if 'GOOGLE_CSE_ID' in os.environ else '未設定'}")
    print(f"GOOGLE_API_KEY: {'設定済み' if 'GOOGLE_API_KEY' in os.environ else '未設定'}")
    print(f"GOOGLE_PLACE_API_KEY: {'設定済み' if 'GOOGLE_PLACE_API_KEY' in os.environ else '未設定'}")
    print(f"MAPBOX_TOKEN: {'設定済み' if 'MAPBOX_TOKEN' in os.environ else '未設定'}")
    print(f"DEBUG: {DEBUG}")

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

# スレッド間通信用のグローバル変数
global_progress_queue = queue.Queue()

# セッション状態の初期化
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "こんにちは！CampCompanionへようこそ。理想のキャンプ場を探すお手伝いをします。どんなキャンプ場をお探しですか？例えば「富士山が見える静かなキャンプ場を教えて」「ペット可で設備が充実したキャンプ場は？」などと質問してください。",
        }
    ]

if "campsites" not in st.session_state:
    st.session_state.campsites = []

if "search_performed" not in st.session_state:
    st.session_state.search_performed = False

if "show_results" not in st.session_state:
    st.session_state.show_results = False

if "current_progress" not in st.session_state:
    st.session_state.current_progress = None

if "search_in_progress" not in st.session_state:
    st.session_state.search_in_progress = False

if "summary" not in st.session_state:
    st.session_state.summary = None

if "featured" not in st.session_state:
    st.session_state.featured = None

if "popular" not in st.session_state:
    st.session_state.popular = None

# スレッド間通信用のキュー - この行は機能しないので、グローバル変数を使用
if "progress_queue" not in st.session_state:
    st.session_state.progress_queue = global_progress_queue  # 実際のキューオブジェクトを設定

# グローバル変数を参照
progress_queue = global_progress_queue

if "search_results" not in st.session_state:
    st.session_state.search_results = None

if "search_executed" not in st.session_state:
    st.session_state.search_executed = False

if "search_summary" not in st.session_state:
    st.session_state.search_summary = None

if "featured_campsites" not in st.session_state:
    st.session_state.featured_campsites = None

if "popular_campsites" not in st.session_state:
    st.session_state.popular_campsites = None

if "last_query" not in st.session_state:
    st.session_state.last_query = None

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
        st.session_state.current_progress = None
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
if "search_in_progress" in st.session_state and st.session_state.search_in_progress:
    # 進捗キューからメッセージを取得
    try:
        # キューにメッセージがあれば取得（ブロックしない）
        if "progress_queue" in st.session_state and st.session_state.progress_queue is not None:
            while not st.session_state.progress_queue.empty():
                progress_message = st.session_state.progress_queue.get(block=False)
                st.session_state.current_progress = progress_message

                # デバッグ出力
                if DEBUG:
                    print(f"\n===== 進捗状況の更新 =====")
                    print(f"current_progress = '{progress_message}'")

                # 最後のメッセージがアシスタントのものであれば更新
                if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "assistant":
                    # 最後のメッセージを更新
                    st.session_state.messages[-1]["content"] = progress_message
                    if DEBUG:
                        print(f"最後のアシスタントメッセージを更新しました: '{progress_message}'")
                else:
                    # 新しいアシスタントメッセージを追加
                    st.session_state.messages.append({"role": "assistant", "content": progress_message})
                    if DEBUG:
                        print(f"新しいアシスタントメッセージを追加しました: '{progress_message}'")
    except queue.Empty:
        pass

    # 検索結果が準備できているか確認
    if st.session_state.search_results is not None:
        # 検索結果を処理
        search_results = st.session_state.search_results

        # 検索結果を保存
        st.session_state.campsites = search_results.get("results", [])
        st.session_state.summary = search_results.get("summary", "")
        st.session_state.featured = search_results.get("featured_campsites", [])
        st.session_state.popular = search_results.get("popular_campsites", [])
        st.session_state.search_executed = True
        st.session_state.search_in_progress = False

        # 検索完了フラグを設定
        st.session_state.search_performed = True
        st.session_state.show_results = True
        st.session_state.search_results = None

        if DEBUG:
            print(f"検索が完了しました")
            print(f"キャンプ場: {len(st.session_state.campsites)}件")
            print(f"おすすめキャンプ場: {len(st.session_state.featured)}件")
            print(f"人気キャンプ場: {len(st.session_state.popular)}件")

            # 写真URLと口コミ分析の確認
            if st.session_state.campsites:
                first_campsite = st.session_state.campsites[0]
                print(f"最初のキャンプ場: {first_campsite.get('name')}")
                print(f"写真URL: {first_campsite.get('photo_urls', [])[:1]}")
                print(f"メイン画像URL: {first_campsite.get('image_url', 'なし')}")
                print(f"AIおすすめ: {first_campsite.get('ai_recommendation', 'なし')[:50]}...")
                print(f"口コミ分析: {first_campsite.get('review_summary', 'なし')[:50]}...")

        # 再描画
        st.rerun()

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

            # 検索状態を設定
            st.session_state.search_in_progress = True
            st.session_state.search_executed = False

            # 検索クエリを保存
            st.session_state.search_query = user_input

            # 進捗状況を明示的に設定
            st.session_state.current_progress = "キャンプ場を検索しています..."

            # 進捗状況の初期化
            start_message = "🔎 キャンプ場を検索中です。少々お待ちください..."
            st.session_state.current_progress = start_message

            # 検索を同期的に実行
            try:
                # 進捗状況を報告する関数
                def report_progress(message):
                    try:
                        # セッション状態ではなくグローバル変数のキューを使用
                        global_progress_queue.put(message)
                        st.session_state.current_progress = message
                        if DEBUG:
                            print(f"進捗状況をキューに追加: '{message}'")
                    except Exception as e:
                        if DEBUG:
                            print(f"進捗報告エラー: {str(e)}")

                # 検索モジュールの関数をオーバーライド
                import utils.parallel_search

                utils.parallel_search.report_progress = report_progress

                # 初期進捗状況
                report_progress("🔍 キャンプ場を検索中...")

                # 検索を実行（同期的に）
                with st.spinner("キャンプ場を検索しています..."):
                    search_results = utils.parallel_search.search_and_analyze(query, preferences, facilities_required)

                    # 検索結果をセッション状態に設定
                    st.session_state.search_results = search_results
                    st.session_state.campsites = search_results.get("results", [])
                    st.session_state.summary = search_results.get("summary", "")
                    st.session_state.featured = search_results.get("featured_campsites", [])
                    st.session_state.popular = search_results.get("popular_campsites", [])
                    st.session_state.search_executed = True
                    st.session_state.search_in_progress = False

                    # 完了メッセージ
                    report_progress(
                        f"✅ 検索が完了しました！{len(search_results.get('results', []))}件のキャンプ場が見つかりました。AIで分析しておすすめのキャンプ場をピックアップします！"
                    )

                    if DEBUG:
                        print(f"検索完了: {len(st.session_state.campsites)}件のキャンプ場が見つかりました")
                        print(f"特集キャンプ場: {len(st.session_state.featured)}件")
                        print(f"人気キャンプ場: {len(st.session_state.popular)}件")

                        # 写真URLと口コミ分析の確認
                        if st.session_state.campsites:
                            first_campsite = st.session_state.campsites[0]
                            print(f"最初のキャンプ場: {first_campsite.get('name')}")
                            print(f"写真URL: {first_campsite.get('photo_urls', [])[:1]}")
                            print(f"メイン画像URL: {first_campsite.get('image_url', 'なし')}")
                            print(f"AIおすすめ: {first_campsite.get('ai_recommendation', 'なし')[:50]}...")
                            print(f"口コミ分析: {first_campsite.get('review_summary', 'なし')[:50]}...")

                # 検索結果を表示するために画面を更新
                st.rerun()

            except Exception as e:
                # エラーが発生した場合
                print(f"検索処理エラー: {str(e)}")
                import traceback

                print(traceback.format_exc())

                # エラーメッセージを報告
                try:
                    if "progress_queue" in st.session_state and st.session_state.progress_queue is not None:
                        st.session_state.progress_queue.put(f"❌ 検索中にエラーが発生しました: {str(e)}")
                        st.session_state.search_in_progress = False
                        st.session_state.search_executed = False
                except:
                    pass

                # エラーメッセージをチャットに表示
                error_message = "検索中にエラーが発生しました。もう一度お試しください。"
                st.session_state.messages.append({"role": "assistant", "content": error_message})
                st.rerun()

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

    # 検索結果を表示（検索実行後）
    if st.session_state.search_performed and st.session_state.campsites and st.session_state.show_results:
        # 検索結果がある場合
        if st.session_state.campsites:
            # 検索結果のタブを作成
            tab1, tab2, tab3 = st.tabs(["📋 検索結果", "🗺️ 地図", "📚 関連記事"])

            with tab1:
                # 検索結果の表示
                display_search_results()

            with tab2:
                # 地図表示
                display_map(st.session_state.campsites)

            with tab3:
                # 関連記事の表示
                st.subheader("📚 関連記事・特集")
                st.write("検索内容に関連する特集記事やまとめ記事です。参考にしてキャンプ計画を立ててみましょう。")

                # 関連記事を取得
                if "search_query" in st.session_state:
                    query = st.session_state.search_query

                    with st.spinner("関連記事を検索中..."):
                        # 関連記事を検索
                        related_articles = search_related_articles(query)

                    # 関連記事を表示
                    if related_articles:
                        # 記事カードのスタイル
                        st.markdown(
                            """
                        <style>
                        .article-card {
                            border: 1px solid #ddd;
                            border-radius: 5px;
                            padding: 10px;
                            margin-bottom: 10px;
                            background-color: #f9f9f9;
                        }
                        .article-title {
                            font-size: 18px;
                            font-weight: bold;
                            margin-bottom: 5px;
                        }
                        .article-source {
                            color: #666;
                            font-size: 14px;
                            margin-bottom: 10px;
                        }
                        .article-summary {
                            margin-bottom: 10px;
                        }
                        </style>
                        """,
                            unsafe_allow_html=True,
                        )

                        for i, article in enumerate(related_articles):
                            # Expanderのタイトルを短くして見やすくする
                            title_display = article["title"]
                            if len(title_display) > 60:
                                title_display = title_display[:57] + "..."

                            with st.expander(f"{title_display}", expanded=i == 0):
                                # 記事タイトルを完全に表示（Expander内）
                                st.markdown(f"### {article['title']}")
                                st.markdown(f"**出典**: {article['source']}")

                                # 要約を表示（テキストエリアで表示して見切れないようにする）
                                st.markdown("**要約**:")
                                # テキストエリアを使用して長いテキストを表示（高さを調整）
                                summary_text = article["summary"]
                                st.text_area("", summary_text, height=200, label_visibility="collapsed")

                                # 公開日があれば表示
                                if "published_date" in article:
                                    try:
                                        # 日付形式を整形
                                        from datetime import datetime

                                        date_obj = datetime.fromisoformat(
                                            article["published_date"].replace("Z", "+00:00")
                                        )
                                        formatted_date = date_obj.strftime("%Y年%m月%d日")
                                        st.markdown(f"**公開日**: {formatted_date}")
                                    except:
                                        pass

                                # リンクボタン
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.markdown(f"[🔗 記事を読む]({article['url']})")
                                with col2:
                                    st.markdown(
                                        f"[🔍 Googleで検索](https://www.google.com/search?q={urllib.parse.quote(article['title'])})"
                                    )
                    else:
                        st.info(f"「{query}」に関連する記事が見つかりませんでした。")
                else:
                    st.warning("条件に合うキャンプ場が見つかりませんでした。検索条件を変更してお試しください。")

    # 入力欄を最下層に固定表示するためのスタイル
    st.markdown(
        """
        <style>
        .fixed-input {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            padding: 1rem;
            background-color: white;
            box-shadow: 0px -2px 10px rgba(0, 0, 0, 0.1);
            z-index: 1000;
        }
        .main .block-container {
            padding-bottom: 5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 空のスペースを追加して、固定入力欄の下に余白を作る
    st.markdown("<div style='height: 3rem;'></div>", unsafe_allow_html=True)

    # 固定入力欄のコンテナ
    with st.container():
        st.markdown("<div class='fixed-input'>", unsafe_allow_html=True)
        # ユーザー入力
        user_input = st.chat_input("キャンプ場について質問してください...")
        st.markdown("</div>", unsafe_allow_html=True)

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

            # 検索状態を設定
            st.session_state.search_in_progress = True
            st.session_state.search_executed = False

            # 検索クエリを保存
            st.session_state.search_query = user_input

            # 進捗状況を明示的に設定
            st.session_state.current_progress = "キャンプ場を検索しています..."

            # 進捗状況の初期化
            st.session_state.current_progress = start_message

            # 進捗キューをクリア
            try:
                while not global_progress_queue.empty():
                    global_progress_queue.get()
                if DEBUG:
                    print("進捗キューをクリアしました")
            except Exception as e:
                if DEBUG:
                    print(f"進捗キュークリアエラー: {str(e)}")

            # 画面を更新して検索開始メッセージを表示
            st.rerun()


# キャンプ場カードを表示する関数
def display_campsite_card(campsite, index=None):
    """キャンプ場のカード表示を行う関数"""
    # 画像の表示
    try:
        # 写真の取得
        photo_urls = campsite.get("photo_urls", [])
        image_url = campsite.get("image_url", "")
        default_image = "https://placehold.jp/24/3d4070/ffffff/300x200.png?text=No%20Image"

        if DEBUG:
            print(f"キャンプ場カード表示: {campsite.get('name')}")
            print(f"写真URL: {image_url[:50] if image_url else 'なし'}")
            print(f"写真枚数: {len(photo_urls)}")

        # メイン画像の表示
        if image_url:
            st.image(image_url, use_column_width=True)
        else:
            st.image(default_image, use_column_width=True)

        # 追加の写真がある場合は横に並べて表示
        if len(photo_urls) > 1:
            st.write("📸 その他の写真")
            # 写真を2行3列で表示（最大6枚）
            if len(photo_urls) > 1:
                rows = 2
                cols_per_row = 3
                for row in range(rows):
                    photo_cols = st.columns(cols_per_row)
                    for col in range(cols_per_row):
                        idx = row * cols_per_row + col + 1  # メイン画像を除く
                        if idx < len(photo_urls):
                            with photo_cols[col]:
                                st.image(photo_urls[idx], width=150)
    except Exception as e:
        if DEBUG:
            print(f"画像表示エラー: {str(e)}")
        st.image("https://placehold.jp/24/3d4070/ffffff/300x200.png?text=No%20Image", use_column_width=True)

    # 評価
    rating = campsite.get("rating", 0)
    reviews_count = campsite.get("reviews_count", 0)
    st.write(f"⭐ {rating}/5.0 ({reviews_count}件の口コミ)")

    # 住所
    address = campsite.get("address", "")
    if address:
        st.write(f"📍 {address}")

    # リンク
    col1, col2 = st.columns(2)
    with col1:
        google_maps_url = campsite.get("googleMapsUri", "") or campsite.get("google_maps_url", "")
        if google_maps_url:
            st.markdown(f"[🗺️ Google Mapで見る]({google_maps_url})")
        elif DEBUG:
            st.write("Google Mapリンクなし")
            print(f"Google Mapリンクなし: {campsite.get('name')}")
            print(f"キャンプ場データキー: {campsite.keys()}")

    with col2:
        website_url = campsite.get("websiteUri", "") or campsite.get("website_url", "")
        if website_url:
            st.markdown(f"[🌐 公式サイト]({website_url})")
        elif DEBUG:
            st.write("公式サイトリンクなし")
            print(f"公式サイトリンクなし: {campsite.get('name')}")

    # AIのおすすめポイント
    ai_recommendation = campsite.get("ai_recommendation", "")
    if ai_recommendation:
        st.markdown("**🤖 AIのおすすめポイント:**")
        st.write(ai_recommendation)

    # 口コミの分析
    review_summary = campsite.get("review_summary", "")
    if review_summary:
        st.markdown("**👥 口コミの分析:**")
        st.write(review_summary)


# キャンプ場の詳細を表示する関数
def display_campsite_details(campsite, index=None):
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
            if image_url:
                st.image(image_url, use_column_width=True)
            else:
                st.image(default_image, use_column_width=True)

            # 複数の写真がある場合はギャラリー表示
            if len(photo_urls) > 1:
                st.write("📸 その他の写真")
                cols = st.columns(min(3, len(photo_urls) - 1))
                for i, url in enumerate(photo_urls[1:4]):  # 最大3枚まで表示
                    with cols[i % 3]:
                        st.image(url, use_column_width=True)
        except Exception as e:
            if DEBUG:
                print(f"画像表示エラー: {str(e)}")
            st.image(default_image, use_column_width=True)

    with col2:
        # 基本情報
        st.subheader(campsite.get("name", "不明なキャンプ場"))
        st.write(f"⭐ {campsite.get('rating', 0)}/5.0 ({campsite.get('reviews_count', 0)}件の口コミ)")

        # 住所
        address = campsite.get("address", "")
        if address:
            st.write(f"📍 {address}")

        # 電話番号
        phone = campsite.get("phone", "")
        if phone:
            st.write(f"📞 {phone}")

        # ウェブサイト
        website = campsite.get("website", "")
        if website:
            st.write(f"🌐 [ウェブサイト]({website})")

        # Google Mapsリンク
        maps_url = campsite.get("maps_url", "")
        if maps_url:
            st.write(f"🗺️ [Google Mapsで見る]({maps_url})")

    # 営業時間
    hours = campsite.get("opening_hours", [])
    if hours:
        st.subheader("⏰ 営業時間")
        for day, time in hours:
            st.write(f"**{day}**: {time}")

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
    elif DEBUG:
        print(f"AIのおすすめポイントがありません: {campsite.get('name')}")

        # 口コミの分析
        review_summary = campsite.get("review_summary", "")
        if review_summary:
            st.markdown(f"**👥 口コミの分析**:\n{review_summary}")
    elif DEBUG:
        print(f"口コミの分析がありません: {campsite.get('name')}")

    # デバッグ情報の表示
    if DEBUG:
        st.write("---")
        st.write("**デバッグ情報**")
        st.write(f"キャンプ場ID: {campsite.get('place_id', 'なし')}")
        st.write(f"写真URL数: {len(campsite.get('photo_urls', []))}")
        st.write(f"メイン画像URL: {campsite.get('image_url', 'なし')}")
        st.write(f"AIおすすめ: {'あり' if campsite.get('ai_recommendation') else 'なし'}")
        st.write(f"口コミ分析: {'あり' if campsite.get('review_summary') else 'なし'}")


# 検索実行関数
def execute_search():
    """検索を実行する関数"""
    # 検索クエリを取得
    query = st.session_state.search_input

    # 検索クエリをセッション状態に保存
    st.session_state.search_query = query

    if not query:
        st.warning("検索キーワードを入力してください")
        return

    # 検索中の表示
    with st.spinner("キャンプ場を検索中..."):
        # 検索を実行
        search_result = search_and_analyze(query)

        # 検索結果をセッション状態に保存
        if "results" in search_result:
            st.session_state.campsites = search_result["results"]
            st.session_state.summary = search_result.get("summary", "")
            st.session_state.featured = search_result.get("featured_campsites", [])
            st.session_state.popular = search_result.get("popular_campsites", [])
            st.session_state.search_executed = True

            if DEBUG:
                print(f"検索結果: {len(st.session_state.campsites)}件")
                print(f"特集キャンプ場: {len(st.session_state.featured)}件")
                print(f"人気キャンプ場: {len(st.session_state.popular)}件")
        else:
            st.error("検索結果の取得に失敗しました")
            return

    # 検索完了のメッセージ
    st.success(f"検索が完了しました！{len(st.session_state.campsites)}件のキャンプ場が見つかりました。")


def search_related_articles(query):
    """
    検索クエリに関連する記事を検索する関数

    Args:
        query (str): 検索クエリ

    Returns:
        list: 関連記事のリスト
    """
    try:
        if DEBUG:
            print(f"関連記事検索: クエリ='{query}'")

        # web_search.pyの関数を使用して関連記事を検索
        results = web_search_articles(query, max_results=5, enhance_summaries=True)
        return results

    except Exception as e:
        if DEBUG:
            print(f"関連記事検索エラー: {str(e)}")
        return []


def display_search_results():
    """検索結果を表示する関数"""
    # 検索が実行されていない場合は何も表示しない
    if "search_executed" not in st.session_state or not st.session_state.search_executed:
        if DEBUG:
            print("display_search_results: search_executed=False")
        return

    # 検索結果を取得
    search_results = st.session_state.campsites
    search_summary = st.session_state.summary
    featured_campsites = st.session_state.featured
    popular_campsites = st.session_state.popular

    if DEBUG:
        print(f"display_search_results: 検索結果={len(search_results)}件")
        print(f"display_search_results: サマリー={search_summary[:30]}...")
        print(f"display_search_results: 特集={len(featured_campsites)}件")
        print(f"display_search_results: 人気={len(popular_campsites)}件")

    # 検索結果がない場合
    if not search_results:
        st.warning("条件に合うキャンプ場が見つかりませんでした。検索条件を変更してお試しください。")
        return

    # タブを作成
    tab1, tab2, tab3 = st.tabs(["📋 キャンプ場情報", "🗺️ 地図表示", "📚 関連記事"])

    with tab1:
        # 検索結果の要約を表示
        st.subheader("🔍 検索結果の要約")
        st.write(search_summary)

        # 特集キャンプ場を表示
        if featured_campsites:
            st.markdown("## ✨ おすすめキャンプ場")
            for i, campsite in enumerate(featured_campsites[:3]):
                with st.expander(f"{i+1}. {campsite.get('name', '不明なキャンプ場')}", expanded=i == 0):
                    display_campsite_card(campsite, index=f"featured_{i}")

        # 人気キャンプ場を表示
        if popular_campsites:
            st.markdown("## 🔥 人気のキャンプ場")
            for i, campsite in enumerate(popular_campsites[:3]):
                with st.expander(f"{i+1}. {campsite.get('name', '不明なキャンプ場')}", expanded=False):
                    display_campsite_card(campsite, index=f"popular_{i}")

    with tab2:
        # 地図表示
        st.subheader("🗺️ キャンプ場の位置")
        st.write("キャンプ場の位置を地図上で確認できます。マーカーをクリックすると詳細情報が表示されます。")
        display_map(search_results)

    with tab3:
        # 関連記事の表示
        st.subheader("📚 関連記事・特集")
        st.write("検索内容に関連する特集記事やまとめ記事です。参考にしてキャンプ計画を立ててみましょう。")

        # 関連記事を取得
        if "search_query" in st.session_state:
            query = st.session_state.search_query

            with st.spinner("関連記事を検索中..."):
                # 関連記事を検索
                related_articles = search_related_articles(query)

            # 関連記事を表示
            if related_articles:
                # 記事カードのスタイル
                st.markdown(
                    """
                <style>
                .article-card {
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    padding: 10px;
                    margin-bottom: 10px;
                    background-color: #f9f9f9;
                }
                .article-title {
                    font-size: 18px;
                    font-weight: bold;
                    margin-bottom: 5px;
                }
                .article-source {
                    color: #666;
                    font-size: 14px;
                    margin-bottom: 10px;
                }
                .article-summary {
                    margin-bottom: 10px;
                }
                </style>
                """,
                    unsafe_allow_html=True,
                )

                for i, article in enumerate(related_articles):
                    # Expanderのタイトルを短くして見やすくする
                    title_display = article["title"]
                    if len(title_display) > 60:
                        title_display = title_display[:57] + "..."

                    with st.expander(f"{title_display}", expanded=i == 0):
                        # 記事タイトルを完全に表示（Expander内）
                        st.markdown(f"### {article['title']}")
                        st.markdown(f"**出典**: {article['source']}")

                        # 要約を表示（テキストエリアで表示して見切れないようにする）
                        st.markdown("**要約**:")
                        # テキストエリアを使用して長いテキストを表示（高さを調整）
                        summary_text = article["summary"]
                        st.text_area("", summary_text, height=200, label_visibility="collapsed")

                        # 公開日があれば表示
                        if "published_date" in article:
                            try:
                                # 日付形式を整形
                                from datetime import datetime

                                date_obj = datetime.fromisoformat(article["published_date"].replace("Z", "+00:00"))
                                formatted_date = date_obj.strftime("%Y年%m月%d日")
                                st.markdown(f"**公開日**: {formatted_date}")
                            except:
                                pass

                        # リンクボタン
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"[🔗 記事を読む]({article['url']})")
                        with col2:
                            st.markdown(
                                f"[🔍 Googleで検索](https://www.google.com/search?q={urllib.parse.quote(article['title'])})"
                            )
            else:
                st.info(f"「{query}」に関連する記事が見つかりませんでした。")
        else:
            st.info("検索クエリがありません。キャンプ場を検索すると、関連記事が表示されます。")


# メイン関数
def main():
    """メイン関数"""
    st.title("🏕️ CampCompanion")
    st.subheader("理想のキャンプ場を見つける旅へ")

    # 現在の進捗状況があれば表示
    try:
        # グローバル変数からキューを取得
        # キューにメッセージがあれば取得（ブロックしない）
        while not global_progress_queue.empty():
            try:
                progress_message = global_progress_queue.get(block=False)
                st.session_state.current_progress = progress_message
                if DEBUG:
                    print(f"進捗状況を更新: current_progress = '{progress_message}'")
            except Exception as e:
                if DEBUG:
                    print(f"キュー処理エラー: {str(e)}")
                break
    except Exception as e:
        if DEBUG:
            print(f"キュー処理エラー: {str(e)}")

    # 進捗状況を表示
    if "current_progress" in st.session_state and st.session_state.current_progress:
        progress_message = st.session_state.current_progress
        if progress_message:
            if "search_in_progress" in st.session_state and st.session_state.search_in_progress:
                with st.spinner(progress_message):
                    # 検索中はスピナーを表示し続ける
                    st.info(progress_message)
            else:
                # 検索が完了したらスピナーなしで表示
                st.info(progress_message)

    # 選択されたキャンプ場の詳細を表示
    if "selected_campsite" in st.session_state:
        st.subheader(f"🏕️ {st.session_state.selected_campsite.get('name', '不明なキャンプ場')}の詳細")
        display_campsite_details(st.session_state.selected_campsite, index="selected")

        # 戻るボタン
        if st.button("検索結果に戻る", key="back_to_results"):
            del st.session_state.selected_campsite
            st.rerun()
    else:
        # 検索結果を表示
        display_search_results()

    # 入力欄を最下層に固定表示するためのスタイル
    st.markdown(
        """
        <style>
        .fixed-input {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            padding: 1rem;
            background-color: white;
            box-shadow: 0px -2px 10px rgba(0, 0, 0, 0.1);
            z-index: 1000;
        }
        .main .block-container {
            padding-bottom: 5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 空のスペースを追加して、固定入力欄の下に余白を作る
    st.markdown("<div style='height: 3rem;'></div>", unsafe_allow_html=True)

    # 固定入力欄のコンテナ
    with st.container():
        st.markdown("<div class='fixed-input'>", unsafe_allow_html=True)
        # ユーザー入力
        user_input = st.chat_input("キャンプ場について質問してください...")
        st.markdown("</div>", unsafe_allow_html=True)

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

            # 検索状態を設定
            st.session_state.search_in_progress = True
            st.session_state.search_executed = False

            # 検索クエリを保存
            st.session_state.search_query = user_input

            # 進捗状況を明示的に設定
            st.session_state.current_progress = "キャンプ場を検索しています..."

            # 進捗状況の初期化
            st.session_state.current_progress = start_message

            # 進捗キューをクリア
            try:
                while not global_progress_queue.empty():
                    global_progress_queue.get()
                if DEBUG:
                    print("進捗キューをクリアしました")
            except Exception as e:
                if DEBUG:
                    print(f"進捗キュークリアエラー: {str(e)}")

            # 画面を更新して検索開始メッセージを表示
            st.rerun()


# アプリケーションの実行
if __name__ == "__main__":
    main()
