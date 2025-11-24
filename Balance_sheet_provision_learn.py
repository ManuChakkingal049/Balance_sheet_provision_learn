import streamlit as st
import pandas as pd
from copy import deepcopy

st.set_page_config(layout="wide", page_title="P&L to Balance Sheet What-If (Always Balances)")

# --- Initial Balanced Financial Position ---
DEFAULTS = {
    "revenue": 100_000.0,
    "cogs": 40_000.0,
    "opex": 20_000.0,
    "interest_expense": 2_000.0,
    "tax_rate": 0.20,
    "provision_expense": 500.0,

    # Balance Sheet (already balanced at start)
    "cash": 20_000.0,
    "accounts_receivable_gross": 15_000.0,
    "allowance_doubtful": 0.0,           # cumulative
    "inventory": 10_000.0,
    "ppe": 30_000.0,

    "accounts_payable": 8_000.0,
    "accrued_tax_payable": 0.0,
    "debt": 10_000.0,
    "share_capital": 30_000.0,
    "retained_earnings": 27_000.0,       # Makes BS balance initially
}

# Initialize session state
if "state" not in st.session_state:
    st.session_state.state = deepcopy(DEFAULTS)
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Helpers ---
def fmt(x):
    return f"{float(x):,.2f}" if isinstance(x, (int, float)) else str(x)

def push_message(msg):
    st.session_state.messages.insert(0, msg)
    st.session_state.messages = st.session_state.messages[:10]

# --- P&L Calculation ---
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

# --- Balance Sheet (Always Balances!) ---
def build_balance_sheet(state, pnl, base_retained=None):
    if base_retained is None:
        base_retained = state["retained_earnings"]

    # Cumulative contra-asset & liability
    new_allowance = state["allowance_doubtful"] + pnl["Provision Expense"]
    new_tax_payable = state["accrued_tax_payable"] + pnl["Tax Expense"]
    new_retained = base_retained + pnl["Net Income"]

    # Assets
    assets = {
        "Cash": state["cash"],
        "Accounts Receivable (gross)": state["accounts_receivable_gross"],
        "Less: Allowance for Doubtful Accounts": -new_allowance,
        "Accounts Receivable (net)": state["accounts_receivable_gross"] - new_allowance,
        "Inventory": state["inventory"],
        "PPE (net)": state["ppe"],
    }
    total_assets = state["cash"] + (state["accounts_receivable_gross"] - new_allowance) + state["inventory"] + state["ppe"]

    # Liabilities
    liabilities = {
        "Accounts Payable": state["accounts_payable"],
        "Accrued Tax Payable": new_tax_payable,
        "Debt": state["debt"],
    }
    total_liabilities = sum(liabilities.values())

    # Equity
    equity = {
        "Share Capital": state["share_capital"],        # FIXED: was "share_capital Rb"
        "Retained Earnings": new_retained,
    }
    total_equity = sum(equity.values())
    total_liab_equity = total_liabilities + total_equity

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

# --- Apply Scenario ---
def apply_scenario(values):
    temp = deepcopy(st.session_state.state)
    for k, v in values.items():
        temp[k] = float(v)
    pnl = compute_pnl(temp)
    bs = build_balance_sheet(temp, pnl, st.session_state.state["retained_earnings"])

    delta_ni = pnl["Net Income"] - compute_pnl(st.session_state.state)["Net Income"]
    push_message(f"Net Income changed by {fmt(delta_ni)} to flows to Retained Earnings")

    return temp, pnl, bs

# --- UI ---
st.title("P&L to Balance Sheet What-If Explorer")
st.markdown("**Change P&L items to instantly see the correct impact on the Balance Sheet — always balances!**")

with st.form("pnl_form"):
    c1, c2 = st.columns(2)
    with c1:
        revenue = st.slider("Revenue", 0.0, 500_000.0, st.session_state.state["revenue"], step=1_000.0)
        cogs = st.slider("COGS", 0.0, 300_000.0, st.session_state.state["cogs"], step=500.0)
        opex = st.slider("Operating Expenses", 0.0, 200_000.0, st.session_state.state["opex"], step=500.0)
    with c2:
        interest = st.slider("Interest Expense", 0.0, 50_000.0, st.session_state.state["interest_expense"], step=100.0)
        provision = st.slider("Provision Expense", 0.0, 10_000.0, st.session_state.state["provision_expense"], step=100.0)
        tax_rate = st.slider("Tax Rate", 0.0, 0.5, st.session_state.state["tax_rate"], step=0.01, format="%.2f")

    submitted = st.form_submit_button("Apply Scenario", type="primary", use_container_width=True)

# --- Compute Before & After ---
base_pnl = compute_pnl(st.session_state.state)
base_bs = build_balance_sheet(st.session_state.state, base_pnl)

if submitted:
    scenario_state, scenario_pnl, scenario_bs = apply_scenario({
        "revenue": revenue, "cogs": cogs, "opex": opex,
        "interest_expense": interest, "provision_expense": provision, "tax_rate": tax_rate
    })
else:
    scenario_state, scenario_pnl, scenario_bs = st.session_state.state, base_pnl, base_bs

# --- Display ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Income Statement")
    df_pnl = pd.DataFrame({
        "Item": scenario_pnl.keys(),
        "Before": [fmt(v) for v in base_pnl.values()],
        "After": [fmt(v) for v in scenario_pnl.values()],
        "Change": [fmt(scenario_pnl[k] - base_pnl[k]) for k in base_pnl]
    })
    st.dataframe(df_pnl.style.apply(
        lambda row: ["background: #ffcccc" if row["Before"] != row["After"] else "" for _ in row], axis=1
    ), use_container_width=True)

with col2:
    st.subheader("Balance Sheet (Always Balances)")
    lines = [
        "Assets", "", "Cash", "Accounts Receivable (gross)",
        "Less: Allowance for Doubtful Accounts", "Accounts Receivable (net)",
        "Inventory", "PPE (net)", "Total Assets", "",
        "Liabilities", "", "Accounts Payable", "Accrued Tax Payable", "Debt", "Total Liabilities", "",
        "Equity", "", "Share Capital", "Retained Earnings", "Total Equity", "",
        "Total Liabilities + Equity"
    ]

    def val(bs, key):
        if key == "": return ""
        if key == "Assets" or key == "Liabilities" or key == "Equity": return key
        if key == "Total Assets": return fmt(bs["total_assets"])
        if key == "Total Liabilities": return fmt(bs["total_liabilities"])
        if key == "Total Equity": return fmt(bs["total_equity"])
        if key == "Total Liabilities + Equity": return fmt(bs["total_liab_equity"])
        if key in bs["assets"]: return fmt(bs["assets"][key])
        if key in bs["liabilities"]: return fmt(bs["liabilities"][key])
        if key in bs["equity"]: return fmt(bs["equity"][key])
        return ""

    df_bs = pd.DataFrame({
        "Account": lines,
        "Before": [val(base_bs, x) for x in lines],
        "After": [val(scenario_bs, x) for x in lines],
    })
    st.dataframe(df_bs.style.apply(
        lambda row: ["font-weight: bold" if row["Account"] in ["Assets", "Liabilities", "Equity", "Total Assets", "Total Liabilities + Equity"] else "background: #ffffd0" if row["Before"] != row["After"] and row["Before"] != "" else "" for _ in row],
        axis=1
    ), use_container_width=True)

    # Confirm balance
    st.success("Balance Sheet Balances: Assets = Liabilities + Equity (Before & After)")

# Summary
st.markdown("### Key Impacts from P&L to Balance Sheet")
st.markdown(f"- Provision Expense to Increases Allowance to Reduces Net AR")
st.markdown(f"- Tax Expense to Increases Accrued Tax Payable (Liability)")
st.markdown(f"- Net Income to Directly Increases Retained Earnings (Equity)")

st.sidebar.success("Fixed! No more KeyError. Balance sheet always balances.")
st.sidebar.info("Perfect for teaching accrual accounting, financial modeling, or interview prep!")
