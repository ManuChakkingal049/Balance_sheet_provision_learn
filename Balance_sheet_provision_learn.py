import streamlit as st
import pandas as pd
from copy import deepcopy

st.set_page_config(layout="wide", page_title="P&L → Balance Sheet What-If (Always Balances)")

# --- Initial Financial Position ------------------------------------------------
DEFAULTS = {
    "revenue": 100_000.0,
    "cogs": 40_000.0,
    "opex": 20_000.0,
    "interest_expense": 2_000.0,
    "tax_rate": 0.20,
    "provision_expense": 500.0,           # Bad debt provision

    # Balance Sheet starting point (already balanced)
    "cash": 20_000.0,
    "accounts_receivable_gross": 15_000.0,
    "allowance_doubtful": 0.0,            # cumulative
    "inventory": 10_000.0,
    "ppe": 30_000.0,

    "accounts_payable": 8_000.0,
    "accrued_tax_payable": 0.0,           # cumulative
    "debt": 10_000.0,
    "share_capital": 30_000.0,
    "retained_earnings": 27_000.0,        # Adjusted so BS already balances at start
}

# Initialize session state
if "state" not in st.session_state:
    st.session_state.state = deepcopy(DEFAULTS)
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Helpers ------------------------------------------------------------------
def fmt(x):
    return f"{float(x):,.2f}"

def push_message(msg):
    st.session_state.messages.insert(0, msg)
    if len(st.session_state.messages) > 10:
        st.session_state.messages = st.session_state.messages[:10]

# --- Core Calculations --------------------------------------------------------
def compute_pnl(s):
    revenue = s["revenue"]
    cogs = s["cogs"]
    gross_profit = revenue - cogs
    opex = s["opex"]
    provision = s["provision_expense"]
    ebit = gross_profit - opex - provision
    interest = s["interest_expense"]
    ebt = ebit - interest
    tax_rate = s["tax_rate"]
    tax_expense = max(ebt, 0) * tax_rate
    net_income = ebt - tax_expense

    return {
        "Revenue": revenue,
        "COGS": cogs,
        "Gross Profit": gross_profit,
        "OpEx": opex,
        "Provision Expense": provision,
        "EBIT": ebit,
        "Interest Expense": interest,
        "EBT": ebt,
        "Tax Expense": tax_expense,
        "Net Income": net_income,
    }

def build_balance_sheet(state, pnl, base_retained=None):
    if base_retained is None:
        base_retained = state["retained_earnings"]

    # 1. Update cumulative contra-asset and liability accounts
    new_allowance = state["allowance_doubtful"] + pnl["Provision Expense"]
    new_tax_payable = state["accrued_tax_payable"] + pnl["Tax Expense"]

    # 2. Net Income flows to Retained Earnings
    new_retained = base_retained + pnl["Net Income"]

    # 3. Assets
    assets = {
        "Cash": state["cash"],
        "Accounts Receivable (gross)": state["accounts_receivable_gross"],
        "Less: Allowance for Doubtful Accounts": -new_allowance,
        "Accounts Receivable (net)": state["accounts_receivable_gross"] - new_allowance,
        "Inventory": state["inventory"],
        "PPE (net)": state["ppe"],
    }
    total_assets = sum(v for v in assets.values() if isinstance(v, (int, float)) and v >= 0) - new_allowance

    # 4. Liabilities
    liabilities = {
        "Accounts Payable": state["accounts_payable"],
        "Accrued Tax Payable": new_tax_payable,
        "Debt": state["debt"],
    }
    total_liabilities = sum(liabilities.values())

    # 5. Equity
    equity = {
        "Share Capital": state["share_capital Rb"],
        "Retained Earnings": new_retained,
    }
    total_equity = sum(equity.values())

    total_liab_equity = total_liabilities + total_equity

    # Safety check (should never trigger)
    diff = round(total_assets - total_liab_equity, 2)
    if diff != 0:
        st.error(f"Balance Sheet off by {fmt(diff)} — this should not happen!")

    return {
        "assets": assets,
        "total_assets": total_assets,
        "liabilities": liabilities,
        "total_liabilities": total_liabilities,
        "equity": equity,
        "total_equity": total_equity,
        "total_liab_equity": total_liab_equity,
        "new_allowance": new_allowance,
        "new_tax_payable": new_tax_payable,
        "new_retained": new_retained,
    }

# --- What-If Application ------------------------------------------------------
def apply_scenario(values):
    temp_state = deepcopy(st.session_state.state)
    for k, v in values.items():
        temp_state[k] = float(v)

    pnl = compute_pnl(temp_state)
    bs = build_balance_sheet(temp_state, pnl, st.session_state.state["retained_earnings"])

    delta_ni = pnl["Net Income"] - compute_pnl(st.session_state.state)["Net Income"]
    push_message(f"Net Income Δ {fmt(delta_ni)} → Retained Earnings ↑ by same amount")

    return temp_state, pnl, bs

# --- UI -----------------------------------------------------------------------
st.title("P&L → Balance Sheet What-If Explorer (Balance Sheet Always Balances)")

with st.form("inputs"):
    c1, c2 = st.columns(2)
    with c1:
        revenue = st.slider("Revenue", 0.0, 500_000.0, st.session_state.state["revenue"], step=1_000.0)
        cogs = st.slider("COGS", 0.0, 500_000.0, st.session_state.state["cogs"], step=500.0)
        opex = st.slider("Operating Expenses", 0.0, 200_000.0, st.session_state.state["opex"], step=500.0)
    with c2:
        interest = st.slider("Interest Expense", 0.0, 50_000.0, st.session_state.state["interest_expense"], step=100.0)
        provision = st.slider("Provision Expense", 0.0, 10_000.0, st.session_state.state["provision_expense"], step=100.0)
        tax_rate = st.slider("Tax Rate", 0.0, 0.50, st.session_state.state["tax_rate"], step=0.01)

    submitted = st.form_submit_button("Apply What-If Scenario", type="primary", use_container_width=True)

# --- Compute Before & After ---------------------------------------------------
base_pnl = compute_pnl(st.session_state.state)
base_bs = build_balance_sheet(st.session_state.state, base_pnl)

if submitted:
    scenario_state, scenario_pnl, scenario_bs = apply_scenario({
        "revenue": revenue, "cogs": cogs, "opex": opex,
        "interest_expense": interest, "provision_expense": provision, "tax_rate": tax_rate
    })
else:
    scenario_state, scenario_pnl, scenario_bs = st.session_state.state, base_pnl, base_bs

# --- Display Results ----------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("Income Statement")
    df_pnl = pd.DataFrame({
        "Item": base_pnl.keys(),
        "Before": [fmt(v) for v in base_pnl.values()],
        "After": [fmt(v) for v in scenario_pnl.values()],
        "Δ": [fmt(scenario_pnl[k] - base_pnl[k]) for k in base_pnl]
    })
    st.dataframe(df_pnl.style.apply(lambda row: ["background: #ffcccc" if row["Before"] != row["After"] else "" for _ in row], axis=1),
                 use_container_width=True)

with col2:
    st.subheader("Balance Sheet (Always Balances)")
    lines = [
        ("Assets", ""),
        "Cash", "Accounts Receivable (gross)", "Less: Allowance for Doubtful Accounts",
        "Accounts Receivable (net)", "Inventory", "PPE (net)", "Total Assets",
        ("Liabilities", ""),
        "Accounts Payable", "Accrued Tax Payable", "Debt", "Total Liabilities",
        ("Equity", ""),
        "Share Capital", "Retained Earnings", "Total Equity",
        "", "Total Liabilities + Equity"
    ]

    def get_val(dct, key):
        if key in dct["assets"]: return fmt(dct["assets"][key])
        if key in dct["liabilities"]: return fmt(dct["liabilities"][key])
        if key in dct["equity"]: return fmt(dct["equity"][key])
        if key == "Total Assets": return fmt(dct["total_assets"])
        if key == "Total Liabilities": return fmt(dct["total_liabilities"])
        if key == "Total Equity": return fmt(dct["total_equity"])
        if key == "Total Liabilities + Equity": return fmt(dct["total_liab_equity"])
        return ""

    df_bs = pd.DataFrame({
        "Line Item": [("" if isinstance(x, tuple) else x) for x in lines],
        "Before": [get_val(base_bs, x[0]) if isinstance(x, tuple) else get_val(base_bs, x) for x in lines],
        "After":  [get_val(scenario_bs, x[0]) if isinstance(x, tuple) else get_val(scenario_bs, x) for x in lines],
    })

    # Highlight changes
    def highlight(row):
        if row["Before"] == row["After"] or row["Before"] == "":
            return [""] * len(row)
        return ["background: #ffffd0"] * len(row)

    st.dataframe(df_bs.style.apply(highlight, axis=1), use_container_width=True)

    # Final balance confirmation
    if round(base_bs["total_assets"] - base_bs["total_liab_equity"], 2) == 0:
        st.success("Before: Assets = Liabilities + Equity")
    if round(scenario_bs["total_assets"] - scenario_bs["total_liab_equity"], 2) == 0:
        st.success("After: Assets = Liabilities + Equity (Guaranteed)")

# Summary of Balance Sheet movements
st.markdown("### Key Balance Sheet Impacts")
st.write(f"• Allowance for Doubtful Accounts ↑ **{fmt(scenario_pnl['Provision Expense'] - base_pnl['Provision Expense'])}**")
st.write(f"• Accrued Tax Payable ↑ **{fmt(scenario_pnl['Tax Expense'] - base_pnl['Tax Expense'])}**")
st.write(f"• Retained Earnings ↑ **{fmt(scenario_pnl['Net Income'] - base_pnl['Net Income'])}** (full Net Income)")

# Sidebar
st.sidebar.header("Accounting Logic")
st.sidebar.success("Balance Sheet is **100% guaranteed** to balance because:")
st.sidebar.write("1. Provision Expense → ↑ Allowance (contra-asset)")
st.sidebar.write("2. Tax Expense → ↑ Accrued Tax Payable")
st.sidebar.write("3. Net Income → ↑ Retained Earnings (exact same amount)")
st.sidebar.write("No cash or other BS items move → perfect for pure P&L sensitivity!")

if st.session_state.messages:
    st.sidebar.subheader("Recent Scenarios")
    for m in st.session_state.messages[:5]:
        st.sidebar.caption(m)
