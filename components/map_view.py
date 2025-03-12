import streamlit as st
import pandas as pd
import pydeck as pdk


def render_map(campsites):
    """
    キャンプ場の位置を地図上に表示する関数

    Args:
        campsites (list): キャンプ場データのリスト
    """
    st.subheader("地図表示")

    # 地図データの準備
    map_data = []
    for site in campsites:
        # 緯度経度情報がある場合のみ追加
        if "latitude" in site and "longitude" in site:
            map_data.append(
                {
                    "name": site.get("name", ""),
                    "latitude": site.get("latitude", 0),
                    "longitude": site.get("longitude", 0),
                    "price": site.get("price", 0),
                    "rating": site.get("rating", 0),
                }
            )

    # 地図データがある場合のみ表示
    if map_data:
        df = pd.DataFrame(map_data)

        # 地図の中心位置を計算（全キャンプ場の平均位置）
        center_lat = df["latitude"].mean()
        center_lon = df["longitude"].mean()

        # PyDeckを使用して地図を表示
        st.pydeck_chart(
            pdk.Deck(
                map_style="mapbox://styles/mapbox/outdoors-v11",
                initial_view_state=pdk.ViewState(
                    latitude=center_lat,
                    longitude=center_lon,
                    zoom=5,
                    pitch=0,
                ),
                layers=[
                    pdk.Layer(
                        "ScatterplotLayer",
                        data=df,
                        get_position=["longitude", "latitude"],
                        get_color=[255, 0, 0, 160],
                        get_radius=5000,
                        pickable=True,
                        auto_highlight=True,
                    ),
                ],
                tooltip={
                    "html": "<b>{name}</b><br/>料金: ¥{price}/泊<br/>評価: {rating}⭐",
                    "style": {"backgroundColor": "white", "color": "black"},
                },
            )
        )
    else:
        # サンプルマップを表示（日本全体）
        st.info("位置情報のあるキャンプ場がありません。サンプルマップを表示します。")

        # 日本の中心あたりの座標
        center_lat = 36.2048
        center_lon = 138.2529

        # 日本全体を表示するサンプルマップ
        st.pydeck_chart(
            pdk.Deck(
                map_style="mapbox://styles/mapbox/outdoors-v11",
                initial_view_state=pdk.ViewState(
                    latitude=center_lat,
                    longitude=center_lon,
                    zoom=4,
                    pitch=0,
                ),
            )
        )
