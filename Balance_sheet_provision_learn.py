import streamlit as st
import pandas as pd
from copy import deepcopy

st.set_page_config(layout="wide", page_title="P&L & Balance Sheet Interactive Explorer")

# --- Helpers and defaults -------------------------------------------------
DEFAULTS = {
    # P&L
    "revenue": 100000.0,
    "cogs": 40000.0,
    "opex": 20000.0,
    "interest_expense": 2000.0,
    "tax_rate": 0.20,
    # Balance sheet
    "cash": 20000.0,
    "accounts_receivable": 15000.0,
    "inventory": 10000.0,
    "ppe": 30000.0,
    "allowance_for_doubtful_accounts": 500.0,  # contra-asset (provision)
    "accounts_payable": 8000.0,
    "debt": 10000.0,
    "share_capital": 30000.0,
    # retained earnings will be calculated from historical net income
    "retained_earnings": 12000.0,
}

if "state" not in st.session_state:
    st.session_state.state = deepcopy(DEFAULTS)
    st.session_state.prev = deepcopy(DEFAULTS)
    st.session_state.messages = []

# Utility for formatting
def fmt(x):
    return f"{x:,.2f}"

# --- Accounting logic -----------------------------------------------------

def compute_pnl(s):
    revenue = s["revenue"]
    cogs = s["cogs"]
    gross_profit = revenue - cogs
    opex = s["opex"]
    ebit = gross_profit - opex
    interest = s["interest_expense"]
    ebt = ebit - interest
    tax = max(0.0, ebt) * s["tax_rate"]
    net_income = ebt - tax
    return {
        "Revenue": revenue,
        "COGS": cogs,
        "Gross Profit": gross_profit,
        "Operating Expenses": opex,
        "EBIT": ebit,
        "Interest Expense": interest,
        "EBT": ebt,
        "Tax": tax,
        "Net Income": net_income,
    }


def compute_balance_sheet(s, include_retained=True):
    # Assets
    assets = {
        "Cash": s["cash"],
        "Accounts Receivable (gross)": s["accounts_receivable"],
        "Less: Allowance for Doubtful Accounts": -s["allowance_for_doubtful_accounts"],
        "Inventory": s["inventory"],
        "PPE (net)": s["ppe"],
    }
    total_assets = sum(assets.values())

    # Liabilities
    liabilities = {
        "Accounts Payable": s["accounts_payable"],
        "Debt": s["debt"],
    }
    total_liabilities = sum(liabilities.values())

    # Equity
    retained = s["retained_earnings"] if include_retained else 0.0
    equity = {
        "Share Capital": s["share_capital"],
        "Retained Earnings": retained,
    }
    total_equity = sum(equity.values())

    return assets, liabilities, equity, total_assets, total_liabilities, total_equity


def balance_sheet_gap(s):
    _, _, _, total_assets, total_liabilities, total_equity = compute_balance_sheet(s)
    return total_assets - (total_liabilities + total_equity)

# --- Interaction: when user updates values --------------------------------

def push_message(msg):
    st.session_state.messages.insert(0, msg)
    if len(st.session_state.messages) > 12:
        st.session_state.messages = st.session_state.messages[:12]


def apply_changes(new_vals, auto_balance_cash=True):
    # Compare previous to new to generate messages and update derived items
    prev = st.session_state.prev
    s = st.session_state.state

    # Detect P&L changes affecting retained earnings
    pnl_before = compute_pnl(prev)["Net Income"]
    pnl_after = compute_pnl(new_vals)["Net Income"]
    delta_net_income = pnl_after - pnl_before

    # If P&L changed, flow to retained earnings
    if abs(delta_net_income) > 0.005:
        s["retained_earnings"] += delta_net_income
        push_message(f"Net income changed by {fmt(delta_net_income)} and flows into Retained Earnings (Equity).")

    # If allowance (provision) changed, create provision expense effect on P&L
    delta_allowance = new_vals.get("allowance_for_doubtful_accounts", prev["allowance_for_doubtful_accounts"]) - prev["allowance_for_doubtful_accounts"]
    if abs(delta_allowance) > 0.005:
        # Increase in allowance => Provision expense (P&L) reduces net income and retained earnings
        # We'll model it as an immediate P&L expense reduction (bad debt expense)
        s["revenue"] = new_vals["revenue"]
        s["cogs"] = new_vals["cogs"]
        s["opex"] = new_vals["opex"] + delta_allowance  # record as additional expense
        s["allowance_for_doubtful_accounts"] = new_vals["allowance_for_doubtful_accounts"]
        push_message(f"Allowance for doubtful accounts changed by {fmt(delta_allowance)}. This increase is recorded as a provision (expense) which reduces Net Income and therefore Retained Earnings.")
    else:
        # copy P&L items
        s["revenue"] = new_vals["revenue"]
        s["cogs"] = new_vals["cogs"]
        s["opex"] = new_vals["opex"]
        s["interest_expense"] = new_vals["interest_expense"]
        s["tax_rate"] = new_vals["tax_rate"]
        s["allowance_for_doubtful_accounts"] = new_vals["allowance_for_doubtful_accounts"]

    # Copy balance sheet items
    s["accounts_receivable"] = new_vals["accounts_receivable"]
    s["inventory"] = new_vals["inventory"]
    s["ppe"] = new_vals["ppe"]
    s["accounts_payable"] = new_vals["accounts_payable"]
    s["debt"] = new_vals["debt"]
    s["share_capital"] = new_vals["share_capital"]

    # If user changed cash directly, accept it
    s["cash"] = new_vals["cash"]

    # Optionally auto-balance the balance sheet by adjusting cash
    gap = balance_sheet_gap(s)
    if auto_balance_cash:
        if abs(gap) > 0.005:
            old_cash = s["cash"]
            s["cash"] = old_cash - gap
            push_message(f"Auto-balancing: Cash adjusted by {-gap:,.2f} so Assets = Liabilities + Equity. This keeps the balance sheet balanced.")

    # Save prev snapshot
    st.session_state.prev = deepcopy(s)

# --- UI -------------------------------------------------------------------

st.title("Interactive P&L & Balance Sheet Explorer 📊")
st.write("Learn how the income statement and balance sheet connect. Edit values and watch the effects flow through.")

col1, col2 = st.columns([1, 1])

with col1:
    st.header("Profit & Loss (Income Statement)")
    with st.form(key="pnl_form"):
        rev = st.number_input("Revenue", value=st.session_state.state["revenue"], format="%.2f")
        cogs = st.number_input("COGS", value=st.session_state.state["cogs"], format="%.2f")
        opex = st.number_input("Operating Expenses (SG&A)", value=st.session_state.state["opex"], format="%.2f")
        interest = st.number_input("Interest Expense", value=st.session_state.state["interest_expense"], format="%.2f")
        tax_rate = st.slider("Tax rate", min_value=0.0, max_value=0.5, value=float(st.session_state.state["tax_rate"]), step=0.01)
        submitted_pnl = st.form_submit_button("Apply P&L changes")

with col2:
    st.header("Balance Sheet")
    with st.form(key="bs_form"):
        cash = st.number_input("Cash", value=st.session_state.state["cash"], format="%.2f")
        ar = st.number_input("Accounts Receivable (gross)", value=st.session_state.state["accounts_receivable"], format="%.2f")
        allowance = st.number_input("Allowance for Doubtful Accounts (provision)", value=st.session_state.state["allowance_for_doubtful_accounts"], format="%.2f")
        inv = st.number_input("Inventory", value=st.session_state.state["inventory"], format="%.2f")
        ppe = st.number_input("PPE (net)", value=st.session_state.state["ppe"], format="%.2f")
        ap = st.number_input("Accounts Payable", value=st.session_state.state["accounts_payable"], format="%.2f")
        debt = st.number_input("Debt", value=st.session_state.state["debt"], format="%.2f")
        share_cap = st.number_input("Share Capital", value=st.session_state.state["share_capital"], format="%.2f")
        retained = st.number_input("Retained Earnings (editable)", value=st.session_state.state["retained_earnings"], format="%.2f")
        auto_balance = st.checkbox("Auto-balance balance sheet by adjusting Cash", value=True)
        submitted_bs = st.form_submit_button("Apply Balance Sheet changes")

# When either form is submitted, collect current inputs and apply
if submitted_pnl or submitted_bs:
    new_vals = {
        "revenue": rev,
        "cogs": cogs,
        "opex": opex,
        "interest_expense": interest,
        "tax_rate": tax_rate,
        "cash": cash,
        "accounts_receivable": ar,
        "allowance_for_doubtful_accounts": allowance,
        "inventory": inv,
        "ppe": ppe,
        "accounts_payable": ap,
        "debt": debt,
        "share_capital": share_cap,
        "retained_earnings": retained,
    }
    apply_changes(new_vals, auto_balance_cash=auto_balance)

# Show computed statements
pnl = compute_pnl(st.session_state.state)
assets, liabilities, equity, total_assets, total_liabilities, total_equity = compute_balance_sheet(st.session_state.state)

col3, col4 = st.columns([1, 1])
with col3:
    st.subheader("Calculated Income Statement")
    pnl_df = pd.DataFrame(list(pnl.items()), columns=["Line", "Amount"]) 
    pnl_df["Amount"] = pnl_df["Amount"].map(lambda x: f"{x:,.2f}")
    st.table(pnl_df)

with col4:
    st.subheader("Calculated Balance Sheet")
    left = pd.DataFrame(list(assets.items()), columns=["Assets", "Amount"]) 
    right = pd.DataFrame(list(liabilities.items()) + list(equity.items()), columns=["Liabilities & Equity", "Amount"]) 
    left["Amount"] = left["Amount"].map(lambda x: f"{x:,.2f}")
    right["Amount"] = right["Amount"].map(lambda x: f"{x:,.2f}")
    st.markdown(f"**Total Assets:** {fmt(total_assets)}  \\ **Total Liabilities:** {fmt(total_liabilities)}  \\ **Total Equity:** {fmt(total_equity)}")
    st.write("Assets")
    st.table(left)
    st.write("Liabilities & Equity")
    st.table(right)

# Show balance check
gap = balance_sheet_gap(st.session_state.state)
if abs(gap) < 0.01:
    st.success("Balance Sheet balances: Assets = Liabilities + Equity")
else:
    st.error(f"Balance Sheet does NOT balance. Gap = {fmt(gap)} (Assets - Liabilities - Equity). Use Auto-balance or adjust items.")

# Explanations panel
st.sidebar.header("Explanations & Teaching Hints")
if st.session_state.messages:
    for m in st.session_state.messages:
        st.sidebar.write(f"- {m}")
else:
    st.sidebar.write("Make a change to see teaching messages appear here explaining the accounting flows.")

st.sidebar.markdown("---")
st.sidebar.header("Suggested Exercises")
st.sidebar.markdown(
"""
1. Increase Revenue and observe how Net Income and Retained Earnings increase.\n
2. Increase Allowance for Doubtful Accounts: notice it creates a provision (expense) and reduces Net Income and Retained Earnings, while reducing net Accounts Receivable on the Balance Sheet.\n
3. Add PPE purchase by reducing Cash and increasing PPE — observe that Assets don't change but the composition does.\n
4. Toggle Auto-balance to see manual vs automatic balancing behavior and learn why cash often absorbs timing differences.
"""
)

st.sidebar.markdown("---")
st.sidebar.header("Quick Notes")
st.sidebar.markdown(
"""
- Net Income flows to Retained Earnings (Equity) when profit is recognized.\n- Provisions (like allowance for doubtful accounts) create a P&L expense and a contra-asset on the Balance Sheet.\n- The Balance Sheet must always balance: Assets = Liabilities + Equity.\n"""
)

# Footer: small debug / state view if developer mode
if st.checkbox("Show internal state (developer)"):
    st.write(st.session_state.state)
    st.write("Messages:")
    st.write(st.session_state.messages)
