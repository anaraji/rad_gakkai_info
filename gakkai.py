import streamlit as st
import pandas as pd
from datetime import datetime
import re

# ページ設定
st.set_page_config(page_title="放射線技師 学会・研究会DB", layout="wide")

# --- 【追加】右上のメニューやヘッダーを隠すCSS ---
hide_menu_style = """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """
st.markdown(hide_menu_style, unsafe_allow_html=True)


# --- 【追加】簡易パスワード認証機能 ---
def check_password():
    """パスワード認証を行う関数"""
    # セッション状態にパスワード認証済みフラグがない場合は初期化
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    # 認証済みなら何もしない（メイン処理へ進む）
    if st.session_state.password_correct:
        return True

    # パスワード入力フォームを表示
    st.header("🔒 認証")
    password_input = st.text_input("合言葉を入力してください", type="password")
    
    if st.button("ログイン"):
        # Secretsに保存したパスワードと照合
        if password_input == st.secrets["app_password"]:
            st.session_state.password_correct = True
            st.rerun() # 画面を再読み込みしてメイン表示へ
        else:
            st.error("合言葉が違います")
            
    return False

# 認証チェック：通らなければここでプログラムを強制終了(stop)する
if not check_password():
    st.stop()

# --- ここから下はいつものメイン処理 ---
# ... (clean_date関数やデータ読み込み処理など、既存のコードが続きます)
# --- 関数: 日付のクリーニング処理 ---
def clean_date(date_val):
    if pd.isna(date_val):
        return pd.NaT
    text = str(date_val)
    text = re.sub(r'[~〜\u2010-\u2015\u2212ー−]', '-', text)
    text = text.split('-')[0]
    text = text.replace('年', '/').replace('月', '/').replace('日', '')
    text = text.strip()
    try:
        return pd.to_datetime(text)
    except:
        return pd.NaT

# --- 1. データ読み込み ---
try:
    # Secrets(金庫)からURLを取得
    csv_url = st.secrets["csv_url"]
    
    # データを読み込む
    df = pd.read_csv(csv_url)

    # --- データの加工 ---
    
    # 日付変換
    df["開催日"] = df["開催日"].apply(clean_date)
    df = df.dropna(subset=["開催日"])

    # モダリティのリスト化
    df["モダリティ"] = df["モダリティ"].fillna("").astype(str).apply(
        lambda x: x.replace("、", ",").replace('"', '').split(",")
    )
    df["モダリティ"] = df["モダリティ"].apply(lambda x: [m.strip() for m in x if m.strip()])
    
except Exception as e:
    st.error(f"データの読み込み中にエラーが発生しました: {e}")
    st.stop()


# --- 2. サイドバー (検索条件) ---
st.sidebar.header("🔍 学会検索")

# 地域フィルター
region_list = sorted(list(set(df["地域"].dropna().astype(str))))
selected_regions = st.sidebar.multiselect("地域を選択", region_list, default=region_list)

# モダリティフィルター
all_modalities = set([m for sublist in df["モダリティ"] for m in sublist])
selected_modalities = st.sidebar.multiselect("モダリティを選択", sorted(list(all_modalities)))

# 日付フィルター
today = datetime.now()
show_past = st.sidebar.checkbox("終了した学会も表示する", value=False)


# --- 3. データの絞り込み ---
filtered_df = df[df["地域"].isin(selected_regions)]

if selected_modalities:
    filtered_df = filtered_df[filtered_df["モダリティ"].apply(lambda x: not set(x).isdisjoint(set(selected_modalities)))]

if not show_past:
    filtered_df = filtered_df[filtered_df["開催日"] >= pd.to_datetime(today.date())]

filtered_df = filtered_df.sort_values("開催日")


# --- 4. メイン表示 ---
st.title("🏥 診療放射線技師向け 学会・研究会情報")
st.caption(f"最終更新: {today.strftime('%Y/%m/%d %H:%M')}")

try:
    edit_url = st.secrets["edit_url"]
    st.markdown(f"データの修正・追加は[こちらのスプレッドシート]({edit_url})からお願いします。")
except:
    st.warning("Secretsに edit_url が設定されていません。")

st.info(f"検索結果: {len(filtered_df)} 件")

if len(filtered_df) == 0:
    st.warning("条件に一致する学会が見つかりませんでした。")
else:
    for index, row in filtered_df.iterrows():
        with st.container():
            st.markdown("---")
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # 日付と学会名
                date_str = row['開催日'].strftime('%Y/%m/%d')
                st.subheader(f"📅 {date_str} | {row['学会名']}")
                st.caption(f"📍 {row['地域']} ({row['都道府県']})")
                
                # バッジ表示
                badges_html = ""
                
                # 1. モダリティ (水色)
                for mod in row["モダリティ"]:
                    badges_html += f"<span style='background-color:#e0f7fa; color:#006064; padding:4px 8px; border-radius:12px; margin-right:5px; font-size:0.8em; display:inline-block; margin-bottom:4px;'>{mod}</span>"
                
                # 2. 専門ポイント (黄色/オレンジ) - G列「専門ポイント」
                if "専門ポイント" in df.columns:
                    point_val = row["専門ポイント"]
                    if pd.notna(point_val) and str(point_val).strip() != "":
                        badges_html += f"<span style='background-color:#fff9c4; color:#f57f17; padding:4px 8px; border-radius:12px; margin-right:5px; font-size:0.8em; display:inline-block; margin-bottom:4px; font-weight:bold;'>★ {point_val}</span>"

                # 3. ハイブリッド開催 (紫) - H列「ハイブリッド開催」
                if "ハイブリッド開催" in df.columns:
                    hybrid_val = row["ハイブリッド開催"]
                    if pd.notna(hybrid_val) and str(hybrid_val).strip() != "":
                        badges_html += f"<span style='background-color:#f3e5f5; color:#7b1fa2; padding:4px 8px; border-radius:12px; margin-right:5px; font-size:0.8em; display:inline-block; margin-bottom:4px;'>📶 {hybrid_val}</span>"

                st.markdown(badges_html, unsafe_allow_html=True)
                
            with col2:
                st.write("")
                st.write("")
                url = str(row["URL"])
                if url and url.lower() != "nan" and url != "":
                    st.link_button("公式サイトへ", url)
                else:
                    st.button("URLなし", disabled=True)

st.markdown("---")


