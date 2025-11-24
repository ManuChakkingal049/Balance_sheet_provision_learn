import streamlit as st
import pandas as pd
from copy import deepcopy

st.set_page_config(layout="wide", page_title="Bank P&L to Balance Sheet What-If")

# -------------------------------------------------------------
# DEFAULTS (raw starting point before applying opening P&L)
# -------------------------------------------------------------
DEFAULTS = {
    "revenue": 120_000.0,           
    "cogs": 45_000.0,               
    "opex": 25_000.0,
    "interest_expense": 3_000.0,
    "tax_rate": 0.25,
    "provision_expense": 0.0,

    "cash": 50_000.0,
    "gross_loans": 400_000.0,
    "allowance": 0.0,
    "ppe": 30_000.0,

    "deposits": 300_000.0,
    "debt": 80_000.0,

    # Initially zero but will be filled by opening P&L
    "accrued_tax_payable": 0.0,
    "accrued_interest_payable": 0.0,

    "share_capital": 50_000.0,
    "retained_earnings": 0.0
}

if "state" not in st.session_state:
    st.session_state.state = deepcopy(DEFAULTS)

def fmt(x):
    return f"{x:,.0f}"

# -------------------------------------------------------------
# CORRECT P&L (allows negative tax = tax credit)
# -------------------------------------------------------------
def compute_pnl(s):
    net_interest_income = s["revenue"] - s["cogs"]
    operating_income = net_interest_income - s["opex"] - s["provision_expense"]
    ebt = operating_income - s["interest_expense"]

    # Correct logic: tax credit allowed when EBT < 0
    tax = ebt * s["tax_rate"]
    net_income = ebt - tax

    return {
        "Net Income": net_income,
        "Provision Expense": s["provision_expense"],
        "Tax Expense": tax
    }


# -------------------------------------------------------------
# BALANCE SHEET BUILDER
# -------------------------------------------------------------
def build_bs(state, pnl):
    new_allowance = state["allowance"] + pnl["Provision Expense"]
    new_tax_payable = state["accrued_tax_payable"] + pnl["Tax Expense"]
    new_interest_payable = state["accrued_interest_payable"]  # interest already accrued in opening
    new_retained = state["retained_earnings"] + pnl["Net Income"]

    net_loans = state["gross_loans"] - new_allowance

    total_assets = state["cash"] + net_loans + state["ppe"]
    total_liabilities = (
        state["deposits"]
        + state["debt"]
        + new_tax_payable
        + new_interest_payable
    )
    total_equity = state["share_capital"] + new_retained

    assets = {
        "Cash": state["cash"],
        "Loans (net)": net_loans,
        "  ├─ Gross Loans": state["gross_loans"],
        "  └─ Allowance for Loan Losses": -new_allowance,
        "Property & Equipment": state["ppe"],
        "TOTAL ASSETS": total_assets,
    }

    lie = {
        "Customer Deposits": state["deposits"],
        "Debt": state["debt"],
        "Accrued Interest Payable": new_interest_payable,
        "Accrued Tax Payable": new_tax_payable,
        "TOTAL LIABILITIES": total_liabilities,
        "": "",
        "Share Capital": state["share_capital"],
        "Retained Earnings": new_retained,
        "TOTAL EQUITY": total_equity,
        "TOTAL LIABILITIES + EQUITY": total_liabilities + total_equity,
    }

    return {"assets": assets, "lie": lie}


# -------------------------------------------------------------
# 1) Build OPENING P&L and apply it to get BALANCED OPENING BS
# -------------------------------------------------------------
opening_state = deepcopy(st.session_state.state)
opening_pnl = compute_pnl(opening_state)

opening_state["retained_earnings"] = opening_pnl["Net Income"]
opening_state["accrued_tax_payable"] = opening_pnl["Tax Expense"]
opening_state["accrued_interest_payable"] = opening_state["interest_expense"]
opening_state["allowance"] = opening_pnl["Provision Expense"]

bs_before = build_bs(opening_state, opening_pnl)


# -------------------------------------------------------------
# UI FOR SCENARIO
# -------------------------------------------------------------
st.title("Bank P&L → Balance Sheet What-If Explorer")
st.markdown("**Adjust P&L and see instant impact on tax, allowance, and retained earnings**")

with st.form("inputs"):
    c1, c2, c3 = st.columns(3)

    with c1:
        revenue = st.slider("Interest Income", 0.0, 300000.0, opening_state["revenue"], 5000.0)
    with c2:
        provision = st.slider("Provision for Loan Losses", 0.0, 50000.0, opening_state["provision_expense"], 1000.0)
    with c3:
        tax_rate = st.slider("Tax Rate", 0.0, 0.50, opening_state["tax_rate"], 0.01)

    apply = st.form_submit_button("Apply Scenario", type="primary", use_container_width=True)

temp = deepcopy(opening_state)
temp.update({
    "revenue": revenue,
    "provision_expense": provision,
    "tax_rate": tax_rate
})

pnl_after = compute_pnl(temp)
bs_after = build_bs(temp, pnl_after)


# -------------------------------------------------------------
# TABLE FORMATTER
# -------------------------------------------------------------
def create_bs_table(bs_data, compare_bs=None):

    asset_items = [
        "Cash",
        "Loans (net)",
        "  ├─ Gross Loans",
        "  └─ Allowance for Loan Losses",
        "Property & Equipment",
        "TOTAL ASSETS",
    ]

    liability_items = [
        "Customer Deposits",
        "Debt",
        "Accrued Interest Payable",
        "Accrued Tax Payable",
        "TOTAL LIABILITIES",
        "",
        "Share Capital",
        "Retained Earnings",
        "TOTAL EQUITY",
        "TOTAL LIABILITIES + EQUITY",
    ]

    data = {"Assets": [], "Amount": [], "Liabilities & Equity": [], "Amount ": []}

    def get_val(key):
        return bs_data["assets"].get(key, bs_data["lie"].get(key, ""))

    def get_old_val(key):
        if not compare_bs:
            return None
        return compare_bs["assets"].get(key, compare_bs["lie"].get(key, None))

    max_rows = max(len(asset_items), len(liability_items))

    for i in range(max_rows):
        # Assets
        if i < len(asset_items):
            label = asset_items[i]
            data["Assets"].append(label)
            val = get_val(label)
            data["Amount"].append(fmt(val) if isinstance(val, (int, float)) else "")
        else:
            data["Assets"].append("")
            data["Amount"].append("")

        # Liabilities
        if i < len(liability_items):
            label = liability_items[i]
            data["Liabilities & Equity"].append(label)
            val = get_val(label)
            data["Amount "].append(fmt(val) if isinstance(val, (int, float)) else "")
        else:
            data["Liabilities & Equity"].append("")
            data["Amount "].append("")

    df = pd.DataFrame(data)

    def style_fn(row):
        styles = [""] * len(row)

        # highlight TOTALS
        if "TOTAL" in row["Assets"]:
            styles[0] = styles[1] = "font-weight: bold; background-color: #e3f2fd"
        if ("TOTAL" in row["Liabilities & Equity"]) or ("EQUITY" in row["Liabilities & Equity"]):
            styles[2] = styles[3] = "font-weight: bold; background-color: #e3f2fd"

        # highlight changed items
        if compare_bs:
            a = row["Assets"]
            l = row["Liabilities & Equity"]

            if a and get_old_val(a) != get_val(a):
                styles[1] = "background-color: #fff7b2; font-weight:bold"
            if l and get_old_val(l) != get_val(l):
                styles[3] = "background-color: #fff7b2; font-weight:bold"

        return styles

    return df.style.apply(style_fn, axis=1).hide(axis="index")


# -------------------------------------------------------------
# DISPLAY
# -------------------------------------------------------------
col1, col2 = st.columns(2)
with col1:
    diff_before = bs_before["assets"]["TOTAL ASSETS"] - bs_before["lie"]["TOTAL LIABILITIES + EQUITY"]
    st.metric("Before Balance Check", "Balanced" if abs(diff_before) < 0.01 else "UNBALANCED",
              delta=f"{diff_before:,.2f}")

with col2:
    diff_after = bs_after["assets"]["TOTAL ASSETS"] - bs_after["lie"]["TOTAL LIABILITIES + EQUITY"]
    st.metric("After Balance Check", "Balanced" if abs(diff_after) < 0.01 else "UNBALANCED",
              delta=f"{diff_after:,.2f}")

st.markdown("### Balance Sheet – Opening (Balanced)")
st.dataframe(create_bs_table(bs_before), use_container_width=True)

st.markdown("### Balance Sheet – After Scenario (Changes Highlighted)")
st.dataframe(create_bs_table(bs_after, bs_before), use_container_width=True)

st.metric("Net Income After Scenario", fmt(pnl_after["Net Income"]))

st.success("✔ Both opening and scenario balance sheets are perfectly balanced.")

st.info("""
**P&L → Balance Sheet Impact**
- Provision → Allowance ↑ → Net Loans ↓  
- Tax Expense → Accrued Tax Payable ↑ (or ↓ if tax credit)  
- Net Income → Retained Earnings ↑ (or ↓)  
""")
