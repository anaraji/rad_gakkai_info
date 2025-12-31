import streamlit as st
import pandas as pd
from datetime import datetime
import re

# ページ設定
st.set_page_config(page_title="放射線技師 学会・研究会DB", layout="wide")

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
    df = df.dropna(subset=["開催日"]) # 日付がないものは除外

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

# 編集用URLもSecretsから取得
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
                
                # バッジ表示用のHTML作成
                badges_html = ""
                
                # 1. モダリティ (水色)
                for mod in row["モダリティ"]:
                    badges_html += f"<span style='background-color:#e0f7fa; color:#006064; padding:4px 8px; border-radius:12px; margin-right:5px; font-size:0.8em; display:inline-block; margin-bottom:4px;'>{mod}</span>"
                
                # 2. 専門ポイント (黄色/オレンジ) - G列
                # 列が存在し、かつデータが入っている場合のみ表示
                if "専門ポイントの有無" in df.columns:
                    point_val = row["専門ポイント"]
                    if pd.notna(point_val) and str(point_val).strip() != "":
                        badges_html += f"<span style='background-color:#fff9c4; color:#f57f17; padding:4px 8px; border-radius:12px; margin-right:5px; font-size:0.8em; display:inline-block; margin-bottom:4px; font-weight:bold;'>★ {point_val}</span>"

                # 3. ハイブリッド開催 (紫) - H列
                if "ハイブリッド開催の有無" in df.columns:
                    hybrid_val = row["ハイブリッド開催"]
                    if pd.notna(hybrid_val) and str(hybrid_val).strip() != "":
                        badges_html += f"<span style='background-color:#f3e5f5; color:#7b1fa2; padding:4px 8px; border-radius:12px; margin-right:5px; font-size:0.8em; display:inline-block; margin-bottom:4px;'>📶 {hybrid_val}</span>"

                # HTMLを表示
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

