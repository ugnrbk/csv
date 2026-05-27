import io

import pandas as pd
import streamlit as st


st.set_page_config(page_title="CSV Image URL Splitter", page_icon="🖼️", layout="wide")
st.title("CSV/Excel Image URL Splitter for Shopify")
st.write(
    "Upload a CSV or Excel file, choose the column with comma-separated image URLs, "
    "and download a clean UTF-8 CSV with one image URL per row."
)


def read_uploaded_file(uploaded_file: st.runtime.uploaded_file_manager.UploadedFile) -> pd.DataFrame:
    """Read CSV or Excel file from memory and return a DataFrame."""
    file_name = uploaded_file.name.lower()
    file_bytes = uploaded_file.getvalue()

    if file_name.endswith(".csv"):
        # Try UTF-8 first, then fallback for broader compatibility.
        try:
            return pd.read_csv(io.BytesIO(file_bytes), dtype=str).fillna("")
        except UnicodeDecodeError:
            return pd.read_csv(io.BytesIO(file_bytes), dtype=str, encoding="latin1").fillna("")

    if file_name.endswith(".xlsx") or file_name.endswith(".xls"):
        return pd.read_excel(io.BytesIO(file_bytes), dtype=str).fillna("")

    raise ValueError("Unsupported file type. Please upload CSV, XLSX, or XLS.")


def detect_url_columns(df: pd.DataFrame) -> list[str]:
    """Return columns that appear to contain HTTP/HTTPS links."""
    url_columns: list[str] = []
    for col in df.columns:
        series = df[col].astype(str)
        has_url = series.str.contains(r"https?://", case=False, regex=True, na=False).any()
        if has_url:
            url_columns.append(col)
    return url_columns


def split_image_urls(df: pd.DataFrame, image_column: str) -> pd.DataFrame:
    """Explode comma-separated image URLs while duplicating all other row fields."""
    exploded = (
        df.assign(Img_Src=df[image_column].fillna("").astype(str).str.split(","))
        .explode("Img_Src", ignore_index=True)
    )

    exploded["Img_Src"] = exploded["Img_Src"].fillna("").astype(str).str.strip()
    exploded = exploded[exploded["Img_Src"] != ""].reset_index(drop=True)

    # Replace the source image column with cleaned single-image values.
    exploded[image_column] = exploded["Img_Src"]
    exploded = exploded.drop(columns=["Img_Src"])

    return exploded


uploaded_file = st.file_uploader(
    "Upload input file",
    type=["csv", "xlsx", "xls"],
    help="Supported formats: CSV, XLSX, XLS",
)

if uploaded_file is not None:
    try:
        df = read_uploaded_file(uploaded_file)
    except Exception as exc:
        st.error(f"Could not read the file: {exc}")
        st.stop()

    st.subheader("Preview (first 5 rows)")
    st.dataframe(df.head(5), use_container_width=True)

    if df.empty:
        st.warning("The uploaded file is empty.")
        st.stop()

    candidate_columns = detect_url_columns(df)

    if candidate_columns:
        default_col = candidate_columns[0]
        help_text = "Detected URL-like columns are preselected."
        column_options = list(df.columns)
    else:
        default_col = df.columns[0]
        help_text = "No URL-like column detected automatically. Please choose the correct column."
        column_options = list(df.columns)

    selected_column = st.selectbox(
        "Select the column containing comma-separated image URLs",
        options=column_options,
        index=column_options.index(default_col),
        help=help_text,
    )

    if st.button("Split URLs and Prepare Output", type="primary"):
        output_df = split_image_urls(df, selected_column)

        st.subheader("Output Preview (first 5 rows)")
        st.dataframe(output_df.head(5), use_container_width=True)

        csv_data = output_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download Output CSV (UTF-8)",
            data=csv_data,
            file_name="shopify_image_rows_expanded.csv",
            mime="text/csv",
        )

        st.success(
            f"Done. Input rows: {len(df):,} | Output rows: {len(output_df):,}. "
            "All non-image fields are duplicated for each split image row."
        )
else:
    st.info("Upload a CSV or Excel file to begin.")
