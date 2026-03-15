import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Analisis Penurunan Nasabah", layout="wide")

st.title("Analisis 20 Nasabah dengan Penurunan Tertinggi")
st.write(
    "Upload file CSV, lalu pilih kolom Nasabah, YoY, dan YTD. "
    "Angka dengan tanda kurung seperti `(11310)` akan dianggap sebagai penurunan."
)

def parse_financial_number(value):
    """
    Mengubah format angka seperti:
    - 11310   -> 11310
    - (11310) -> -11310
    - 11,310  -> 11310
    - (11,310)-> -11310
    - kosong / invalid -> None
    """
    if pd.isna(value):
        return None

    s = str(value).strip()
    if s == "":
        return None

    s = s.replace(" ", "")

    is_negative = False
    if s.startswith("(") and s.endswith(")"):
        is_negative = True
        s = s[1:-1]

    s = s.replace(",", "")
    s = re.sub(r"[^0-9\.-]", "", s)

    if s in ["", "-", ".", "-."]:
        return None

    try:
        num = float(s)
        if is_negative:
            num = -abs(num)
        return num
    except ValueError:
        return None


def format_display_number(value):
    """
    Format tampilan:
    negative -> (angka)
    positive -> angka biasa
    """
    if pd.isna(value):
        return ""

    try:
        value = float(value)
    except Exception:
        return str(value)

    if value < 0:
        return f"({abs(value):,.0f})"
    return f"{value:,.0f}"


def highlight_rows(row):
    """
    Warna berdasarkan ranking:
    0-4   -> merah
    5-9   -> kuning menyala
    >=10  -> putih
    """
    rank = row["Rank"]
    if rank <= 5:
        return ["background-color: #ff4d4f; color: white;"] * len(row)
    elif rank <= 10:
        return ["background-color: #ffff00; color: black;"] * len(row)
    else:
        return ["background-color: white; color: black;"] * len(row)


uploaded_file = st.file_uploader("Upload file CSV", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
    except UnicodeDecodeError:
        df = pd.read_csv(uploaded_file, encoding="latin1")

    st.subheader("Preview Data")
    st.dataframe(df.head(), use_container_width=True)

    st.subheader("Pilih Kolom")
    columns = df.columns.tolist()

    col1, col2, col3 = st.columns(3)

    with col1:
        nasabah_col = st.selectbox("Kolom Nama Nasabah", columns)

    with col2:
        yoy_col = st.selectbox("Kolom YoY", columns)

    with col3:
        ytd_col = st.selectbox("Kolom YTD", columns)

    ranking_mode = st.radio(
        "Urutkan berdasarkan:",
        ["YoY", "YTD", "Gabungan YoY + YTD"],
        horizontal=True
    )

    top_n = st.number_input(
        "Jumlah nasabah yang ditampilkan",
        min_value=1,
        max_value=100,
        value=20
    )

    if st.button("Proses Data"):
        result_df = df.copy()

        result_df["YoY_numeric"] = result_df[yoy_col].apply(parse_financial_number)
        result_df["YTD_numeric"] = result_df[ytd_col].apply(parse_financial_number)

        result_df["YoY_turun"] = result_df["YoY_numeric"] < 0
        result_df["YTD_turun"] = result_df["YTD_numeric"] < 0

        result_df["YoY_penurunan"] = result_df["YoY_numeric"].apply(
            lambda x: abs(x) if pd.notna(x) and x < 0 else 0
        )
        result_df["YTD_penurunan"] = result_df["YTD_numeric"].apply(
            lambda x: abs(x) if pd.notna(x) and x < 0 else 0
        )

        if ranking_mode == "YoY":
            filtered = result_df[result_df["YoY_turun"]].copy()
            filtered = filtered.sort_values(by="YoY_penurunan", ascending=False)

        elif ranking_mode == "YTD":
            filtered = result_df[result_df["YTD_turun"]].copy()
            filtered = filtered.sort_values(by="YTD_penurunan", ascending=False)

        else:
            filtered = result_df[
                (result_df["YoY_turun"]) | (result_df["YTD_turun"])
            ].copy()
            filtered["Total_penurunan"] = (
                filtered["YoY_penurunan"] + filtered["YTD_penurunan"]
            )
            filtered = filtered.sort_values(by="Total_penurunan", ascending=False)

        top_data = filtered.head(top_n).copy()
        top_data = top_data.reset_index(drop=True)
        top_data["Rank"] = top_data.index + 1

        display_df = pd.DataFrame({
            "Rank": top_data["Rank"],
            "Nasabah": top_data[nasabah_col],
            "YoY": top_data["YoY_numeric"].apply(format_display_number),
            "YTD": top_data["YTD_numeric"].apply(format_display_number),
            "Penurunan YoY": top_data["YoY_penurunan"].apply(lambda x: f"{x:,.0f}" if x != 0 else "-"),
            "Penurunan YTD": top_data["YTD_penurunan"].apply(lambda x: f"{x:,.0f}" if x != 0 else "-"),
        })

        if ranking_mode == "Gabungan YoY + YTD":
            display_df["Total Penurunan"] = top_data["Total_penurunan"].apply(
                lambda x: f"{x:,.0f}"
            )

        styled_df = display_df.style.apply(highlight_rows, axis=1)

        st.subheader(f"Top {top_n} Nasabah dengan Penurunan Tertinggi")
        st.dataframe(styled_df, use_container_width=True)

        csv_download = top_data.copy()
        cols_download = [
            nasabah_col, yoy_col, ytd_col,
            "YoY_numeric", "YTD_numeric",
            "YoY_penurunan", "YTD_penurunan"
        ]

        if ranking_mode == "Gabungan YoY + YTD":
            cols_download.append("Total_penurunan")

        csv_download = csv_download[cols_download]

        st.download_button(
            label="Download hasil CSV",
            data=csv_download.to_csv(index=False).encode("utf-8"),
            file_name="top_penurunan_nasabah.csv",
            mime="text/csv"
        )
else:
    st.info("Silakan upload file CSV terlebih dahulu.")
