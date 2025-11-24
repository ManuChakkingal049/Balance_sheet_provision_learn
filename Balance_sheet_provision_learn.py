import streamlit as st
import pandas as pd
from copy import deepcopy

st.set_page_config(layout="wide", page_title="P&L & Balance Sheet Interactive Explorer")

# --- Helpers and defaults -------------------------------------------------
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

# Initialize session state
for key in ['state', 'prev', 'messages']:
    if key not in st.session_state:
        st.session_state[key] = deepcopy(DEFAULTS) if key != 'messages' else []

# --- Helpers ---------------------------------------------------------------
def fmt(x):
    try:
        return f"{float(x):,.2f}"
    except:
        return str(x)

# --- Accounting logic -----------------------------------------------------
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

def compute_balance_sheet(s, include_retained=True):
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

    retained = float(s.get("retained_earnings", 0)) if include_retained else 0.0
    equity = {
        "Share Capital": float(s.get("share_capital", 0)),
        "Retained Earnings": retained,
    }
    total_equity = sum(equity.values())

    return assets, liabilities, equity, total_assets, total_liabilities, total_equity

def balance_sheet_gap(s):
    _, _, _, total_assets, total_liabilities, total_equity = compute_balance_sheet(s)
    return total_assets - (total_liabilities + total_equity)

# --- Apply changes --------------------------------------------------------
def push_message(msg):
    st.session_state.messages.insert(0, msg)
    if len(st.session_state.messages) > 12:
        st.session_state.messages = st.session_state.messages[:12]

def apply_changes(new_vals, auto_balance_cash=True):
    s = st.session_state.state
    prev = st.session_state.prev

    # Track if provision changed
    provision_changed = False
    delta_provision = float(new_vals.get("provision_expense", 0)) - float(prev.get("provision_expense", 0))
    if abs(delta_provision) > 0.005:
        s["provision_expense"] = float(new_vals["provision_expense"])
        push_message(f"Provision changed by {fmt(delta_provision)}. Automatically affects P&L and Equity.")
        provision_changed = True

    # Update other P&L and balance sheet items
    for key in ["revenue", "cogs", "opex", "interest_expense", "tax_rate",
                "cash", "accounts_receivable", "inventory", "ppe",
                "accounts_payable", "debt", "share_capital"]:
        s[key] = float(new_vals.get(key, s.get(key, 0)))

    # Recompute Net Income and update Retained Earnings
    pnl_before = compute_pnl(prev).get("Net Income", 0)
    pnl_after = compute_pnl(s).get("Net Income", 0)
    delta_net_income = pnl_after - pnl_before
    if abs(delta_net_income) > 0.005:
        s["retained_earnings"] += delta_net_income
        push_message(f"Net Income changed by {fmt(delta_net_income)}. Retained Earnings updated automatically.")

    # Auto-balance Cash
    gap = balance_sheet_gap(s)
    if auto_balance_cash and abs(gap) > 0.005:
        s["cash"] -= gap
        push_message(f"Auto-balancing: Cash adjusted by {-gap:,.2f} to maintain balance.")

    st.session_state.prev = deepcopy(s)
    return provision_changed

# --- UI -------------------------------------------------------------------
st.title("Interactive P&L & Balance Sheet Explorer 📊")
st.write("Learn how the income statement and balance sheet connect. Edit values and watch the effects flow through.")

col1, col2 = st.columns([1, 1])

with col1:
    st.header("Profit & Loss (Income Statement)")
    with st.form(key="pnl_form"):
        rev = st.number_input("Revenue", value=st.session_state.state["revenue"], format="%.2f")
        cogs = st.number_input("COGS", value=st.session_state.state["cogs"], format="%.2f")
        opex = st.number_input("Operating Expenses", value=st.session_state.state["opex"], format="%.2f")
        interest = st.number_input("Interest Expense", value=st.session_state.state["interest_expense"], format="%.2f")
        provision = st.slider("Provision Expense", min_value=0.0, max_value=5000.0, value=st.session_state.state["provision_expense"], step=100.0)
        tax_rate = st.slider("Tax rate", min_value=0.0, max_value=0.5, value=float(st.session_state.state["tax_rate"]), step=0.01)
        submitted_pnl = st.form_submit_button("Apply P&L changes")

with col2:
    st.header("Balance Sheet")
    with st.form(key="bs_form"):
        cash = st.number_input("Cash", value=st.session_state.state["cash"], format="%.2f")
        ar = st.number_input("Accounts Receivable", value=st.session_state.state["accounts_receivable"], format="%.2f")
        inv = st.number_input("Inventory", value=st.session_state.state["inventory"], format="%.2f")
        ppe = st.number_input("PPE (net)", value=st.session_state.state["ppe"], format="%.2f")
        ap = st.number_input("Accounts Payable", value=st.session_state.state["accounts_payable"], format="%.2f")
        debt = st.number_input("Debt", value=st.session_state.state["debt"], format="%.2f")
        share_cap = st.number_input("Share Capital", value=st.session_state.state["share_capital"], format="%.2f")
        auto_balance = st.checkbox("Auto-balance balance sheet by adjusting Cash", value=True)
        submitted_bs = st.form_submit_button("Apply Balance Sheet changes")

provision_changed = False
if submitted_pnl or submitted_bs:
    new_vals = {
        "revenue": rev, "cogs": cogs, "opex": opex, "interest_expense": interest, "provision_expense": provision, "tax_rate": tax_rate,
        "cash": cash, "accounts_receivable": ar, "inventory": inv, "ppe": ppe,
        "accounts_payable": ap, "debt": debt, "share_capital": share_cap
    }
    provision_changed = apply_changes(new_vals, auto_balance_cash=auto_balance)

# Display P&L and Balance Sheet side by side
col3, col4 = st.columns([1, 1])

with col3:
    st.subheader("Assets")
    assets, liabilities, equity, total_assets, total_liabilities, total_equity = compute_balance_sheet(st.session_state.state)
    left_df = pd.DataFrame(list(assets.items()), columns=["Assets", "Amount"])
    left_df.loc['Total'] = ['Total Assets', total_assets]
    left_df["Amount"] = left_df["Amount"].map(fmt)
    st.table(left_df)

with col4:
    st.subheader("Liabilities & Equity")
    right_df = pd.DataFrame(list(liabilities.items()) + list(equity.items()), columns=["Liabilities & Equity", "Amount"])
    right_df.loc['Total'] = ['Total Liabilities + Equity', total_liabilities + total_equity]
    right_df["Amount"] = right_df["Amount"].map(fmt)
    st.table(right_df)

# P&L below balance sheet
st.subheader("Income Statement")
pnl_df = pd.DataFrame(list(compute_pnl(st.session_state.state).items()), columns=["Line", "Amount"])
pnl_df["Amount"] = pnl_df["Amount"].map(fmt)
st.table(pnl_df)
