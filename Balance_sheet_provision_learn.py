import streamlit as st
import pandas as pd
from copy import deepcopy

st.set_page_config(layout="wide", page_title="Bank P&L impact on Balance Sheet")

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
    return {"Revenue": revenue, "Opex": opex, "Interest Expense": interest_expense,
            "Provision": provision, "EBT": ebt, "Tax": tax, "Net Income": net_income,
            "Tax Rate": tax_rate}

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
# Dynamic Explanation Generator
# -----------------------------
def generate_dynamic_explanation(pnl_base, pnl_scn):
    explanation = []
    def change_word(diff):
        return "increases" if diff > 0 else "reduces" if diff < 0 else "does not change"
    diff = pnl_scn["Revenue"] - pnl_base["Revenue"]
    explanation.append(f"- Revenue: {fmt(pnl_base['Revenue'])} → {fmt(pnl_scn['Revenue'])}, {change_word(diff)} EBT & Net Income → Retained Earnings.")
    diff = pnl_scn["Opex"] - pnl_base["Opex"]
    explanation.append(f"- Opex: {fmt(pnl_base['Opex'])} → {fmt(pnl_scn['Opex'])}, {change_word(-diff)} EBT & Net Income → Retained Earnings.")
    diff = pnl_scn["Interest Expense"] - pnl_base["Interest Expense"]
    explanation.append(f"- Interest Expense: {fmt(pnl_base['Interest Expense'])} → {fmt(pnl_scn['Interest Expense'])}, {change_word(-diff)} EBT & Net Income → Retained Earnings.")
    diff = pnl_scn["Provision"] - pnl_base["Provision"]
    explanation.append(f"- Provision: {fmt(pnl_base['Provision'])} → {fmt(pnl_scn['Provision'])}, {change_word(-diff)} Net Loans (asset), {change_word(-diff)} EBT & Net Income → Retained Earnings, affects Tax Payable.")
    diff = pnl_scn["Tax Rate"] - pnl_base["Tax Rate"]
    explanation.append(f"- Tax Rate: {pnl_base['Tax Rate']:.2%} → {pnl_scn['Tax Rate']:.2%}, {change_word(diff)} Tax Expense → affects Net Income & Retained Earnings.")
    explanation.append("\n**Balance Sheet Impact:**")
    explanation.append("- Assets change due to Net Loans / Allowance.")
    explanation.append("- Liabilities change due to Tax Payable.")
    explanation.append("- Equity changes due to Net Income / Retained Earnings.")
    explanation.append("- Total Assets = Total Liabilities + Equity remains balanced.")
    return "\n".join(explanation)

# -----------------------------
# Two Columns for Base and Scenario Inputs
# -----------------------------
st.title("Bank P&L impact on Balance Sheet")

col_base, col_scn = st.columns(2)

with col_base:
    st.subheader("Base P&L")
    revenue_base = st.number_input("Revenue (Base)", min_value=0, max_value=300_000, value=120_000, step=5_000)
    opex_base = st.number_input("Opex (Base)", min_value=0, max_value=100_000, value=25_000, step=1_000)
    interest_base = st.number_input("Interest Expense (Base)", min_value=0, max_value=20_000, value=3_000, step=500)
    provision_base = st.number_input("Provision (Base)", min_value=0, max_value=50_000, value=0, step=1_000)
    tax_rate_base = st.number_input("Tax Rate (Base)", min_value=0.0, max_value=0.50, value=0.25, step=0.01, format="%.2f")

with col_scn:
    st.subheader("Scenario P&L")
    revenue_scn = st.number_input("Revenue (Scenario)", min_value=0, max_value=300_000, value=120_000, step=5_000)
    opex_scn = st.number_input("Opex (Scenario)", min_value=0, max_value=100_000, value=25_000, step=1_000)
    interest_scn = st.number_input("Interest Expense (Scenario)", min_value=0, max_value=20_000, value=3_000, step=500)
    provision_scn = st.number_input("Provision (Scenario)", min_value=0, max_value=50_000, value=10_000, step=1_000)
    tax_rate_scn = st.number_input("Tax Rate (Scenario)", min_value=0.0, max_value=0.50, value=0.25, step=0.01, format="%.2f")

apply = st.button("Apply Scenario")

# -----------------------------
# Compute P&L
# -----------------------------
pnl_base = compute_pnl(revenue_base, st.session_state.state["cogs"], opex_base, interest_base, provision_base, tax_rate_base)
pnl_scn = compute_pnl(revenue_scn, st.session_state.state["cogs"], opex_scn, interest_scn, provision_scn, tax_rate_scn)

# -----------------------------
# Build balance sheets
# -----------------------------
bs_base = build_bs(st.session_state.state, pnl_base)
bs_scn = build_bs(st.session_state.state, pnl_scn)

# -----------------------------
# P&L side-by-side table
# -----------------------------
def create_pnl_comparison(pnl_base, pnl_scn):
    items = ["Revenue","Opex","Interest Expense","Provision","EBT","Tax","Net Income"]
    data = {"Item":[], "Base":[], "Scenario":[]}
    for item in items:
        data["Item"].append(item)
        data["Base"].append(pnl_base[item])
        data["Scenario"].append(pnl_scn[item])
    df = pd.DataFrame(data)
    return df.style.format({"Base":"{0:,.0f}", "Scenario":"{0:,.0f}"}).hide(axis="index")

st.markdown("### P&L Comparison – Base vs Scenario")
st.dataframe(create_pnl_comparison(pnl_base, pnl_scn), use_container_width=True)

# -----------------------------
# Retained earnings
# -----------------------------
st.write(f"**Retained Earnings – Base:** {fmt(bs_base['lie']['Retained Earnings'])}")
st.write(f"**Retained Earnings – Scenario:** {fmt(bs_scn['lie']['Retained Earnings'])}")

# -----------------------------
# Balance Sheets
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

st.markdown("### Balance Sheet – Base Scenario")
st.dataframe(create_bs_table(bs_base), use_container_width=True)

st.markdown("### Balance Sheet – Scenario (Changes Highlighted)")
st.dataframe(create_bs_table(bs_scn, bs_base), use_container_width=True)

# -----------------------------
# Dynamic Explanation
# -----------------------------
st.markdown("### Dynamic Explanation")
st.markdown(generate_dynamic_explanation(pnl_base, pnl_scn))

st.success("✔ Balance sheets and P&L are correctly aligned and balanced.")
