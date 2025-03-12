import streamlit as st


def render_search_filters():
    """
    キャンプ場検索用のフィルターUIを表示する関数

    Returns:
        dict: 検索パラメータを含む辞書
    """
    # 検索条件を格納する辞書
    search_params = {}

    # 検索条件の入力UI - メイン画面向けにレイアウトを改善
    # キーワード検索 - 最も重要な要素なので目立つように配置
    search_params["keyword"] = st.text_input(
        "キャンプ場を検索",
        placeholder="キャンプ場名、特徴、地名など",
        help="検索したいキャンプ場の名前や特徴を入力してください",
    )

    # 3列レイアウトで基本条件を表示
    col1, col2, col3 = st.columns(3)

    with col1:
        # 地域選択
        regions = ["すべて", "北海道", "東北", "関東", "中部", "関西", "中国", "四国", "九州・沖縄"]
        search_params["region"] = st.selectbox("地域", regions, help="検索したい地域を選択してください")

    with col2:
        # 検索半径
        search_params["radius"] = (
            st.slider("検索半径", 10, 200, 50, step=10, help="指定した地域からの検索半径（km）") * 1000
        )  # メートルに変換

    with col3:
        # 並び替え
        sort_options = ["関連度", "評価順", "人気順"]
        search_params["sort"] = st.selectbox("並び替え", sort_options, help="検索結果の並び替え方法を選択してください")

    # 詳細条件の折りたたみセクション - コンパクトに表示
    with st.expander("詳細条件"):
        # 設備チェックボックス - 横並びに配置
        st.write("設備・特徴")

        # 設備チェックボックスを3列で表示
        amenities_col1, amenities_col2, amenities_col3 = st.columns(3)

        with amenities_col1:
            search_params["has_shower"] = st.checkbox("シャワー設備あり")
            search_params["has_toilet"] = st.checkbox("トイレあり")
            search_params["has_bath"] = st.checkbox("お風呂あり")

        with amenities_col2:
            search_params["has_electricity"] = st.checkbox("電源サイトあり")
            search_params["has_wifi"] = st.checkbox("Wi-Fiあり")
            search_params["has_shop"] = st.checkbox("売店あり")

        with amenities_col3:
            search_params["pet_friendly"] = st.checkbox("ペット可")
            search_params["has_playground"] = st.checkbox("遊び場あり")
            search_params["has_bbq"] = st.checkbox("BBQ可")

        # 追加オプション
        st.write("追加オプション")
        options_col1, options_col2 = st.columns(2)

        with options_col1:
            search_params["get_reviews"] = st.checkbox("口コミを取得", value=True)
            search_params["family_friendly"] = st.checkbox("ファミリー向け")

        with options_col2:
            search_params["beginner_friendly"] = st.checkbox("初心者向け")
            search_params["use_current_location"] = st.checkbox("現在地から検索")

    # 検索パラメータから設備リストを作成
    amenities = []
    if search_params.get("has_shower"):
        amenities.append("シャワー")
    if search_params.get("has_electricity"):
        amenities.append("電源")
    if search_params.get("pet_friendly"):
        amenities.append("ペット可")
    if search_params.get("has_toilet"):
        amenities.append("トイレ")
    if search_params.get("has_bath"):
        amenities.append("お風呂")
    if search_params.get("has_wifi"):
        amenities.append("Wi-Fi")
    if search_params.get("has_shop"):
        amenities.append("売店")
    if search_params.get("has_playground"):
        amenities.append("遊び場")
    if search_params.get("has_bbq"):
        amenities.append("BBQ")

    # 設備リストをパラメータに追加
    search_params["amenities"] = amenities

    return search_params


def render_ai_recommendation_form():
    """
    AIによるキャンプ場推薦のためのフォームを表示する関数

    Returns:
        dict: 推薦パラメータを含む辞書
    """
    st.subheader("あなたにぴったりのキャンプ場を提案します")

    # 推薦パラメータを格納する辞書
    recommendation_params = {}

    # ユーザー入力
    recommendation_params["preferences"] = st.text_area(
        "キャンプの希望条件を教えてください（例: 家族連れ、初心者向け、温泉付き、東京から2時間以内など）", height=150
    )

    # 詳細条件の折りたたみセクション
    with st.expander("詳細条件"):
        col1, col2 = st.columns(2)

        with col1:
            # 地域選択
            regions = ["指定なし", "北海道", "東北", "関東", "中部", "関西", "中国", "四国", "九州・沖縄"]
            recommendation_params["region"] = st.selectbox("希望地域", regions)

            # 予算範囲
            recommendation_params["budget"] = st.slider("予算（1泊あたり）", 0, 20000, 5000, step=1000)

        with col2:
            # グループタイプ
            group_types = ["指定なし", "家族", "カップル", "友人グループ", "ソロ"]
            recommendation_params["group_type"] = st.selectbox("グループタイプ", group_types)

            # キャンプスタイル
            camp_styles = ["指定なし", "オートキャンプ", "グランピング", "バンガロー", "コテージ", "テント泊"]
            recommendation_params["camp_style"] = st.selectbox("キャンプスタイル", camp_styles)

    return recommendation_params


def render_plan_generator_form():
    """
    キャンプ計画生成のためのフォームを表示する関数

    Returns:
        dict: 計画生成パラメータを含む辞書
    """
    st.subheader("キャンプ計画を作成")

    # 計画生成パラメータを格納する辞書
    plan_params = {}

    # キャンプ場名
    plan_params["campsite_name"] = st.text_input("キャンプ場名", placeholder="計画を作成するキャンプ場名")

    col1, col2 = st.columns(2)

    with col1:
        # 滞在期間
        durations = ["1泊2日", "2泊3日", "3泊4日", "日帰り"]
        plan_params["duration"] = st.selectbox("滞在期間", durations)

        # 季節
        seasons = ["春", "夏", "秋", "冬", "現在の季節"]
        plan_params["season"] = st.selectbox("季節", seasons)

    with col2:
        # グループタイプ
        group_types = ["家族", "カップル", "友人グループ", "ソロ"]
        plan_params["group_type"] = st.selectbox("グループタイプ", group_types)

        # 子供の有無
        plan_params["has_children"] = st.checkbox("子供連れ")

    # 希望条件
    plan_params["preferences"] = st.text_area(
        "希望条件や特別な要望があれば入力してください",
        placeholder="例: バーベキューをしたい、釣りを楽しみたい、ハイキングコースを探している など",
        height=100,
    )

    return plan_params


def render_packing_list_form():
    """
    持ち物リスト生成のためのフォームを表示する関数

    Returns:
        dict: 持ち物リスト生成パラメータを含む辞書
    """
    st.subheader("持ち物リストを作成")

    # 持ち物リスト生成パラメータを格納する辞書
    packing_params = {}

    col1, col2 = st.columns(2)

    with col1:
        # キャンプスタイル
        camp_styles = ["テント泊", "オートキャンプ", "グランピング", "バンガロー", "コテージ"]
        packing_params["camp_style"] = st.selectbox("キャンプスタイル", camp_styles)

        # 滞在期間
        durations = ["日帰り", "1泊2日", "2泊3日", "3泊4日以上"]
        packing_params["duration"] = st.selectbox("滞在期間", durations)

    with col2:
        # 季節
        seasons = ["春", "夏", "秋", "冬"]
        packing_params["season"] = st.selectbox("季節", seasons)

        # グループタイプ
        group_types = ["家族", "カップル", "友人グループ", "ソロ"]
        packing_params["group_type"] = st.selectbox("グループタイプ", group_types)

    # 特別な要望
    packing_params["special_needs"] = st.text_area(
        "特別な要望や条件があれば入力してください",
        placeholder="例: 小さな子供がいる、ペット同伴、釣りをする予定 など",
        height=100,
    )

    return packing_params
