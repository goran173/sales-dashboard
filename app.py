import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from utils.helpers import format_currency, format_number, calculate_growth

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Sales Dashboard",
    page_icon="📊",
    layout="wide"
)

# --- CUSTOM STYLING ---
st.markdown("""
    <style>
    /* Sidebar multiselect chips */
    [data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    /* Sidebar multiselect labels */
    [data-testid="stSidebar"] label p {
        color: #FFFFFF !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- TITLE & SUBTITLE ---
st.title("Sales Analytics Dashboard")
st.markdown("### Interactive analysis of retail sales performance")

# --- PLACEHOLDER FOR KPIs (Loaded after data filtering) ---
kpi_placeholder = st.empty()

# --- DATA LOADING ---
@st.cache_data
def load_data():
    """
    Loads the Superstore Sales dataset from a URL or local fallback.
    """
    url = "https://raw.githubusercontent.com/leonism/sample-superstore/refs/heads/master/data/superstore.csv"
    local_path = "data/superstore.csv"
    
    # List of alternative URLs since the main one is often unstable
    fallbacks = [
        "https://raw.githubusercontent.com/plotly/datasets/master/superstore.csv",
        "https://raw.githubusercontent.com/dataprofessor/data/master/superstore.csv",
        "https://raw.githubusercontent.com/jeon-yh/superstore-analysis/master/superstore.csv"
    ]
    
    try:
        # Try primary URL
        df = pd.read_csv(url)
        return df
    except Exception as e:
        st.warning(f"Primary URL failed: {e}. Trying fallbacks...")
        
        for fallback_url in fallbacks:
            for enc in [None, 'cp1252', 'latin1']:
                try:
                    df = pd.read_csv(fallback_url, encoding=enc)
                    return df
                except:
                    continue
                
        # Final local fallback
        if os.path.exists(local_path):
            for enc in [None, 'cp1252', 'latin1']:
                try:
                    return pd.read_csv(local_path, encoding=enc)
                except:
                    continue
        
        st.error("No dataset found. Please ensure data/superstore.csv exists.")
        return pd.DataFrame()

# Load dataset
df = load_data()

if not df.empty:
    # --- DATA CLEANING ---
    # Drop rows where critical info is missing
    df = df.dropna(subset=["Order Date", "Sales", "Region", "Category"])
    
    # Handle NaNs in other categorical columns to avoid sorting errors
    cat_cols = ["Region", "State", "Category", "Sub-Category", "Segment"]
    for col in cat_cols:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown").astype(str)

    # --- DATE PARSING ---
    df["Order Date"] = pd.to_datetime(df["Order Date"])
    df["Ship Date"] = pd.to_datetime(df["Ship Date"])
    
    # --- SIDEBAR FILTERS ---
    st.sidebar.header("Filters 🔍")

    # Reset Button logic
    def reset_filters():
        for key in ["f_date", "f_region", "f_state", "f_cat", "f_subcat", "f_seg"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    if st.sidebar.button("Reset All Filters", use_container_width=True):
        reset_filters()
    
    # 1. Date Range
    min_date = df["Order Date"].min().date()
    max_date = df["Order Date"].max().date()
    
    date_range = st.sidebar.date_input(
        "Select Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key="f_date"
    )
    
    # 2. Region
    regions = sorted(df["Region"].unique())
    selected_regions = st.sidebar.multiselect("Region", options=regions, default=regions, key="f_region")
    
    # 3. State (Hierarchy: Region -> State)
    state_options = sorted(df[df["Region"].isin(selected_regions)]["State"].unique()) if selected_regions else []
    selected_states = st.sidebar.multiselect("State", options=state_options, default=state_options, key="f_state")
    
    # 4. Category
    categories = sorted(df["Category"].unique())
    selected_categories = st.sidebar.multiselect("Category", options=categories, default=categories, key="f_cat")
    
    # 5. Sub-Category (Hierarchy: Category -> Sub-Category)
    sub_category_options = sorted(df[df["Category"].isin(selected_categories)]["Sub-Category"].unique()) if selected_categories else []
    selected_sub_categories = st.sidebar.multiselect("Sub-Category", options=sub_category_options, default=sub_category_options, key="f_subcat")
    
    # 6. Segment
    segments = sorted(df["Segment"].unique())
    selected_segments = st.sidebar.multiselect("Segment", options=segments, default=segments, key="f_seg")
    
    # --- APPLY FILTERS ---
    try:
        start_date, end_date = date_range
    except ValueError:
        st.error("Please select a valid date range (start and end date).")
        st.stop()
        
    mask = (
        (df["Order Date"].dt.date >= start_date) & 
        (df["Order Date"].dt.date <= end_date) &
        (df["Region"].isin(selected_regions)) &
        (df["State"].isin(selected_states)) &
        (df["Category"].isin(selected_categories)) &
        (df["Sub-Category"].isin(selected_sub_categories)) &
        (df["Segment"].isin(selected_segments))
    )
    
    df_filtered = df.loc[mask].copy()
    
    # Sidebar footer info
    st.sidebar.markdown("---")
    st.sidebar.write(f"Showing {format_number(len(df_filtered))} of {format_number(len(df))} total orders")

    # --- MAIN CONTENT ---
    if not df_filtered.empty:
        # --- KPI CALCULATIONS ---
        # Split period in half
        min_date_f = df_filtered["Order Date"].min()
        max_date_f = df_filtered["Order Date"].max()
        midpoint = min_date_f + (max_date_f - min_date_f) / 2
        
        df_recent = df_filtered[df_filtered["Order Date"] > midpoint]
        df_prior = df_filtered[df_filtered["Order Date"] <= midpoint]
        
        def get_metrics(data):
            rev = data["Sales"].sum()
            prof = data["Profit"].sum()
            orders = data["Order ID"].nunique()
            margin = (prof / rev * 100) if rev != 0 else 0
            return rev, prof, orders, margin
            
        rev_r, prof_r, ord_r, marg_r = get_metrics(df_recent)
        rev_p, prof_p, ord_p, marg_p = get_metrics(df_prior)
        
        d_rev = calculate_growth(rev_r, rev_p)
        d_prof = calculate_growth(prof_r, prof_p)
        d_ord = calculate_growth(ord_r, ord_p)
        d_marg = marg_r - marg_p
        
        with kpi_placeholder.container():
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Revenue", format_currency(rev_r), f"{d_rev:.1f}%")
            col2.metric("Total Profit", format_currency(prof_r), f"{d_prof:.1f}%")
            col3.metric("Total Orders", format_number(ord_r), f"{d_ord:.1f}%")
            col4.metric("Profit Margin", f"{marg_r:.1f}%", f"{d_marg:.1f} pts")
            st.divider()

        # --- SECTION 1: TRENDS & CATEGORIES ---
        st.header("Revenue Insights")
        col_left, col_right = st.columns(2)
        
        with col_left:
            # Monthly Revenue Trend
            df_trend = df_filtered.set_index("Order Date").resample("ME")["Sales"].sum().reset_index()
            df_trend["Trend"] = df_trend["Sales"].rolling(window=3).mean()
            
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=df_trend["Order Date"], y=df_trend["Sales"],
                mode='lines+markers', name='Monthly Sales',
                line=dict(color='royalblue', width=2)
            ))
            fig_trend.add_trace(go.Scatter(
                x=df_trend["Order Date"], y=df_trend["Trend"],
                mode='lines', name='3-Mo Trend',
                line=dict(color='firebrick', width=2, dash='dash')
            ))
            fig_trend.update_layout(
                title="Monthly Revenue Trend", template="plotly_white",
                xaxis_title="Month-Year", yaxis_title="Sales ($)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_trend, use_container_width=True)
            
        with col_right:
            # Revenue by Category
            df_cat = df_filtered.groupby("Category")["Sales"].sum().reset_index()
            total_rev = df_filtered["Sales"].sum()
            fig_donut = px.pie(
                df_cat, values="Sales", names="Category", hole=0.4,
                title="Revenue by Category",
                color_discrete_sequence=px.colors.qualitative.Prism
            )
            fig_donut.update_traces(textposition='inside', textinfo='percent+label')
            fig_donut.add_annotation(
                text=f"Total<br>{format_currency(total_rev)}",
                showarrow=False, font_size=14
            )
            fig_donut.update_layout(template="plotly_white")
            st.plotly_chart(fig_donut, use_container_width=True)
            
        st.divider()

        # --- SECTION 2: GEOGRAPHIC & PRODUCT ---
        st.header("Geographic & Product Analysis")
        # Top 15 States by Revenue
        df_state = df_filtered.groupby("State").agg({"Sales": "sum", "Profit": "sum"}).reset_index()
        df_state["Profit Margin (%)"] = (df_state["Profit"] / df_state["Sales"]) * 100
        df_state = df_state.sort_values("Sales", ascending=False).head(15)
        
        fig_state = px.bar(
            df_state, x="Sales", y="State", orientation='h',
            color="Profit Margin (%)", color_continuous_scale="RdYlGn",
            title="Top 15 States by Revenue (colored by profit margin)",
            template="plotly_white", text_auto='.2s'
        )
        fig_state.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_state, use_container_width=True)

        st.divider()

        # --- SECTION 3: PROFITABILITY ---
        st.header("Product & Profitability Analysis")
        col_prod_left, col_prod_right = st.columns(2)
        
        with col_prod_left:
            # Top 10 Sub-Categories
            df_sub = df_filtered.groupby("Sub-Category").agg({"Sales": "sum", "Profit": "sum"}).reset_index()
            df_sub["Margin (%)"] = (df_sub["Profit"] / df_sub["Sales"]) * 100
            df_sub = df_sub.sort_values("Sales", ascending=False).head(10)
            
            fig_sub = px.bar(
                df_sub, x="Sales", y="Sub-Category", orientation='h',
                color="Profit", color_continuous_scale="RdYlGn",
                title="Top 10 Sub-Categories by Revenue",
                template="plotly_white", text=df_sub["Margin (%)"].apply(lambda x: f"{x:.1f}%")
            )
            fig_sub.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_sub, use_container_width=True)
            
        with col_prod_right:
            # Profit Matrix
            df_scatter = df_filtered.groupby(["Sub-Category", "Category"]).agg({
                "Sales": "sum", "Profit": "sum", "Order ID": "nunique"
            }).reset_index()
            fig_scatter = px.scatter(
                df_scatter, x="Sales", y="Profit", size="Order ID", color="Category",
                hover_name="Sub-Category", title="Profitability Matrix: Sales vs Profit",
                template="plotly_white"
            )
            fig_scatter.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig_scatter, use_container_width=True)
            
        # Treemap
        df_tree = df_filtered.groupby(["Category", "Sub-Category"]).agg({"Sales": "sum", "Profit": "sum"}).reset_index()
        df_tree["Margin (%)"] = (df_tree["Profit"] / df_tree["Sales"]) * 100
        fig_tree = px.treemap(
            df_tree, path=["Category", "Sub-Category"], values="Sales",
            color="Margin (%)", color_continuous_scale="RdYlGn",
            title="Revenue Treemap by Category & Sub-Category", template="plotly_white"
        )
        st.plotly_chart(fig_tree, use_container_width=True)

        st.divider()

        # --- SECTION 4: CUSTOMER SEGMENTS ---
        st.header("Customer Segment Analysis")
        col_seg_left, col_seg_right = st.columns(2)
        
        with col_seg_left:
            # Segment & Category
            df_seg = df_filtered.groupby(["Segment", "Category"])["Sales"].sum().reset_index()
            fig_seg = px.bar(
                df_seg, x="Segment", y="Sales", color="Category",
                title="Revenue by Customer Segment & Category",
                barmode="stack", template="plotly_white",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            st.plotly_chart(fig_seg, use_container_width=True)
            
        with col_seg_right:
            # Order Value & Margin
            df_seg_m = df_filtered.groupby("Segment").agg({
                "Sales": "sum", "Profit": "sum", "Order ID": "nunique"
            }).reset_index()
            df_seg_m["Avg Order Value"] = df_seg_m["Sales"] / df_seg_m["Order ID"]
            df_seg_m["Margin (%)"] = (df_seg_m["Profit"] / df_seg_m["Sales"]) * 100
            
            fig_seg_m = make_subplots(specs=[[{"secondary_y": True}]])
            fig_seg_m.add_trace(go.Bar(
                x=df_seg_m["Segment"], y=df_seg_m["Avg Order Value"],
                name="Avg Order Value ($)", marker_color="skyblue"
            ), secondary_y=False)
            fig_seg_m.add_trace(go.Scatter(
                x=df_seg_m["Segment"], y=df_seg_m["Margin (%)"],
                name="Profit Margin (%)", mode="lines+markers",
                line=dict(color="tomato", width=3)
            ), secondary_y=True)
            fig_seg_m.update_layout(
                title="Avg Order Value & Profit Margin by Segment",
                template="plotly_white",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig_seg_m.update_yaxes(title_text="Avg Order Value ($)", secondary_y=False)
            fig_seg_m.update_yaxes(title_text="Profit Margin (%)", secondary_y=True)
            st.plotly_chart(fig_seg_m, use_container_width=True)

        st.divider()

        # --- SECTION 5: PERFORMANCE SUMMARY ---
        st.header("Monthly Performance Summary")
        df_month = df_filtered.set_index("Order Date").resample("ME").agg({
            "Sales": "sum", "Profit": "sum", "Order ID": "nunique"
        }).reset_index()
        df_month["Avg Order Value"] = df_month["Sales"] / df_month["Order ID"]
        df_month["Profit Margin (%)"] = (df_month["Profit"] / df_month["Sales"]) * 100
        df_month["Month"] = df_month["Order Date"].dt.strftime("%B %Y")
        
        styled_table = df_month[["Month", "Sales", "Profit", "Order ID", "Avg Order Value", "Profit Margin (%)"]].style \
            .highlight_max(subset=["Sales", "Profit", "Profit Margin (%)"], color="#d4edda") \
            .highlight_min(subset=["Sales", "Profit", "Profit Margin (%)"], color="#f8d7da")
        
        st.dataframe(
            styled_table,
            column_config={
                "Sales": st.column_config.NumberColumn(format="$%.2f"),
                "Profit": st.column_config.NumberColumn(format="$%.2f"),
                "Avg Order Value": st.column_config.NumberColumn(format="$%.2f"),
                "Profit Margin (%)": st.column_config.NumberColumn(format="%.1f%%"),
                "Order ID": "Total Orders"
            },
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        # --- SECTION 6: DATA EXPLORER ---
        st.header("Detailed Data Explorer")
        with st.expander("🔍 View & Export Raw Data"):
            st.write(f"Showing {format_number(len(df_filtered))} records")
            csv = df_filtered.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Filtered Data as CSV",
                data=csv,
                file_name="superstore_filtered.csv",
                mime="text/csv"
            )
            st.dataframe(
                df_filtered,
                column_config={
                    "Sales": st.column_config.NumberColumn(format="$%.2f"),
                    "Profit": st.column_config.NumberColumn(format="$%.2f")
                },
                use_container_width=True
            )

    else:
        st.warning("⚠️ No data matches the selected filters. Please adjust your criteria.")

    # --- FOOTER ---
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray;'>"
        "Dashboard built with Streamlit & Plotly | Data: Sample Retail Dataset | Author: Antigravity AI"
        "</div>",
        unsafe_allow_html=True
    )
else:
    st.info("Upload or provide a valid superstore.csv file in the data/ directory.")
