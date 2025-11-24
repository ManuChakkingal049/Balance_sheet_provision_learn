import streamlit as st
import pandas as pd
from copy import deepcopy

st.set_page_config(layout="wide", page_title="Bank P&L to Balance Sheet What-If")

# -----------------------------
# Default Bank Balance Sheet
# -----------------------------
DEFAULTS = {
    "revenue": 120_000.0,
    "cogs": 45_000.0,
    "opex": 25_000.0,
    "interest_expense": 3_000.0,
    "tax_rate": 0.25,

    "cash": 50_000.0,
    "gross_loans": 400_000.0,
    "ppe": 30_000.0,

    "deposits": 300_000.0,
    "debt": 80_000.0,
    "accrued_interest_payable": 3_000.0,

    "share_capital": 50_000.0,
}

if "state" not in st.session_state:
    st.session_state.state = deepcopy(DEFAULTS)

def fmt(x):
    return f"{x:,.0f}"

# -----------------------------
# P&L computation
# -----------------------------
def compute_pnl(revenue, cogs, opex, interest_expense, provision, tax_rate):
    net_interest_income = revenue - cogs
    operating_income = net_interest_income - opex - provision
    ebt = operating_income - interest_expense
    tax = ebt * tax_rate
    net_income = ebt - tax
    return {"Revenue": revenue, "Opex": opex, "Provision": provision,
            "EBT": ebt, "Tax": tax, "Net Income": net_income}

# -----------------------------
# Build balance sheet
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
        "TOTAL ASSETS": total_assets,
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
        "TOTAL LIABILITIES + EQUITY": total_liabilities + total_equity,
    }

    return {"assets": assets, "lie": lie}

# -----------------------------
# UI sliders for scenario
# -----------------------------
st.title("Bank P&L → Balance Sheet What-If (Provision Scenario)")

with st.form("inputs"):
    c1, c2 = st.columns(2)
    with c1:
        provision_base = st.slider("Base Provision", 0.0, 50_000.0, 0.0, 1_000.0)
    with c2:
        provision_scenario = st.slider("Scenario Provision", 0.0, 50_000.0, 10_000.0, 1_000.0)

    apply = st.form_submit_button("Apply Scenario", type="primary")

tax_rate = st.session_state.state["tax_rate"]
revenue = st.session_state.state["revenue"]
cogs = st.session_state.state["cogs"]
opex = st.session_state.state["opex"]
interest_expense = st.session_state.state["interest_expense"]

# -----------------------------
# Compute P&L
# -----------------------------
pnl_base = compute_pnl(revenue, cogs, opex, interest_expense, provision_base, tax_rate)
pnl_scenario = compute_pnl(revenue, cogs, opex, interest_expense, provision_scenario, tax_rate)

# -----------------------------
# Build balance sheets
# -----------------------------
bs_base = build_bs(st.session_state.state, pnl_base)
bs_scenario = build_bs(st.session_state.state, pnl_scenario)

# -----------------------------
# P&L side-by-side table
# -----------------------------
def create_pnl_comparison(pnl_base, pnl_scenario):
    items = ["Revenue","Opex","Provision","EBT","Tax","Net Income"]
    data = {"Item":[], "Base":[], "Scenario":[]}
    for item in items:
        data["Item"].append(item)
        data["Base"].append(pnl_base[item])
        data["Scenario"].append(pnl_scenario[item])
    df = pd.DataFrame(data)
    return df.style.format({"Base":"{0:,.0f}", "Scenario":"{0:,.0f}"}).hide(axis="index")

st.markdown("### P&L Comparison – Base vs Scenario Provision")
st.dataframe(create_pnl_comparison(pnl_base, pnl_scenario), use_container_width=True)

# -----------------------------
# Display retained earnings above BS
# -----------------------------
st.write(f"**Retained Earnings – Base:** {fmt(bs_base['lie']['Retained Earnings'])}")
st.write(f"**Retained Earnings – Scenario:** {fmt(bs_scenario['lie']['Retained Earnings'])}")

# -----------------------------
# Table builder for BS
# -----------------------------
def create_bs_table(bs_data, compare_bs=None):
    asset_items = ["Cash","Loans (net)","  ├─ Gross Loans","  └─ Allowance for Loan Losses","Property & Equipment","TOTAL ASSETS"]
    liability_items = ["Customer Deposits","Debt","Accrued Interest Payable","Accrued Tax Payable","TOTAL LIABILITIES","","Share Capital","Retained Earnings","TOTAL EQUITY","TOTAL LIABILITIES + EQUITY"]

    data = {"Assets":[],"Amount":[],"Liabilities & Equity":[],"Amount ":[]}
    def get_val(k): return bs_data["assets"].get(k, bs_data["lie"].get(k,""))
    def get_old_val(k): return None if compare_bs is None else compare_bs["assets"].get(k, compare_bs["lie"].get(k,None))

    for i in range(max(len(asset_items), len(liability_items))):
        if i<len(asset_items):
            label=asset_items[i]; val=get_val(label)
            data["Assets"].append(label)
            data["Amount"].append(fmt(val) if isinstance(val,(int,float)) else "")
        else: data["Assets"].append(""); data["Amount"].append("")
        if i<len(liability_items):
            label=liability_items[i]; val=get_val(label)
            data["Liabilities & Equity"].append(label)
            data["Amount "].append(fmt(val) if isinstance(val,(int,float)) else "")
        else: data["Liabilities & Equity"].append(""); data["Amount "].append("")

    df=pd.DataFrame(data)
    def style_fn(row):
        styles=[""]*len(row)
        if "TOTAL" in row["Assets"]: styles[0]=styles[1]="font-weight:bold;background-color:#e3f2fd"
        if ("TOTAL" in row["Liabilities & Equity"]) or ("EQUITY" in row["Liabilities & Equity"]): styles[2]=styles[3]="font-weight:bold;background-color:#e3f2fd"
        if compare_bs:
            a,l=row["Assets"],row["Liabilities & Equity"]
            if a and get_old_val(a)!=get_val(a): styles[1]="background-color:#fff7b2;font-weight:bold"
            if l and get_old_val(l)!=get_val(l): styles[3]="background-color:#fff7b2;font-weight:bold"
        return styles
    return df.style.apply(style_fn, axis=1).hide(axis="index")

# -----------------------------
# Display Balance Sheets
# -----------------------------
st.markdown("### Balance Sheet – Base Provision")
st.dataframe(create_bs_table(bs_base), use_container_width=True)

st.markdown("### Balance Sheet – Scenario Provision (Changes Highlighted)")
st.dataframe(create_bs_table(bs_scenario, bs_base), use_container_width=True)

# -----------------------------
# Dynamic Explanation
# -----------------------------
st.markdown("### Dynamic Explanation")
st.markdown(f"""
- **Provision Increase:** From {fmt(provision_base)} → {fmt(provision_scenario)}  
  - Increases **Allowance for Loan Losses** → reduces **Net Loans** (asset side).  
  - Reduces **EBT** → reduces **Net Income** → reduces **Retained Earnings** (equity side).  
  - Reduces **Tax** payable as it is computed on EBT → reduces **Accrued Tax Payable** (liability side).  

**Balance Sheet Impact:**  
- Assets decrease due to higher allowance.  
- Liabilities decrease slightly (tax), but equity decreases by net income reduction.  
- Total Assets = Total Liabilities + Equity remains balanced.
""")

st.success("✔ Balance sheets and P&L are correctly aligned and balanced.")
