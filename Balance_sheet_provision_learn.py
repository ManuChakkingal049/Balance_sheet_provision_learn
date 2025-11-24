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

for key in ['state', 'prev', 'messages']:
    if key not in st.session_state:
        st.session_state[key] = deepcopy(DEFAULTS) if key != 'messages' else []

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

def compute_balance_sheet(s, include_retained=True, old_retained=0.0, pnl_component=0.0):
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

    if include_retained:
        equity = {
            "Share Capital": float(s.get("share_capital", 0)),
            f"Retained Earnings (Old: {fmt(old_retained)} + P&L: {fmt(pnl_component)})": old_retained + pnl_component,
        }
    else:
        equity = {
            "Share Capital": float(s.get("share_capital", 0)),
            "Retained Earnings": 0.0,
        }
    total_equity = sum(equity.values())

    return assets, liabilities, equity, total_assets, total_liabilities, total_equity

def balance_sheet_gap(s):
    _, _, _, total_assets, total_liabilities, total_equity = compute_balance_sheet(s)
    return total_assets - (total_liabilities + total_equity)

# --- Apply changes -----------------------------------------------------
def push_message(msg):
    st.session_state.messages.insert(0, msg)
    if len(st.session_state.messages) > 12:
        st.session_state.messages = st.session_state.messages[:12]

def apply_changes(new_vals, auto_balance_cash=True):
    s = st.session_state.state
    prev = st.session_state.prev

    old_retained = s["retained_earnings"]
    old_net_income = compute_pnl(prev)["Net Income"]

    for key in new_vals:
        s[key] = float(new_vals[key])

    new_net_income = compute_pnl(s)["Net Income"]
    pnl_component = new_net_income - old_net_income

    if abs(pnl_component) > 0.01:
        s["retained_earnings"] = old_retained + pnl_component
        push_message(f"Net Income changed by {fmt(pnl_component)}. Retained Earnings updated automatically.")

    provision_changed = abs(float(new_vals.get("provision_expense",0)) - float(prev.get("provision_expense",0))) > 0.01
    if provision_changed:
        push_message(f"Provision changed by {fmt(float(new_vals.get('provision_expense',0)) - float(prev.get('provision_expense',0)))}. Affects P&L and reduces Accounts Receivable (Assets).")

    gap = balance_sheet_gap(s)
    if auto_balance_cash and abs(gap) > 0.01:
        s["cash"] -= gap
        push_message(f"Auto-balancing: Cash adjusted by {-gap:,.2f} to maintain balance.")

    st.session_state.prev = deepcopy(s)
    return provision_changed, pnl_component, old_retained

# --- UI ---------------------------------------------------------------
st.title("Interactive P&L & Balance Sheet Explorer 📊")
st.write("Edit values and see effects on P&L and Balance Sheet.")

col1, col2 = st.columns([1,1])

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
        auto_balance = st.checkbox("Auto-balance Cash", value=True)
        submitted_bs = st.form_submit_button("Apply Balance Sheet changes")

provision_changed = False
pnl_component = 0
old_retained = 0
if submitted_pnl or submitted_bs:
    new_vals = {"revenue": rev, "cogs": cogs, "opex": opex, "interest_expense": interest, "provision_expense": provision, "tax_rate": tax_rate,
                "cash": cash, "accounts_receivable": ar, "inventory": inv, "ppe": ppe,
                "accounts_payable": ap, "debt": debt, "share_capital": share_cap}
    provision_changed, pnl_component, old_retained = apply_changes(new_vals, auto_balance_cash=auto_balance)

# --- Display ------------------------------------------------------------
assets, liabilities, equity, total_assets, total_liabilities, total_equity = compute_balance_sheet(st.session_state.state, old_retained=old_retained, pnl_component=pnl_component)

col3, col4 = st.columns([1,1])
with col3:
    st.subheader("Assets")
    left_df = pd.DataFrame(list(assets.items()), columns=["Assets", "Amount"])
    left_df.loc['Total'] = ['Total Assets', total_assets]
    left_df["Amount"] = left_df["Amount"].map(fmt)
    def highlight_assets(row):
        if provision_changed and row['Assets'] == 'Less: Allowance for Doubtful Accounts':
            return ['background-color: yellow']*2
        return ['']*2
    st.table(left_df.style.apply(highlight_assets, axis=1))

with col4:
    st.subheader("Liabilities & Equity")
    right_df = pd.DataFrame(list(liabilities.items()) + list(equity.items()), columns=["Liabilities & Equity", "Amount"])
    right_df.loc['Total'] = ['Total Liabilities + Equity', total_liabilities + total_equity]
    right_df["Amount"] = right_df["Amount"].map(fmt)
    def highlight_equity(row):
        if row['Liabilities & Equity'].startswith('Retained Earnings'):
            return ['background-color: yellow']*2
        return ['']*2
    st.table(right_df.style.apply(highlight_equity, axis=1))

st.subheader("Income Statement")
pnl = compute_pnl(st.session_state.state)
pnl_df = pd.DataFrame(list(pnl.items()), columns=["Line", "Amount"])
pnl_df["Amount"] = pnl_df["Amount"].map(fmt)

def highlight_pnl(row):
    if provision_changed and row['Line'] == 'Provision Expense':
        return ['background-color: yellow']*2
    return ['']*2
st.table(pnl_df.style.apply(highlight_pnl, axis=1))

st.sidebar.header("Explanation")
if st.session_state.messages:
    for m in st.session_state.messages:
        st.sidebar.write(f"- {m}")
else:
    st.sidebar.write("Make a change to see how it affects P&L and Balance Sheet.")
