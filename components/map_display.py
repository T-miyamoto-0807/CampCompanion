import streamlit as st
import folium
from streamlit_folium import folium_static
import pandas as pd


def display_map(campsites):
    """
    キャンプ場の位置情報を地図上に表示する関数

    Args:
        campsites (list): キャンプ場データのリスト
    """
    # デバッグ出力
    DEBUG = True
    if DEBUG:
        print(f"\n===== display_map: キャンプ場数: {len(campsites)} =====")
        if campsites:
            first_site = campsites[0]
            print(f"最初のキャンプ場: {first_site.get('name', '不明')}")
            print(f"位置情報: {first_site.get('location', '不明')}")
            print(f"緯度: {first_site.get('latitude', '不明')}")
            print(f"経度: {first_site.get('longitude', '不明')}")

    # 有効な位置情報を持つキャンプ場のみをフィルタリング
    valid_locations = []
    for site in campsites:
        # locationオブジェクトがある場合
        if "location" in site and isinstance(site["location"], dict):
            # latitudeとlongitudeキーがある場合
            if "latitude" in site["location"] and "longitude" in site["location"]:
                lat = site["location"].get("latitude")
                lng = site["location"].get("longitude")
                if lat and lng:
                    # locationオブジェクトを標準形式に変換
                    site["location"] = {"lat": lat, "lng": lng}
                    valid_locations.append(site)
            # latとlngキーがある場合
            elif "lat" in site["location"] and "lng" in site["location"]:
                lat = site["location"].get("lat")
                lng = site["location"].get("lng")
                if lat and lng:
                    valid_locations.append(site)
        # 緯度経度が直接指定されている場合
        elif "latitude" in site and "longitude" in site and site["latitude"] and site["longitude"]:
            # locationオブジェクトを作成
            site["location"] = {"lat": site["latitude"], "lng": site["longitude"]}
            valid_locations.append(site)

    if DEBUG:
        print(f"有効な位置情報を持つキャンプ場: {len(valid_locations)}件")

    if not valid_locations:
        st.warning("位置情報のあるキャンプ場が見つかりませんでした。")
        return

    # 地図の中心位置を計算（全キャンプ場の平均位置）
    avg_lat = sum(site["location"]["lat"] for site in valid_locations) / len(valid_locations)
    avg_lng = sum(site["location"]["lng"] for site in valid_locations) / len(valid_locations)

    # 地図を作成
    m = folium.Map(location=[avg_lat, avg_lng], zoom_start=10)

    # キャンプ場ごとにマーカーを追加
    for site in valid_locations:
        # 評価に基づいてマーカーの色を決定
        rating = site.get("rating", 0)
        if rating >= 4.5:
            color = "darkgreen"  # 最高評価
        elif rating >= 4.0:
            color = "green"  # 高評価
        elif rating >= 3.5:
            color = "orange"  # 中評価
        elif rating >= 3.0:
            color = "lightred"  # やや低評価
        else:
            color = "lightgray"  # 低評価または評価なし

        # おすすめスコアがある場合は、マーカーサイズを調整
        if "score" in site:
            score = site.get("score", 0)
            radius = min(10 + (score / 2), 20)  # スコアに基づいてサイズを調整（最大20）
        else:
            radius = 10  # デフォルトサイズ

        # ポップアップ内容を作成
        popup_html = f"""
        <div style="width: 250px;">
            <h4>{site.get('name', '不明')}</h4>
            <p><b>評価:</b> {'⭐' * int(site.get('rating', 0))} ({site.get('rating', 0)})</p>
            <p><b>住所:</b> {site.get('address', '不明')}</p>
        """

        # おすすめスコアがある場合は表示
        if "score" in site:
            popup_html += f"<p><b>おすすめ度:</b> {site.get('score', 0)}点</p>"

        # 施設情報があれば表示
        if site.get("facilities"):
            popup_html += f"<p><b>施設:</b> {', '.join(site.get('facilities', []))[:100]}</p>"

        # 特徴情報があれば表示
        if site.get("features"):
            popup_html += f"<p><b>特徴:</b> {', '.join(site.get('features', []))[:100]}</p>"

        # Google Mapsリンク
        if site.get("place_id"):
            maps_url = f"https://www.google.com/maps/place/?q=place_id:{site['place_id']}"
            popup_html += f'<p><a href="{maps_url}" target="_blank">Google Mapsで見る</a></p>'
        else:
            maps_url = (
                f"https://www.google.com/maps/search/?api=1&query={site['location']['lat']},{site['location']['lng']}"
            )
            popup_html += f'<p><a href="{maps_url}" target="_blank">Google Mapsで見る</a></p>'

        # 公式サイトリンク
        if site.get("website"):
            popup_html += f'<p><a href="{site["website"]}" target="_blank">公式サイトを見る</a></p>'

        popup_html += "</div>"

        # マーカーを追加
        folium.CircleMarker(
            location=[site["location"]["lat"], site["location"]["lng"]],
            radius=radius,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=site.get("name", "不明"),
            color=color,
            fill=True,
            fill_opacity=0.7,
        ).add_to(m)

    # 地図を表示
    folium_static(m, width=800, height=500)
