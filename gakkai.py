import streamlit as st
import pandas as pd
from datetime import datetime
import re

# ページ設定
st.set_page_config(page_title="放射線技師 学会・研究会DB", layout="wide")

# --- 関数: 日付のクリーニング処理 ---
def clean_date(date_val):
    """
    あらゆる形式の日付文字列から、YYYY-MM-DD (datetime型) を抽出する関数
    """
    if pd.isna(date_val):
        return pd.NaT
    
    text = str(date_val)
    # 1. あらゆる種類の「横棒」や「波線」を、普通の半角ハイフン「-」に統一
    text = re.sub(r'[~〜\u2010-\u2015\u2212ー−]', '-', text)
    # 2. 統一したハイフンで分割し、最初の部分（開始日）だけ取る
    text = text.split('-')[0]
    # 3. 日本語の「年」「月」をスラッシュに、「日」を削除
    text = text.replace('年', '/').replace('月', '/').replace('日', '')
    # 4. 余計な空白を削除
    text = text.strip()
    
    try:
        return pd.to_datetime(text)
    except:
        return pd.NaT

# --- 1. データ読み込み (Googleスプレッドシートから) ---
# あなたが発行した公開用URL
csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQkQ35h2CJlsC9bdxHhhE--96pc9HH9diF0NNPQwY1FLMJNa2CuyWWe9EW3bryPE4EFIDn1-yHy_As2/pub?gid=0&single=true&output=csv"

try:
    # URLから直接データを読み込む
    df = pd.read_csv(csv_url)

    # --- データの加工 ---
    
    # 日付変換（強化版）
    df["開催日"] = df["開催日"].apply(clean_date)
    
    # 日付変換に失敗した行（NaT）があるかチェック
    failed_rows = df[df["開催日"].isna()]
    if not failed_rows.empty:
        st.toast(f"⚠️ {len(failed_rows)} 件の日付が読み込めませんでした（スプレッドシートを確認してください）", icon="⚠️")
        df = df.dropna(subset=["開催日"])

    # モダリティのリスト化処理
    # スプレッドシートだと勝手に数値になったりするので文字列に変換してから処理
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
# 地域
filtered_df = df[df["地域"].isin(selected_regions)]

# モダリティ
if selected_modalities:
    filtered_df = filtered_df[filtered_df["モダリティ"].apply(lambda x: not set(x).isdisjoint(set(selected_modalities)))]

# 日付
if not show_past:
    filtered_df = filtered_df[filtered_df["開催日"] >= pd.to_datetime(today.date())]

# ソート
filtered_df = filtered_df.sort_values("開催日")


# --- 4. メイン表示 ---
st.title("🏥 診療放射線技師向け 学会・研究会情報")
st.caption(f"最終更新: {today.strftime('%Y/%m/%d %H:%M')}")
st.markdown("データの修正・追加は[こちらのスプレッドシート](https://docs.google.com/spreadsheets/d/1_mYFO8fCD1c4P8RtiYAVwBem_h7iijpIGFhGxzaf14/edit?gid=0#gid=0)からお願いします。") # ※必要なら編集用URLを貼る

st.info(f"検索結果: {len(filtered_df)} 件")

if len(filtered_df) == 0:
    st.warning("条件に一致する学会が見つかりませんでした。")
else:
    for index, row in filtered_df.iterrows():
        with st.container():
            st.markdown("---")
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # 日付表示
                date_str = row['開催日'].strftime('%Y/%m/%d')
                st.subheader(f"📅 {date_str} | {row['学会名']}")
                st.caption(f"📍 {row['地域']} ({row['都道府県']})")
                
                # モダリティバッジ
                modality_html = ""
                for mod in row["モダリティ"]:
                    modality_html += f"<span style='background-color:#e0f7fa; color:#006064; padding:4px 8px; border-radius:12px; margin-right:5px; font-size:0.8em; display:inline-block; margin-bottom:4px;'>{mod}</span>"
                st.markdown(modality_html, unsafe_allow_html=True)
                
            with col2:
                st.write("")
                st.write("")
                # URLがある場合のみボタンを表示
                url = str(row["URL"])
                if url and url.lower() != "nan" and url != "":
                    st.link_button("公式サイトへ", url)
                else:
                    st.button("URLなし", disabled=True)

st.markdown("---")


