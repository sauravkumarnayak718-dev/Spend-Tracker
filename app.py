import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials
from datetime import date

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="My Spend Tracker", page_icon="💳", layout="wide")

# --- CSS FOR MODERN LOOK ---
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
    }
</style>
""", unsafe_allow_html=True)

# --- AUTHENTICATION ---
# The app looks for 'credentials.json' in the same folder
# --- AUTHENTICATION (Cloud + Local Support) ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# Check if running in Streamlit Cloud (uses Secrets)
if "gcp_service_account" in st.secrets:
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
# Fallback to local file if running on your computer
else:
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)

client = gspread.authorize(creds)

# --- SIDEBAR SETUP ---
st.sidebar.title("🔧 Settings")
sheet_url = st.sidebar.text_input("Google Sheet Name", "Spend Tracker Database")

if not sheet_url:
    st.warning("Please enter your Google Sheet Name in the sidebar.")
    st.stop()

try:
    # Open the sheet - Make sure you shared the sheet with the client_email in json!
    sheet = client.open(sheet_url).sheet1
except Exception as e:
    st.error(f"Could not connect to sheet. Did you share it with the API email? Error: {e}")
    st.stop()

# --- LOAD DATA FUNCTION ---
def load_data():
    data = sheet.get_all_records()
    if not data:
        return pd.DataFrame(columns=["Date", "Item", "Category", "Amount", "Type", "Notes"])
    df = pd.DataFrame(data)
    
    # Clean Data
    if 'Amount' in df.columns:
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        
    return df

df = load_data()

# --- APP TABS ---
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📈 Analysis", "➕ Add Expense"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.header("Financial Overview")
    
    if df.empty:
        st.info("No data found. Go to 'Add Expense' to start tracking!")
    else:
        # Key Metrics
        total_spend = df[df['Type'] == 'Expense']['Amount'].sum()
        total_income = df[df['Type'] == 'Income']['Amount'].sum()
        balance = total_income - total_spend
        
        col1, col2, col3 = st.columns(3)
        col1.metric("💸 Total Expense", f"₹{total_spend:,.2f}")
        col2.metric("💰 Total Income", f"₹{total_income:,.2f}")
        col3.metric("🏦 Balance", f"₹{balance:,.2f}", delta_color="normal")
        
        st.divider()
        
        # Recent Transactions
        st.subheader("Recent Activity")
        st.dataframe(df.sort_values(by="Date", ascending=False).head(5), use_container_width=True)

# --- TAB 2: ANALYSIS ---
with tab2:
    st.header("Deep Dive Analysis")
    
    if df.empty:
        st.info("Add data to see analytics.")
    else:
        # Filter for Expenses Only
        expenses = df[df['Type'] == 'Expense'].copy()
        
        # 1. Spending by Category (Pie Chart)
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.subheader("Where is money going?")
            fig_pie = px.pie(expenses, values='Amount', names='Category', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        # 2. Monthly Trend (Bar Chart)
        with col_b:
            st.subheader("Monthly Spending Trend")
            expenses['Month'] = expenses['Date'].dt.to_period('M').astype(str)
            monthly_data = expenses.groupby('Month')['Amount'].sum().reset_index()
            fig_bar = px.bar(monthly_data, x='Month', y='Amount', text_auto='.2s', color='Amount')
            st.plotly_chart(fig_bar, use_container_width=True)

        # 3. Category Breakdown Table
        st.subheader("Category Breakdown")
        cat_breakdown = expenses.groupby('Category')['Amount'].sum().reset_index().sort_values(by='Amount', ascending=False)
        st.dataframe(cat_breakdown, use_container_width=True)

# --- TAB 3: ADD TRANSACTION ---
with tab3:
    st.header("Add New Transaction")
    
    with st.form("entry_form", clear_on_submit=True):
        col_in1, col_in2 = st.columns(2)
        
        with col_in1:
            date_in = st.date_input("Date", date.today())
            item_in = st.text_input("Item Name (e.g. Coffee)")
            amount_in = st.number_input("Amount", min_value=0.0, format="%.2f")
        
        with col_in2:
            type_in = st.selectbox("Type", ["Expense", "Income", "Investment"])
            category_in = st.selectbox("Category", ["Food", "Transport", "Rent", "Bills", "Shopping", "Salary", "Other"])
            notes_in = st.text_area("Notes")
            
        submitted = st.form_submit_button("💾 Save Transaction")
        
        if submitted:
            # Prepare data row
            new_row = [str(date_in), item_in, category_in, amount_in, type_in, notes_in]
            try:
                sheet.append_row(new_row)
                st.success("Transaction Saved!")
                # Rerun to update dashboard immediately
                st.rerun() 
            except Exception as e:

                st.error(f"Error saving to Google Sheet: {e}")
