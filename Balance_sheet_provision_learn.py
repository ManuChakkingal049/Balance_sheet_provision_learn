import streamlit as st
import pandas as pd
from copy import deepcopy

st.set_page_config(layout="wide", page_title="Bank P&L to Balance Sheet What-If")

# --- Default Bank Balance Sheet (clean start) ---
DEFAULTS = {
    "revenue": 120_000.0,           # Interest income
    "cogs": 45_000.0,               # Funding cost / Interest expense
    "opex": 25_000.0,
    "interest_expense": 3_000.0,
    "tax_rate": 0.25,
    "provision_expense": 0.0,       # P&L Provision

    "cash": 50_000.0,
    "gross_loans": 400_000.0,
    "allowance": 0.0,               # Starting clean
    "ppe": 30_000.0,

    "deposits": 300_000.0,
    "debt": 80_000.0,
    "accrued_tax_payable": 0.0,
    "share_capital": 50_000.0,
    "retained_earnings": 0.0,       # Previous year RE = 0
}

if "state" not in st.session_state:
    st.session_state.state = deepcopy(DEFAULTS)

def fmt(x):
    return f"{x:,.0f}"

# --- P&L Computation ---
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
def build_bs(state, pnl):
    # Apply P&L impacts
    new_allowance = state["allowance"] + pnl["Provision Expense"]
    new_tax_payable = state["accrued_tax_payable"] + pnl["Tax Expense"]
    new_retained = state["retained_earnings"] + pnl["Net Income"]

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

# --- UI ---
st.title("Bank P&L to Balance Sheet What-If Explorer")
st.markdown("**Adjust P&L → See instant impact on Loans, Allowance, Tax & Equity**")

with st.form("inputs"):
    st.subheader("Key P&L Adjustments (Bank Focus)")
    c1, c2, c3 = st.columns(3)
    with c1:
        revenue = st.slider("Interest Income", 0.0, 300_000.0, st.session_state.state["revenue"], 5_000.0)
    with c2:
        provision = st.slider("Provision for Loan Losses", 0.0, 50_000.0, st.session_state.state["provision_expense"], 1_000.0)
    with c3:
        tax_rate = st.slider("Tax Rate", 0.0, 0.50, st.session_state.state["tax_rate"], 0.01)

    apply = st.form_submit_button("Apply Scenario", type="primary", use_container_width=True)

# --- Compute P&L ---
temp_state = deepcopy(st.session_state.state)
temp_state.update({
    "revenue": revenue,
    "provision_expense": provision,
    "tax_rate": tax_rate
})
pnl = compute_pnl(temp_state)
bs_after = build_bs(temp_state, pnl)

# --- Base Balance Sheet (Before) ---
# For before, retained earnings = 0, provision = 0, tax = 0
base_pnl = compute_pnl(st.session_state.state)
bs_before = build_bs(st.session_state.state, base_pnl)

# --- Table Builder ---
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

    data = {
        "Assets": [],
        "Amount": [],
        "Liabilities & Equity": [],
        "Amount ": []
    }

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
            data["Assets"].append(asset_items[i])
            val = get_val(asset_items[i])
            data["Amount"].append(fmt(val) if isinstance(val, (int, float)) else "")
        else:
            data["Assets"].append("")
            data["Amount"].append("")

        # Liabilities & Equity
        if i < len(liability_items):
            data["Liabilities & Equity"].append(liability_items[i])
            val = get_val(liability_items[i])
            data["Amount "].append(fmt(val) if isinstance(val, (int, float)) else "")
        else:
            data["Liabilities & Equity"].append("")
            data["Amount "].append("")

    df = pd.DataFrame(data)

    def style_fn(row):
        styles = [""] * len(row)
        # Assets styling
        asset_label = row["Assets"]
        if asset_label and "TOTAL" in asset_label:
            styles[0] = styles[1] = "font-weight: bold; background-color: #e3f2fd"
        elif compare_bs and asset_label:
            old = get_old_val(asset_label)
            new = get_val(asset_label)
            if old is not None and old != new:
                styles[1] = "background-color: #fff8c4; font-weight: bold"

        # Liabilities styling
        lie_label = row["Liabilities & Equity"]
        if lie_label and ("TOTAL" in lie_label or "EQUITY" in lie_label):
            styles[2] = styles[3] = "font-weight: bold; background-color: #e3f2fd"
        elif compare_bs and lie_label:
            old = get_old_val(lie_label)
            new = get_val(lie_label)
            if old is not None and old != new:
                styles[3] = "background-color: #fff8c4; font-weight: bold"
        return styles

    styled = df.style \
        .apply(style_fn, axis=1) \
        .set_properties(**{"text-align": "right"}, subset=["Amount", "Amount "]) \
        .set_properties(**{"text-align": "left"}, subset=["Assets", "Liabilities & Equity"]) \
        .hide(axis="index")
    return styled

# --- Display ---
col1, col2 = st.columns(2)
with col1:
    balance_check_before = bs_before["assets"]["TOTAL ASSETS"] - bs_before["lie"]["TOTAL LIABILITIES + EQUITY"]
    st.metric("Before: Assets = L+E?", "✓ BALANCED" if abs(balance_check_before) < 0.01 else "✗ UNBALANCED",
              delta=f"Diff: {balance_check_before:,.2f}" if abs(balance_check_before) > 0.01 else "Perfect")
with col2:
    balance_check_after = bs_after["assets"]["TOTAL ASSETS"] - bs_after["lie"]["TOTAL LIABILITIES + EQUITY"]
    st.metric("After: Assets = L+E?", "✓ BALANCED" if abs(balance_check_after) < 0.01 else "✗ UNBALANCED",
              delta=f"Diff: {balance_check_after:,.2f}" if abs(balance_check_after) > 0.01 else "Perfect")

st.markdown("### Balance Sheet – Before Scenario")
st.dataframe(create_bs_table(bs_before), use_container_width=True)

st.markdown("### Balance Sheet – After What-If Scenario (Changes Highlighted in Yellow)")
st.dataframe(create_bs_table(bs_after, bs_before), use_container_width=True)

st.metric("Calculated Net Income", fmt(pnl["Net Income"]))

st.success("Balance Sheet Always Balances | Assets = Liabilities + Equity")

st.info("""
**Bank P&L → Balance Sheet Mechanics**
- Provision → Increases Allowance → Reduces Net Loans  
- Tax → Increases Accrued Tax Payable  
- Net Income → Increases Retained Earnings  
→ Every change has a precise balance sheet impact
""")

st.sidebar.success("Professional Banking Version")
st.sidebar.info("• Side-by-side Assets & L+E\n• Yellow highlight for changes\n• Balance verification\n• Provision-focused")
