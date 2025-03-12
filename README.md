# CampCompanion - キャンプ場検索アプリ

CampCompanionは、日本全国のキャンプ場を簡単に検索できるWebアプリケーションです。キーワード検索や地域、設備などの条件でキャンプ場を探すことができます。

## 特徴

- キーワードによるキャンプ場検索
- 地域別検索（関東、関西、北海道など）
- 設備条件による絞り込み（シャワー、電源、ペット可など）
- 検索結果の地図表示
- 詳細情報の表示（料金、特徴、予約方法など）

## 使用技術

- Python 3.9+
- Streamlit
- Folium (地図表示)
- Google Places API (New) (新バージョン)
- Google Places API Gemini Model

## インストール方法

1. リポジトリをクローン
```bash
git clone https://github.com/yourusername/CampCompanion.git
cd CampCompanion
```

2. 仮想環境を作成して有効化
```bash
python -m venv venv
# Windowsの場合
venv\Scripts\activate
# macOS/Linuxの場合
source venv/bin/activate
```

3. 必要なパッケージをインストール
```bash
pip install -r requirements.txt
```

4. 環境変数の設定
`.env.example`ファイルを`.env`にコピーして、必要なAPIキーを設定します。
```bash
cp .env.example .env
```

5. アプリケーションの起動
```bash
streamlit run app.py
```

## API設定

CampCompanionは2つのAPIモードをサポートしています：

### 1. Places API (New) (デフォルト)

Google Places API (New)を使用して実際のキャンプ場情報を検索します。このモードでは、Googleの新しいPlaces APIエンドポイントを使用します。

設定方法:
1. [Google Cloud Console](https://console.cloud.google.com/)でプロジェクトを作成
2. **Places API (New)** を有効化（重要: 新しいバージョンのAPIが必要です）
3. APIキーを作成
4. `.env`ファイルの`GOOGLE_PLACE_API_KEY`に取得したキーを設定
5. `.env`ファイルの`API_MODE`を`places_new`に設定（デフォルト）

### 2. Places Gemini API

Google Places APIのGeminiモデル機能を使用して、AIによる要約と実際のキャンプ場情報を組み合わせて検索します。このモードでは、Google Mapsのデータと生成AIの機能を組み合わせて使用します。

設定方法:
1. [Google Cloud Console](https://console.cloud.google.com/)でプロジェクトを作成
2. **Places API (New)** を有効化（重要: 新しいバージョンのAPIが必要です）
3. APIキーを作成
4. `.env`ファイルの`GOOGLE_PLACE_API_KEY`に取得したキーを設定
5. `.env`ファイルの`API_MODE`を`places_gemini`に設定

## APIモードの切り替え

デバッグモードが有効な場合（`DEBUG=True`）、アプリケーションのサイドバーでAPIモードを切り替えることができます。

## トラブルシューティング

### Places API (New)のエラー

- APIキーが正しく設定されているか確認してください
- Google Cloud Consoleで**Places API (New)**が有効化されているか確認してください
- 請求情報が正しく設定されているか確認してください
- APIキーの制限が適切に設定されているか確認してください

### Places Gemini APIのエラー

- APIキーが正しく設定されているか確認してください
- Google Cloud Consoleで**Places API (New)**が有効化されているか確認してください
- 請求情報が正しく設定されているか確認してください
- APIキーの制限が適切に設定されているか確認してください

## テスト方法

各APIモードのテストスクリプトが用意されています：

- Places API (New): `python test_places_new.py`
- Places Gemini API: `python test_places_gemini.py`

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 貢献

バグ報告や機能リクエストは、GitHubのIssueで受け付けています。プルリクエストも歓迎します。 