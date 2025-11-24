import streamlit as st
import pandas as pd
from copy import deepcopy

st.set_page_config(layout="wide", page_title="P&L & Balance Sheet Interactive Explorer")

# --- Defaults ------------------------------------------------------------
DEFAULTS = {
    "revenue": 100000.0,
    "cogs": 40000.0,
    "opex": 20000.0,
    "interest_expense": 2000.0,
    "tax_rate": 0.20,
    "provision_expense": 500.0,
    "cash": 20000.0,
    "accounts_receivable": 15000.0,
    "inventory": 10000.0,
    "ppe": 30000.0,
    "accounts_payable": 8000.0,
    "debt": 10000.0,
    "share_capital": 30000.0,
    "retained_earnings": 12000.0,
}

for key in ['state', 'prev', 'messages', 'prev_bs']:
    if key not in st.session_state:
        if key == 'messages':
            st.session_state[key] = []
        else:
            st.session_state[key] = deepcopy(DEFAULTS)

# --- Helpers ------------------------------------------------------------
def fmt(x):
    try:
        return f"{float(x):,.2f}"
    except:
        return str(x)

# --- Accounting ---------------------------------------------------------
def compute_pnl(s):
    revenue = float(s.get("revenue", 0))
    cogs = float(s.get("cogs", 0))
    gross_profit = revenue - cogs
    opex = float(s.get("opex", 0))
    provision_expense = float(s.get("provision_expense", 0))
    ebit = gross_profit - opex - provision_expense
    interest = float(s.get("interest_expense", 0))
    ebt = ebit - interest
    tax_rate = float(s.get("tax_rate", 0))
    tax = max(0.0, ebt) * tax_rate
    net_income = ebt - tax
    return {
        "Revenue": revenue,
        "COGS": cogs,
        "Gross Profit": gross_profit,
        "Operating Expenses": opex,
        "Provision Expense": provision_expense,
        "EBIT": ebit,
        "Interest Expense": interest,
        "EBT": ebt,
        "Tax": tax,
        "Net Income": net_income,
    }

def compute_balance_sheet(s, pnl_component=0.0, old_retained=0.0):
    assets = {
        "Cash": float(s.get("cash", 0)),
        "Accounts Receivable (gross)": float(s.get("accounts_receivable", 0)),
        "Less: Allowance for Doubtful Accounts": -float(s.get("provision_expense", 0)),
        "Inventory": float(s.get("inventory", 0)),
        "PPE (net)": float(s.get("ppe", 0)),
    }
    total_assets = sum(assets.values())

    liabilities = {
        "Accounts Payable": float(s.get("accounts_payable", 0)),
        "Debt": float(s.get("debt", 0)),
    }
    total_liabilities = sum(liabilities.values())

    retained = old_retained + pnl_component
    equity = {
        "Share Capital": float(s.get("share_capital", 0)),
        f"Retained Earnings (Old: {fmt(old_retained)} + P&L: {fmt(pnl_component)})": retained,
    }
    total_equity = sum(equity.values())

    return assets, liabilities, equity, total_assets, total_liabilities, total_equity

# --- Apply changes -----------------------------------------------------
def push_message(msg):
    if 'messages' not in st.session_state:
        st.session_state['messages'] = []
    st.session_state.messages.insert(0, msg)
    if len(st.session_state.messages) > 12:
        st.session_state.messages = st.session_state.messages[:12]

def apply_changes(new_vals):
    s = deepcopy(st.session_state.state)  # Copy state to simulate 'what if'

    for key in new_vals:
        s[key] = float(new_vals[key])

    new_net_income = compute_pnl(s).get("Net Income", 0)
    pnl_component = new_net_income

    push_message(f"This shows a 'What If' scenario: if these P&L items changed, Net Income would be {fmt(new_net_income)}, flowing fully into Retained Earnings.")

    return s, pnl_component

# --- UI ---------------------------------------------------------------
st.title("Interactive P&L & Balance Sheet Explorer 📊")
st.write("Use the sliders to explore 'What If' scenarios. The 'Before' snapshot remains fixed; 'After' reflects the scenario based on slider changes.")

st.header("Profit & Loss (Income Statement) - Adjust 'What If')")
with st.form(key="pnl_form"):
    slider_col1, slider_col2 = st.columns(2)
    with slider_col1:
        rev = st.slider("Revenue", min_value=0.0, max_value=500000.0, value=st.session_state.state["revenue"], step=1000.0)
        cogs = st.slider("COGS", min_value=0.0, max_value=500000.0, value=st.session_state.state["cogs"], step=500.0)
        opex = st.slider("Operating Expenses", min_value=0.0, max_value=200000.0, value=st.session_state.state["opex"], step=500.0)
    with slider_col2:
        interest = st.slider("Interest Expense", min_value=0.0, max_value=50000.0, value=st.session_state.state["interest_expense"], step=100.0)
        provision = st.slider("Provision Expense", min_value=0.0, max_value=5000.0, value=st.session_state.state["provision_expense"], step=100.0)
        tax_rate = st.slider("Tax rate", min_value=0.0, max_value=0.5, value=float(st.session_state.state["tax_rate"]), step=0.01)
    submitted_pnl = st.form_submit_button("Apply 'What If' Scenario")

# --- Prepare Before & After ---------------------------------------------
before_assets, before_liabilities, before_equity, _, _, _ = compute_balance_sheet(st.session_state.state, pnl_component=0.0, old_retained=st.session_state.state.get('retained_earnings',0))

if submitted_pnl:
    after_state, pnl_component = apply_changes({"revenue": rev, "cogs": cogs, "opex": opex, "interest_expense": interest, "provision_expense": provision, "tax_rate": tax_rate})
    after_assets, after_liabilities, after_equity, _, _, _ = compute_balance_sheet(after_state, pnl_component, st.session_state.state.get('retained_earnings',0))
else:
    after_assets, after_liabilities, after_equity = before_assets, before_liabilities, before_equity

# --- Display Balance Sheet Before & After --------------------------------
col1, col2 = st.columns([1,1])
with col1:
    st.markdown("**Assets - Before / After**")
    df_assets = pd.DataFrame({
        "Line Item": list(before_assets.keys()),
        "Before": [fmt(before_assets.get(k,0)) for k in before_assets.keys()],
        "After": [fmt(after_assets[k]) for k in after_assets.keys()]
    })
    st.table(df_assets.style.apply(lambda row: ['background-color: yellow' if row['Before'] != row['After'] else '' for _ in row], axis=1))

with col2:
    st.markdown("**Liabilities & Equity - Before / After**")
    df_eq = pd.DataFrame({
        "Line Item": list(before_liabilities.keys()) + list(before_equity.keys()),
        "Before": [fmt(before_liabilities.get(k,0)) for k in before_liabilities.keys()] + [fmt(before_equity.get(k,0)) for k in before_equity.keys()],
        "After": [fmt(after_liabilities[k]) for k in after_liabilities.keys()] + [fmt(after_equity[k]) for k in after_equity.keys()]
    })
    st.table(df_eq.style.apply(lambda row: ['background-color: yellow' if row['Before'] != row['After'] else '' for _ in row], axis=1))

# --- Display P&L --------------------------------------------------------
st.subheader("Income Statement (After Scenario)")
pnl_after = compute_pnl(after_state if submitted_pnl else st.session_state.state)
pnl_df = pd.DataFrame(list(pnl_after.items()), columns=["Line", "Amount"])
pnl_df["Amount"] = pnl_df["Amount"].map(fmt)
st.table(pnl_df)

# Sidebar Explanation
st.sidebar.header("Explanation")
st.sidebar.write("The 'Before' snapshot shows current financials. Adjust the sliders to explore 'What If' scenarios. The 'After' columns reflect the impact on Net Income and Retained Earnings, illustrating how P&L changes propagate to the Balance Sheet.")
if st.session_state.messages:
    for m in st.session_state.messages:
        st.sidebar.write(f"- {m}")
