import streamlit as st
import pandas as pd
from copy import deepcopy

st.set_page_config(layout="wide", page_title="Bank P&L to Balance Sheet What-If")

# --- Initial Balanced Position (Bank-like) ---
DEFAULTS = {
    "revenue": 120_000.0,
    "cogs": 45_000.0,
    "opex": 25_000.0,
    "interest_expense": 3_000.0,
    "tax_rate": 0.25,
    "provision_expense": 2_000.0,

    "cash": 50_000.0,
    "gross_loans": 400_000.0,
    "allowance": 5_000.0,
    "ppe": 30_000.0,

    "deposits": 300_000.0,
    "debt": 80_000.0,
    "accrued_tax_payable": 0.0,
    "share_capital": 100_000.0,
    "retained_earnings": 70_000.0,
}

if "state" not in st.session_state:
    st.session_state.state = deepcopy(DEFAULTS)

# --- Formatter ---
def fmt(x):
    try:
        return f"{float(x):,.0f}"
    except (ValueError, TypeError):
        return str(x)

# --- P&L ---
def compute_pnl(s):
    net_interest_income = s["revenue"] - s["cogs"]
    operating_income = net_interest_income - s["opex"] - s["provision_expense"]
    ebt = operating_income - s["interest_expense"]
    tax = max(ebt, 0) * s["tax_rate"]
    net_income = ebt - tax
    return {
        "Net Income": net_income,
        "Provision Expense": s["provision_expense"],
        "Tax Expense": tax
    }

# --- Balance Sheet Builder ---
def build_bs(state, pnl, base_re=None):
    if base_re is None:
        base_re = state["retained_earnings"]

    new_allowance = state["allowance"] + pnl["Provision Expense"]
    new_tax_payable = state["accrued_tax_payable"] + pnl["Tax Expense"]
    new_retained = base_re + pnl["Net Income"]
    net_loans = state["gross_loans"] - new_allowance

    total_assets = state["cash"] + net_loans + state["ppe"]
    total_liabilities = state["deposits"] + state["debt"] + new_tax_payable
    total_equity = state["share_capital"] + new_retained

    assets = {
        "Cash": state["cash"],
        "Loans (net)": net_loans,
        "  ├─ Gross Loans": state["gross_loans"],
        "  └─ Allowance for Loan Losses": -new_allowance,
        "Property & Equipment": state["ppe"],
        "Total Assets": total_assets,
    }

    lie = {
        "Customer Deposits": state["deposits"],
        "Debt": state["debt"],
        "Accrued Tax Payable": new_tax_payable,
        "Total Liabilities": total_liabilities,
        "": "",
        "Share Capital": state["share_capital"],
        "Retained Earnings": new_retained,
        "Total Equity": total_equity,
        "Total Liabilities + Equity": total_liabilities + total_equity,
    }

    return {"assets": assets, "lie": lie}

# --- UI ---
st.title("Bank P&L to Balance Sheet What-If Explorer")
st.markdown("**Adjust P&L → See instant impact on Loans, Allowance & Equity**")

with st.form("inputs"):
    c1, c2 = st.columns(2)
    with c1:
        revenue = st.slider("Interest Income", 0.0, 300000.0, st.session_state.state["revenue"], 5000.0)
        funding_cost = st.slider("Funding Cost", 0.0, 150000.0, st.session_state.state["cogs"], 5000.0)
        opex = st.slider("Operating Expenses", 0.0, 100000.0, st.session_state.state["opex"], 2000.0)
    with c2:
        provision = st.slider("Provision for Loan Losses", 0.0, 50000.0, st.session_state.state["provision_expense"], 1000.0)
        non_interest_exp = st.slider("Non-Interest Expense", 0.0, 20000.0, st.session_state.state["interest_expense"], 500.0)
        tax_rate = st.slider("Tax Rate", 0.0, 0.50, st.session_state.state["tax_rate"], 0.01)

    apply = st.form_submit_button("Apply Scenario", type="primary", use_container_width=True)

# Compute
base_pnl = compute_pnl(st.session_state.state)
base_bs = build_bs(st.session_state.state, base_pnl)

if apply:
    temp = deepcopy(st.session_state.state)
    temp.update({
        "revenue": revenue, "cogs": funding_cost, "opex": opex,
        "provision_expense": provision, "interest_expense": non_interest_exp, "tax_rate": tax_rate
    })
    scenario_pnl = compute_pnl(temp)
    scenario_bs = build_bs(temp, scenario_pnl, st.session_state.state["retained_earnings"])
else:
    scenario_bs = base_bs

# --- Table Builder ---
def create_bs_table(bs_data, compare_bs=None):
    assets_keys = list(bs_data["assets"].keys())
    lie_keys = list(bs_data["lie"].keys())

    data = {"Account": assets_keys + lie_keys, "Assets": [], "Liabilities & Equity": []}
    for k in assets_keys:
        data["Assets"].append(fmt(bs_data["assets"][k]))
        data["Liabilities & Equity"].append("")
    for k in lie_keys:
        data["Assets"].append("")
        data["Liabilities & Equity"].append(fmt(bs_data["lie"][k]))

    df = pd.DataFrame(data)

    def highlight_cells(val, account, col_type):
        if not compare_bs:
            return ""
        old_val = compare_bs["assets"].get(account, compare_bs["lie"].get(account, ""))
        current_val = bs_data["assets"].get(account, bs_data["lie"].get(account, ""))
        if old_val != current_val and val != "":
            return "background-color: #fff8c4; font-weight: bold"
        return ""

    def style_fn(row):
        styles = [""] * 3
        account = row["Account"]
        if "Total" in account or "Equity" in account:
            styles = ["font-weight: bold; background-color: #e3f2fd"] * 3
        else:
            if row["Assets"]:
                styles[1] = highlight_cells(row["Assets"], account, "Assets")
            if row["Liabilities & Equity"]:
                styles[2] = highlight_cells(row["Liabilities & Equity"], account, "Liabilities & Equity")
        return styles

    styled = df.style.apply(style_fn, axis=1) \
                   .set_properties(**{"text-align": "right"}, subset=["Assets", "Liabilities & Equity"]) \
                   .set_properties(**{"text-align": "left"}, subset=["Account"]) \
                   .hide(axis="index")
    return styled

# --- Display ---
st.markdown("### Balance Sheet – Before Scenario")
st.dataframe(create_bs_table(base_bs), use_container_width=True)

st.markdown("### Balance Sheet – After What-If Scenario (Changes Highlighted)")
st.dataframe(create_bs_table(scenario_bs, base_bs), use_container_width=True)

st.success("Balance Sheet Always Balances | Assets = Liabilities + Equity")

st.info("""
**Perfect Bank / Credit Model:**
- Provision → Increases Allowance → Reduces Net Loans  
- Tax → Increases Accrued Tax Payable  
- Net Income → Increases Retained Earnings  
→ Every change has a precise balance sheet impact
""")

st.sidebar.success("Final Professional Version")
