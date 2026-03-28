"""
Streamlit Data Explorer
Upload any CSV → get instant statistics, interactive charts, and filtered export.
"""

import io
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Data Explorer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_CSV = Path(__file__).parent / "sample_data.csv"


@st.cache_data(show_spinner=False)
def load_csv(content: bytes) -> pd.DataFrame:
    """Parse CSV bytes into a DataFrame with dtype inference."""
    df = pd.read_csv(io.BytesIO(content))
    # Attempt to parse columns that look like dates
    for col in df.columns:
        if df[col].dtype == object and df[col].str.match(r"\d{4}-\d{2}-\d{2}").any():
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass
    return df


def describe_df(df: pd.DataFrame) -> pd.DataFrame:
    """Extended describe — includes nulls and dtype info."""
    desc = df.describe(include="all").T
    desc["null_count"] = df.isnull().sum()
    desc["null_pct"] = (df.isnull().mean() * 100).round(1).astype(str) + "%"
    desc["dtype"] = df.dtypes.astype(str)
    return desc


def numeric_cols(df: pd.DataFrame) -> list[str]:
    return df.select_dtypes(include="number").columns.tolist()


def categorical_cols(df: pd.DataFrame) -> list[str]:
    return df.select_dtypes(include=["object", "category"]).columns.tolist()


def datetime_cols(df: pd.DataFrame) -> list[str]:
    return df.select_dtypes(include="datetime").columns.tolist()


# ---------------------------------------------------------------------------
# Sidebar — upload & filters
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("📊 Data Explorer")
    st.caption("Upload a CSV to get started.")

    uploaded = st.file_uploader("Upload CSV", type=["csv"])

    if not uploaded and SAMPLE_CSV.exists():
        use_sample = st.button("Use sample dataset")
        if use_sample:
            uploaded = open(SAMPLE_CSV, "rb")  # type: ignore[assignment]
    elif not uploaded:
        st.info("No sample_data.csv found. Upload a file to begin.")

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

df: Optional[pd.DataFrame] = None

if uploaded is not None:
    raw = uploaded.read() if hasattr(uploaded, "read") else uploaded
    try:
        df = load_csv(raw if isinstance(raw, bytes) else raw.encode())
    except Exception as exc:
        st.error(f"Could not parse CSV: {exc}")

# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------

if df is None:
    st.markdown(
        """
        ## Welcome to Data Explorer
        Upload a CSV file from the sidebar to:
        - View instant **summary statistics**
        - Plot **interactive charts** (histogram, scatter, bar, line)
        - **Filter rows** with a visual editor
        - **Export** filtered data as CSV
        """
    )
    st.stop()

# ---------------------------------------------------------------------------
# Dataset overview
# ---------------------------------------------------------------------------

st.subheader("Dataset Overview")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Rows", f"{len(df):,}")
col2.metric("Columns", len(df.columns))
col3.metric("Numeric cols", len(numeric_cols(df)))
col4.metric("Missing values", f"{df.isnull().sum().sum():,}")

with st.expander("Preview (first 100 rows)", expanded=True):
    st.dataframe(df.head(100), use_container_width=True)

with st.expander("Summary Statistics"):
    st.dataframe(describe_df(df), use_container_width=True)

# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Visualize")

chart_type = st.selectbox(
    "Chart type",
    ["Histogram", "Bar chart", "Scatter plot", "Line chart", "Box plot", "Correlation heatmap"],
)

num_cols = numeric_cols(df)
cat_cols = categorical_cols(df)
dt_cols = datetime_cols(df)

fig = None

if chart_type == "Histogram":
    if num_cols:
        col = st.selectbox("Column", num_cols)
        bins = st.slider("Bins", 5, 100, 30)
        fig = px.histogram(df, x=col, nbins=bins, title=f"Distribution of {col}")
    else:
        st.warning("No numeric columns found.")

elif chart_type == "Bar chart":
    if cat_cols and num_cols:
        x_col = st.selectbox("Category (X)", cat_cols)
        y_col = st.selectbox("Value (Y)", num_cols)
        agg = st.selectbox("Aggregation", ["sum", "mean", "count", "max", "min"])
        agg_df = df.groupby(x_col)[y_col].agg(agg).reset_index().sort_values(y_col, ascending=False).head(20)
        fig = px.bar(agg_df, x=x_col, y=y_col, title=f"{agg.capitalize()} of {y_col} by {x_col}")
    else:
        st.warning("Need at least one categorical and one numeric column.")

elif chart_type == "Scatter plot":
    if len(num_cols) >= 2:
        x_col = st.selectbox("X axis", num_cols, index=0)
        y_col = st.selectbox("Y axis", num_cols, index=min(1, len(num_cols) - 1))
        color_col = st.selectbox("Color by (optional)", ["None"] + cat_cols + num_cols)
        fig = px.scatter(
            df,
            x=x_col,
            y=y_col,
            color=None if color_col == "None" else color_col,
            title=f"{x_col} vs {y_col}",
            opacity=0.7,
        )
    else:
        st.warning("Need at least two numeric columns.")

elif chart_type == "Line chart":
    x_options = dt_cols + num_cols
    if x_options and num_cols:
        x_col = st.selectbox("X axis (date or numeric)", x_options)
        y_col = st.selectbox("Y axis", num_cols)
        fig = px.line(df.sort_values(x_col), x=x_col, y=y_col, title=f"{y_col} over {x_col}")
    else:
        st.warning("Need at least one date/numeric X and one numeric Y column.")

elif chart_type == "Box plot":
    if num_cols:
        y_col = st.selectbox("Numeric column", num_cols)
        group_col = st.selectbox("Group by (optional)", ["None"] + cat_cols)
        fig = px.box(
            df,
            y=y_col,
            x=None if group_col == "None" else group_col,
            title=f"Distribution of {y_col}",
        )
    else:
        st.warning("No numeric columns found.")

elif chart_type == "Correlation heatmap":
    if len(num_cols) >= 2:
        corr = df[num_cols].corr()
        fig = px.imshow(
            corr,
            text_auto=".2f",
            color_continuous_scale="RdBu_r",
            title="Correlation Matrix",
            aspect="auto",
        )
    else:
        st.warning("Need at least two numeric columns.")

if fig:
    fig.update_layout(template="plotly_dark", height=420)
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Filter & Export
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Filter & Export")

filter_col = st.selectbox("Filter column", df.columns.tolist())
col_series = df[filter_col]

filtered_df = df.copy()

if pd.api.types.is_numeric_dtype(col_series):
    min_val, max_val = float(col_series.min()), float(col_series.max())
    low, high = st.slider(
        f"Range for {filter_col}",
        min_value=min_val,
        max_value=max_val,
        value=(min_val, max_val),
    )
    filtered_df = df[(col_series >= low) & (col_series <= high)]

elif pd.api.types.is_object_dtype(col_series):
    options = col_series.dropna().unique().tolist()
    selected = st.multiselect(f"Values for {filter_col}", options, default=options[:10])
    if selected:
        filtered_df = df[col_series.isin(selected)]

st.caption(f"Showing {len(filtered_df):,} of {len(df):,} rows after filter.")
st.dataframe(filtered_df.head(200), use_container_width=True)

csv_bytes = filtered_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download filtered CSV",
    data=csv_bytes,
    file_name="filtered_export.csv",
    mime="text/csv",
)
