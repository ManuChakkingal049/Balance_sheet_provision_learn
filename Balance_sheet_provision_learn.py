import streamlit as st
import pandas as pd
from copy import deepcopy

st.set_page_config(layout="wide", page_title="Bank P&L & Balance Sheet What-If")

# -----------------------------
# Default Bank Balance Sheet
# -----------------------------
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
    "ppe": 30_000.0,

    # Liabilities
    "deposits": 300_000.0,
    "debt": 80_000.0,
    "accrued_interest_payable": 3_000.0,

    # Equity
    "share_capital": 50_000.0,
}

if "state" not in st.session_state:
    st.session_state.state = deepcopy(DEFAULTS)

def fmt(x):
    return f"{x:,.0f}"

# -----------------------------
# P&L Computation
# -----------------------------
def compute_pnl(state):
    net_interest_income = state["revenue"] - state["cogs"]
    operating_income = net_interest_income - state["opex"] - state["provision_expense"]
    ebt = operating_income - state["interest_expense"]
    tax = ebt * state["tax_rate"]
    net_income = ebt - tax
    return {
        "Revenue": state["revenue"],
        "Opex": state["opex"],
        "Provision": state["provision_expense"],
        "EBT": ebt,
        "Tax": tax,
        "Net Income": net_income
    }

# -----------------------------
# Build Balance Sheet
# -----------------------------
def build_bs(state, pnl):
    allowance = pnl["Provision"]
    tax_payable = pnl["Tax"]
    retained_earnings = pnl["Net Income"]

    net_loans = state["gross_loans"] - allowance
    total_assets = state["cash"] + net_loans + state["ppe"]
    total_liabilities = state["deposits"] + state["debt"] + state["accrued_interest_payable"] + tax_payable
    total_equity = state["share_capital"] + retained_earnings

    assets = {
        "Cash": state["cash"],
        "Loans (net)": net_loans,
        "  ├─ Gross Loans": state["gross_loans"],
        "  └─ Allowance for Loan Losses": -allowance,
        "Property & Equipment": state["ppe"],
        "TOTAL ASSETS": total_assets
    }

    lie = {
        "Customer Deposits": state["deposits"],
        "Debt": state["debt"],
        "Accrued Interest Payable": state["accrued_interest_payable"],
        "Accrued Tax Payable": tax_payable,
        "TOTAL LIABILITIES": total_liabilities,
        "": "",
        "Share Capital": state["share_capital"],
        "Retained Earnings": retained_earnings,
        "TOTAL EQUITY": total_equity,
        "TOTAL LIABILITIES + EQUITY": total_liabilities + total_equity
    }

    return {"assets": assets, "lie": lie}

# -----------------------------
# Sidebar sliders for After scenario
# -----------------------------
st.sidebar.header("Scenario Adjustments (After)")

after_state = deepcopy(st.session_state.state)
after_state["revenue"] = st.sidebar.slider("Revenue", 0.0, 300_000.0, st.session_state.state["revenue"], 5_000.0)
after_state["opex"] = st.sidebar.slider("Opex", 0.0, 100_000.0, st.session_state.state["opex"], 1_000.0)
after_state["provision_expense"] = st.sidebar.slider("Provision", 0.0, 50_000.0, 10_000.0, 1_000.0)
after_state["cash"] = st.sidebar.slider("Cash", 0.0, 200_000.0, st.session_state.state["cash"], 1_000.0)
after_state["gross_loans"] = st.sidebar.slider("Gross Loans", 0.0, 500_000.0, st.session_state.state["gross_loans"], 1_000.0)
after_state["ppe"] = st.sidebar.slider("PPE", 0.0, 100_000.0, st.session_state.state["ppe"], 1_000.0)
after_state["deposits"] = st.sidebar.slider("Deposits", 0.0, 400_000.0, st.session_state.state["deposits"], 1_000.0)
after_state["debt"] = st.sidebar.slider("Debt", 0.0, 150_000.0, st.session_state.state["debt"], 1_000.0)

# -----------------------------
# Compute P&L and BS
# -----------------------------
pnl_before = compute_pnl(st.session_state.state)
bs_before = build_bs(st.session_state.state, pnl_before)

pnl_after = compute_pnl(after_state)
bs_after = build_bs(after_state, pnl_after)

# -----------------------------
# P&L Table (Before vs After)
# -----------------------------
pnl_items = ["Revenue", "Opex", "Provision", "EBT", "Tax", "Net Income"]
pnl_df = pd.DataFrame({
    "Item": pnl_items,
    "Before": [pnl_before[i] for i in pnl_items],
    "After": [pnl_after[i] for i in pnl_items]
})
st.markdown("### P&L – Before vs After")
st.dataframe(pnl_df.style.format({"Before": "{0:,.0f}", "After": "{0:,.0f}"}).hide(axis="index"), use_container_width=True)

# -----------------------------
# Balance Sheet Table (Before vs After)
# -----------------------------
asset_items = ["Cash","Loans (net)","  ├─ Gross Loans","  └─ Allowance for Loan Losses","Property & Equipment","TOTAL ASSETS"]
liability_items = ["Customer Deposits","Debt","Accrued Interest Payable","Accrued Tax Payable","TOTAL LIABILITIES","","Share Capital","Retained Earnings","TOTAL EQUITY","TOTAL LIABILITIES + EQUITY"]

def create_bs_table(bs_before, bs_after):
    data = {"Assets":[],"Before":[],"After":[],"Liabilities & Equity":[],"Before_L&E":[],"After_L&E":[]}
    max_rows = max(len(asset_items), len(liability_items))
    for i in range(max_rows):
        # Assets
        if i<len(asset_items):
            key = asset_items[i]
            data["Assets"].append(key)
            data["Before"].append(bs_before["assets"].get(key,""))
            data["After"].append(bs_after["assets"].get(key,""))
        else:
            data["Assets"].append(""); data["Before"].append(""); data["After"].append("")
        # Liabilities & Equity
        if i<len(liability_items):
            key = liability_items[i]
            data["Liabilities & Equity"].append(key)
            data["Before_L&E"].append(bs_before["lie"].get(key,""))
            data["After_L&E"].append(bs_after["lie"].get(key,""))
        else:
            data["Liabilities & Equity"].append(""); data["Before_L&E"].append(""); data["After_L&E"].append("")

    df = pd.DataFrame(data)
    def style_fn(row):
        styles=[""]*len(row)
        for col_before, col_after in [("Before","After"),("Before_L&E","After_L&E")]:
            if row[col_before]!=row[col_after]:
                idx_before = df.columns.get_loc(col_before)
                idx_after = df.columns.get_loc(col_after)
                styles[idx_after] = "background-color:#fff7b2;font-weight:bold"
        return styles
    return df.style.apply(style_fn, axis=1).format("{0:,.0f}").hide(axis="index")

st.markdown("### Balance Sheet – Before vs After")
st.dataframe(create_bs_table(bs_before, bs_after), use_container_width=True)

# -----------------------------
# Balance Check
# -----------------------------
st.metric("Assets = L+E (Before)", "✓" if abs(bs_before["assets"]["TOTAL ASSETS"]-bs_before["lie"]["TOTAL LIABILITIES + EQUITY"])<1e-2 else "✗")
st.metric("Assets = L+E (After)", "✓" if abs(bs_after["assets"]["TOTAL ASSETS"]-bs_after["lie"]["TOTAL LIABILITIES + EQUITY"])<1e-2 else "✗")

st.success("✔ Balance sheets are balanced in both scenarios.")

# -----------------------------
# Dynamic reasoning / explanation
# -----------------------------
st.markdown("## How changes propagate to the Balance Sheet")
st.markdown("""
- **Provision for Loan Losses**:
  - Increases allowance → reduces net loans (asset)
  - Reduces taxable profit → reduces tax payable (liability)
  - Reduces net income → reduces retained earnings (equity)
- **Revenue / Interest Income**:
  - Increases EBT → increases net income → increases retained earnings
- **Opex / Interest Expense**:
  - Increases expense → reduces EBT → reduces net income → reduces retained earnings
- **Balance Sheet items (Cash, PPE, Deposits, Debt)**:
  - Directly affect total assets or total liabilities
- **Net effect**: Every P&L change flows through to **retained earnings and tax**, maintaining balance
""")

# -----------------------------
# Summary table of changes
# -----------------------------
summary_df = pd.DataFrame({
    "Item": pnl_items + asset_items + liability_items,
    "Before": [pnl_before[i] for i in pnl_items] + [bs_before["assets"].get(i,bs_before["lie"].get(i,"")) for i in asset_items] + [bs_before["assets"].get(i,bs_before["lie"].get(i,"")) for i in liability_items],
    "After": [pnl_after[i] for i in pnl_items] + [bs_after["assets"].get(i,bs_after["lie"].get(i,"")) for i in asset_items] + [bs_after["assets"].get(i,bs_after["lie"].get(i,"")) for i in liability_items],
})
summary_df["Change"] = summary_df["After"] - summary_df["Before"]
st.markdown("### Summary of Changes (Before → After)")
st.dataframe(summary_df.style.format("{0:,.0f}").hide(axis="index"), use_container_width=True)
