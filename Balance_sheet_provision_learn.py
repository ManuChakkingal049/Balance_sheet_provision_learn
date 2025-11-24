import streamlit as st
import pandas as pd
from copy import deepcopy

st.set_page_config(layout="wide", page_title="Bank P&L → Balance Sheet What-If")

# -------------------------------------------------------------------
# DEFAULT BALANCE SHEET + P&L STARTING POINT
# -------------------------------------------------------------------
DEFAULTS = {
    # P&L
    "revenue": 120_000.0,
    "cogs": 45_000.0,
    "opex": 25_000.0,
    "interest_expense": 3_000.0,
    "tax_rate": 0.25,
    "provision_expense": 0.0,

    # Assets
    "cash": 50_000.0,
    "gross_loans": 400_000.0,
    "allowance": 0.0,
    "ppe": 30_000.0,

    # Liabilities
    "deposits": 300_000.0,
    "debt": 80_000.0,
    "accrued_tax_payable": 0.0,

    # Equity
    "share_capital": 50_000.0,
    "retained_earnings": 0.0,
}

if "state" not in st.session_state:
    st.session_state.state = deepcopy(DEFAULTS)

def fmt(x):
    return f"{x:,.0f}" if isinstance(x, (int, float)) else ""

# -------------------------------------------------------------------
# CORRECT P&L WITH NEGATIVE TAX HANDLING
# -------------------------------------------------------------------
def compute_pnl(s):
    net_interest_income = s["revenue"] - s["cogs"]
    operating_income = net_interest_income - s["opex"] - s["provision_expense"]
    ebt = operating_income - s["interest_expense"]

    # ⭐ Tax can be negative (tax credit) when EBT < 0
    tax = ebt * s["tax_rate"]

    net_income = ebt - tax

    return {
        "Net Income": net_income,
        "Provision Expense": s["provision_expense"],
        "Tax Expense": tax
    }

# -------------------------------------------------------------------
# BALANCE SHEET BUILDER — FULLY CORRECT ACCOUNTING LOGIC
# -------------------------------------------------------------------
def build_bs(state, pnl):
    # Allowance increases by provision
    new_allowance = state["allowance"] + pnl["Provision Expense"]

    # Tax payable moves with tax expense (positive or negative)
    new_tax_payable = state["accrued_tax_payable"] + pnl["Tax Expense"]

    # Retained earnings update from AFTER-TAX net income
    new_retained = state["retained_earnings"] + pnl["Net Income"]

    # Asset: Net loans after updated allowance
    net_loans = state["gross_loans"] - new_allowance

    # Totals
    total_assets = state["cash"] + net_loans + state["ppe"]
    total_liabilities = state["deposits"] + state["debt"] + new_tax_payable
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
        "Accrued Tax Payable": new_tax_payable,
        "TOTAL LIABILITIES": total_liabilities,
        "": "",
        "Share Capital": state["share_capital"],
        "Retained Earnings": new_retained,
        "TOTAL EQUITY": total_equity,
        "TOTAL LIABILITIES + EQUITY": total_liabilities + total_equity,
    }

    return {"assets": assets, "lie": lie}

# -------------------------------------------------------------------
# UI INPUTS
# -------------------------------------------------------------------
st.title("Bank P&L → Balance Sheet What-If Explorer")
st.markdown("Adjust P&L and instantly see **balanced** loan, tax, and equity impact.")

with st.form("inputs"):
    st.subheader("Key P&L Inputs")

    c1, c2, c3 = st.columns(3)
    with c1:
        revenue = st.slider("Interest Income", 0.0, 300_000.0,
                            st.session_state.state["revenue"], 5_000.0)

    with c2:
        provision = st.slider("Provision for Loan Losses", 0.0, 50_000.0,
                              st.session_state.state["provision_expense"], 1_000.0)

    with c3:
        tax_rate = st.slider("Tax Rate", 0.0, 0.5,
                             st.session_state.state["tax_rate"], 0.01)

    apply = st.form_submit_button("Apply Scenario", type="primary", use_container_width=True)

# Temp updated state for "after"
temp_state = deepcopy(st.session_state.state)
temp_state.update({
    "revenue": revenue,
    "provision_expense": provision,
    "tax_rate": tax_rate
})

# Compute P&L
pnl = compute_pnl(temp_state)
bs_after = build_bs(temp_state, pnl)

# "Before" BS (clean default)
base_pnl = compute_pnl(st.session_state.state)
bs_before = build_bs(st.session_state.state, base_pnl)

# -------------------------------------------------------------------
# TABLE CREATOR
# -------------------------------------------------------------------
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
            data["Amount"].append(fmt(val))
        else:
            data["Assets"].append("")
            data["Amount"].append("")

        # Liabilities & Equity
        if i < len(liability_items):
            label = liability_items[i]
            data["Liabilities & Equity"].append(label)
            val = get_val(label)
            data["Amount "].append(fmt(val))
        else:
            data["Liabilities & Equity"].append("")
            data["Amount "].append("")

    df = pd.DataFrame(data)

    # Highlight logic
    def style_fn(row):
        styles = [""] * len(row)

        # Assets
        asset_label = row["Assets"]
        if asset_label and "TOTAL" in asset_label:
            styles[0] = styles[1] = "font-weight: bold; background-color: #e3f2fd"
        elif compare_bs and asset_label:
            old = get_old_val(asset_label)
            new = get_val(asset_label)
            if old is not None and old != new:
                styles[1] = "background-color: #fff8c4; font-weight: bold"

        # L+E
        lie_label = row["Liabilities & Equity"]
        if lie_label and ("TOTAL" in lie_label or "EQUITY" in lie_label):
            styles[2] = styles[3] = "font-weight: bold; background-color: #e3f2fd"
        elif compare_bs and lie_label:
            old = get_old_val(lie_label)
            new = get_val(lie_label)
            if old is not None and old != new:
                styles[3] = "background-color: #fff8c4; font-weight: bold"

        return styles

    return (
        df.style
        .apply(style_fn, axis=1)
        .set_properties(**{"text-align": "right"}, subset=["Amount", "Amount "])
        .set_properties(**{"text-align": "left"}, subset=["Assets", "Liabilities & Equity"])
        .hide(axis="index")
    )

# -------------------------------------------------------------------
# DISPLAY SECTION
# -------------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    diff_before = bs_before["assets"]["TOTAL ASSETS"] - bs_before["lie"]["TOTAL LIABILITIES + EQUITY"]
    st.metric("Before: Balanced?", "✓ Yes" if abs(diff_before) < 0.01 else "✗ No",
              delta=f"{diff_before:,.2f}")

with col2:
    diff_after = bs_after["assets"]["TOTAL ASSETS"] - bs_after["lie"]["TOTAL LIABILITIES + EQUITY"]
    st.metric("After: Balanced?", "✓ Yes" if abs(diff_after) < 0.01 else "✗ No",
              delta=f"{diff_after:,.2f}")

st.markdown("### Balance Sheet – BEFORE Scenario")
st.dataframe(create_bs_table(bs_before), use_container_width=True)

st.markdown("### Balance Sheet – AFTER What-If Scenario (Changes Highlighted)")
st.dataframe(create_bs_table(bs_after, bs_before), use_container_width=True)

st.metric("Calculated Net Income (After-Tax)", fmt(pnl["Net Income"]))

st.info("""
### How the Balance Sheet Balances  
**Provision Expense**
- ↑ Allowance (contra-asset)  
- ↓ Net Loans  
→ Assets ↓

**Tax Effect**
- If provision increases → taxable income ↓ → tax ↓  
- Accrued tax payable is reduced  
→ Liabilities ↓

**Net Income**
- After-tax income flows to retained earnings  
→ Equity ↓

Total movement in **Assets = Liabilities + Equity**.
""")
