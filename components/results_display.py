import streamlit as st
import pandas as pd
import requests
from PIL import Image
from io import BytesIO
import os


def render_results(campsites):
    """
    キャンプ場の検索結果を表示する関数

    Args:
        campsites (list): キャンプ場データのリスト
    """
    # 検索結果の数を表示
    if not campsites:
        st.warning("検索条件に一致するキャンプ場が見つかりませんでした。検索条件を変更してお試しください。")
        return

    st.subheader(f"🏕️ {len(campsites)}件のキャンプ場が見つかりました")

    # 各キャンプ場の詳細情報を表示
    for i, site in enumerate(campsites):
        # 人気のキャンプ場の場合、タイトルに人気マークを追加
        is_popular = site.get("is_popular", False)
        is_featured = site.get("is_featured", False)
        multiple_sources = site.get("multiple_sources", False)
        title_prefix = ""

        if is_featured:
            title_prefix = "🌟 "
        elif is_popular or multiple_sources:
            title_prefix = "🔥 "

        # 利用スタイルに合わせたアイコンを追加
        user_type_icons = {
            "ソロキャンプ": "👤 ",
            "カップル": "💑 ",
            "ファミリー": "👨‍👩‍👧‍👦 ",
            "グループ": "👥 ",
        }

        # キャンプ場の特徴から利用スタイルを推測
        user_type_icon = ""
        features = site.get("features", [])
        description = site.get("description", "").lower()

        if (
            any(keyword in description for keyword in ["ソロ", "一人", "静か", "プライバシー"])
            or "ソロサイト" in features
        ):
            user_type_icon = user_type_icons["ソロキャンプ"]
        elif any(keyword in description for keyword in ["カップル", "二人", "デート", "ロマンチック"]):
            user_type_icon = user_type_icons["カップル"]
        elif (
            any(keyword in description for keyword in ["ファミリー", "家族", "子供", "キッズ", "遊具"])
            or "キッズスペース" in features
        ):
            user_type_icon = user_type_icons["ファミリー"]
        elif (
            any(keyword in description for keyword in ["グループ", "団体", "大人数", "仲間"])
            or "大型サイト" in features
        ):
            user_type_icon = user_type_icons["グループ"]

        # エクスパンダーでキャンプ場情報を表示
        with st.expander(f"{i+1}. {title_prefix}{user_type_icon}{site.get('name', 'キャンプ場')}"):
            # 区切り線の上部
            st.markdown("---")

            # キャンプ場名（大きく表示）
            st.markdown(f"## {site.get('name', 'キャンプ場')}")

            # 地域情報
            region = site.get("region", "")
            if region:
                st.markdown(f"**地域**: {region}")

            # 画像の表示
            image_url = site.get("image_url", "")
            if image_url:
                try:
                    st.image(image_url, use_column_width=True)
                except Exception as e:
                    pass

            # おすすめポイントや理由
            recommendation_points = []

            # ハイライト情報
            highlights = site.get("highlights", "")
            if highlights:
                recommendation_points.append(f"**ハイライト**: {highlights}")

            # AIのおすすめポイント
            ai_recommendation = site.get("ai_recommendation_reason", "")
            if ai_recommendation:
                recommendation_points.append(f"**AIのおすすめポイント**: {ai_recommendation}")

            # 検索条件との一致点
            recommendation_reason = site.get("recommendation_reason", "")
            if recommendation_reason:
                recommendation_points.append(f"**検索条件との一致点**: {recommendation_reason}")

            # 口コミ分析
            review_summary = site.get("review_summary", "")
            if review_summary:
                recommendation_points.append(f"**口コミ分析**: {review_summary}")

            # 最適な利用者層
            best_for = site.get("best_for", "")
            if best_for:
                recommendation_points.append(f"**おすすめの利用者**: {best_for}")
            # 利用スタイルに合わせた情報を強調表示
            elif user_type_icon:
                user_type_text = ""
                if user_type_icon == user_type_icons["ソロキャンプ"]:
                    user_type_text = "ソロキャンパー"
                elif user_type_icon == user_type_icons["カップル"]:
                    user_type_text = "カップル"
                elif user_type_icon == user_type_icons["ファミリー"]:
                    user_type_text = "ファミリー"
                elif user_type_icon == user_type_icons["グループ"]:
                    user_type_text = "グループ・団体"

                recommendation_points.append(f"**おすすめの利用者**: {user_type_text}におすすめ")

            # 説明文
            description = site.get("description", "")
            if description and not any(point in description for point in recommendation_points):
                recommendation_points.append(f"**説明**: {description}")

            # おすすめポイントを表示
            if recommendation_points:
                st.markdown("### おすすめポイント")
                for point in recommendation_points:
                    st.markdown(point)

            # 施設・設備と特徴を簡潔に表示
            facilities = site.get("facilities", [])
            features = site.get("features", [])

            if facilities or features:
                st.markdown("### 施設・特徴")

                if facilities:
                    st.markdown(f"**施設**: {', '.join(facilities)}")

                if features:
                    st.markdown(f"**特徴**: {', '.join(features)}")

            # リンク情報
            st.markdown("### リンク")

            # 公式サイト
            website = site.get("website", "")
            if website:
                st.markdown(f"[🌐 公式サイトを見る]({website})")

            # Google Map
            name = site.get("name", "")
            address = site.get("address", "")
            if address:
                map_query = f"{name} {address}"
            else:
                map_query = f"{name} キャンプ場"

            google_map_url = f"https://www.google.com/maps/search/?api=1&query={map_query}"
            st.markdown(f"[🗺️ Google Mapで見る]({google_map_url})")

            # 予約サイト
            st.markdown("### 予約サイト")
            booking_sites = [
                {
                    "name": "楽天トラベル",
                    "url": f"https://travel.rakuten.co.jp/search/keyword?f_keyword={name}+キャンプ場",
                },
                {"name": "じゃらん", "url": f"https://www.jalan.net/kankou/spt_guide_result/?keyword={name}"},
                {"name": "なっぷ", "url": f"https://www.nap-camp.com/search?keyword={name}"},
            ]

            booking_cols = st.columns(len(booking_sites))
            for j, booking in enumerate(booking_sites):
                with booking_cols[j]:
                    st.markdown(f"[{booking['name']}]({booking['url']})")

            # 区切り線の下部
            st.markdown("---")

            # 詳細情報を表示するボタン
            if st.button(f"「{name}」の詳細情報を見る", key=f"detail_{i}"):
                show_detailed_info(site)


def show_detailed_info(site):
    """
    キャンプ場の詳細情報を表示する関数

    Args:
        site (dict): キャンプ場データ
    """
    st.markdown(f"## {site.get('name', 'キャンプ場')}の詳細情報")

    cols = st.columns([2, 3])

    with cols[0]:
        # 画像の表示
        image_url = site.get("image_url", "")
        if image_url:
            try:
                st.image(image_url, use_column_width=True)
            except Exception as e:
                st.image("https://via.placeholder.com/400x300?text=No+Image", use_column_width=True)
        else:
            st.image("https://via.placeholder.com/400x300?text=No+Image", use_column_width=True)

        # 基本情報
        st.markdown("#### 基本情報")

        # 評価の表示
        rating = site.get("rating", 0)
        if rating > 0:
            st.write(f"⭐ 評価: {rating}/5")

        # スコアの表示
        score = site.get("score", 0)
        if score > 0:
            st.write(f"📊 スコア: {score}/10")

        # 人気度の表示
        is_featured = site.get("is_featured", False)
        is_popular = site.get("is_popular", False)
        multiple_sources = site.get("multiple_sources", False)

        if is_featured:
            st.write("🌟 特集されているキャンプ場")
        elif is_popular or multiple_sources:
            occurrence_count = site.get("occurrence_count", 0)
            if occurrence_count > 1:
                st.write(f"🔥 人気度: {occurrence_count}件のソースで検出")
            else:
                st.write("🔥 人気のキャンプ場")

        # 利用スタイルの表示
        features = site.get("features", [])
        description = site.get("description", "").lower()

        if (
            any(keyword in description for keyword in ["ソロ", "一人", "静か", "プライバシー"])
            or "ソロサイト" in features
        ):
            st.write("👤 ソロキャンパーにおすすめ")
        if any(keyword in description for keyword in ["カップル", "二人", "デート", "ロマンチック"]):
            st.write("💑 カップルにおすすめ")
        if (
            any(keyword in description for keyword in ["ファミリー", "家族", "子供", "キッズ", "遊具"])
            or "キッズスペース" in features
        ):
            st.write("👨‍👩‍👧‍👦 ファミリーにおすすめ")
        if (
            any(keyword in description for keyword in ["グループ", "団体", "大人数", "仲間"])
            or "大型サイト" in features
        ):
            st.write("👥 グループ・団体におすすめ")

        # ハイライトの表示
        highlights = site.get("highlights", "")
        if highlights:
            st.write(f"✨ ハイライト: {highlights}")

        # 最適な利用者層の表示
        best_for = site.get("best_for", "")
        if best_for:
            st.write(f"👥 おすすめ: {best_for}")

        # 地域の表示
        region = site.get("region", "")
        if region:
            st.write(f"📍 地域: {region}")

        # 住所の表示
        address = site.get("address", "")
        if address:
            st.write(f"🏠 住所: {address}")

            # Google Mapへのリンク
            google_map_url = f"https://www.google.com/maps/search/?api=1&query={site.get('name', '')}+{address}"
            st.write(f"🗺️ [Google Mapで見る]({google_map_url})")

        # 価格の表示
        price = site.get("price", "")
        if price:
            st.write(f"💰 価格: {price}")

        # ウェブサイトの表示
        website = site.get("website", "")
        if website:
            st.write(f"🌐 [ウェブサイト]({website})")

        # 位置情報の表示
        location = site.get("location", {})
        if location and "lat" in location and "lng" in location:
            lat = location.get("lat")
            lng = location.get("lng")
            if lat and lng:
                # Google Mapへの直接リンク（座標指定）
                map_url = f"https://www.google.com/maps?q={lat},{lng}"
                st.write(f"📍 [正確な位置を地図で見る]({map_url})")

        # データソースの表示
        source = site.get("source", "")
        if source:
            # 複数のソースがある場合はカンマで区切られている
            if "," in source:
                sources = source.split(",")
                st.write(f"📊 データソース: {', '.join(sources)}")
            else:
                st.write(f"📊 データソース: {source}")

        # 特集記事の表示
        featured_in = site.get("featured_in", "")
        if featured_in:
            st.write(f"📰 掲載: {featured_in}")

    with cols[1]:
        # 説明文
        st.markdown("#### 説明")
        description = site.get("description", "情報がありません")
        st.write(description)

        # 施設・設備
        facilities = site.get("facilities", [])
        if facilities:
            st.markdown("#### 施設・設備")
            st.write(", ".join(facilities))

        # 特徴
        features = site.get("features", [])
        if features:
            st.markdown("#### 特徴")
            st.write(", ".join(features))

        # 口コミ分析
        review_summary = site.get("review_summary", "")
        if review_summary:
            st.markdown("#### 口コミ分析")
            st.write(review_summary)

        # AIのおすすめポイント
        ai_recommendation = site.get("ai_recommendation_reason", "")
        if ai_recommendation:
            st.markdown("#### AIのおすすめポイント")
            st.write(ai_recommendation)

        # 検索条件との一致点
        recommendation_reason = site.get("recommendation_reason", "")
        if recommendation_reason:
            st.markdown("#### 検索条件との一致点")
            st.write(recommendation_reason)

        # 口コミの表示
        reviews = site.get("reviews", [])
        if reviews:
            st.markdown("#### 口コミ")

            for review in reviews[:3]:  # 最大3件まで表示
                review_cols = st.columns([1, 3, 2])

                # 評価
                with review_cols[0]:
                    review_rating = review.get("rating", 0)
                    st.write(f"⭐ {review_rating}/5")

                # レビュー本文
                with review_cols[1]:
                    review_text = review.get("text", "")
                    st.write(review_text)

                # 日付
                with review_cols[2]:
                    review_time = review.get("time", "")
                    if review_time:
                        st.write(f"📅 {review_time}")

            if len(reviews) > 3:
                st.write(f"他 {len(reviews) - 3} 件の口コミがあります。")

        # 設備情報
        st.markdown("### 設備・特徴")
        facilities_cols = st.columns(5)

        with facilities_cols[0]:
            if site.get("has_shower", False):
                st.markdown("🚿 シャワー")
            else:
                st.markdown("🚿 ~~シャワー~~")

        with facilities_cols[1]:
            if site.get("has_electricity", False):
                st.markdown("🔌 電源")
            else:
                st.markdown("🔌 ~~電源~~")

        with facilities_cols[2]:
            if site.get("pet_friendly", False):
                st.markdown("🐕 ペットOK")
            else:
                st.markdown("🐕 ~~ペットOK~~")

        with facilities_cols[3]:
            if site.get("has_hot_spring", False):
                st.markdown("♨️ 温泉")
            else:
                st.markdown("♨️ ~~温泉~~")

        with facilities_cols[4]:
            if site.get("has_wifi", False):
                st.markdown("📶 Wi-Fi")
            else:
                st.markdown("📶 ~~Wi-Fi~~")

        # 特徴タグの表示
        if site.get("features"):
            st.markdown("### 特徴")
            feature_html = ""
            for feature in site.get("features", []):
                feature_html += f'<span style="background-color: #e6f3ff; padding: 3px 8px; margin: 2px; border-radius: 10px; display: inline-block;">{feature}</span>'
            st.markdown(feature_html, unsafe_allow_html=True)


def format_price(price):
    """
    料金を適切にフォーマットする関数

    Args:
        price (str or int): 料金情報

    Returns:
        str: フォーマットされた料金文字列
    """
    if isinstance(price, (int, float)):
        return f"¥{price:,}/泊"
    else:
        return price
