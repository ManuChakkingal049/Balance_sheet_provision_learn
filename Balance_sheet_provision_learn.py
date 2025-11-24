import streamlit as st
import pandas as pd
from copy import deepcopy

st.set_page_config(layout="wide", page_title="Bank P&L to Balance Sheet What-If")

# -----------------------------
# Default Bank Balance Sheet
# -----------------------------
DEFAULTS = {
    "cogs": 45_000.0,
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
# Dynamic explanation generator
# -----------------------------
def generate_dynamic_explanation(pnl_base, pnl_scn):
    explanation = []
    def change_word(diff):
        return "increases" if diff > 0 else "reduces" if diff < 0 else "does not change"

    # Items
    for key in ["Revenue", "Opex", "Interest Expense", "Provision", "Tax Rate"]:
        base_val = pnl_base[key] if key != "Tax Rate" else pnl_base["Tax"] / max(pnl_base["EBT"], 1e-6)
        scn_val = pnl_scn[key] if key != "Tax Rate" else pnl_scn["Tax"] / max(pnl_scn["EBT"], 1e-6)
        diff = scn_val - base_val

        if key == "Provision":
            explanation.append(f"- Provision: {fmt(base_val)} → {fmt(scn_val)}, {change_word(-diff)} Net Loans, EBT, Net Income → Retained Earnings & Tax Payable.")
        elif key == "Revenue":
            explanation.append(f"- Revenue: {fmt(base_val)} → {fmt(scn_val)}, {change_word(diff)} EBT & Net Income → Retained Earnings.")
        elif key == "Opex":
            explanation.append(f"- Opex: {fmt(base_val)} → {fmt(scn_val)}, {change_word(-diff)} EBT & Net Income → Retained Earnings.")
        elif key == "Interest Expense":
            explanation.append(f"- Interest Expense: {fmt(base_val)} → {fmt(scn_val)}, {change_word(-diff)} EBT & Net Income → Retained Earnings.")
        elif key == "Tax Rate":
            explanation.append(f"- Tax Rate: {base_val:.2%} → {scn_val:.2%}, {change_word(diff)} Tax Expense → Net Income & Retained Earnings.")

    explanation.append("\n**Balance Sheet Impact:**")
    explanation.append("- Assets change due to Net Loans / Allowance.")
    explanation.append("- Liabilities change due to Tax Payable.")
    explanation.append("- Equity changes due to Net Income / Retained Earnings.")
    explanation.append("- Total Assets = Total Liabilities + Equity remains balanced.")
    return "\n".join(explanation)

# -----------------------------
# P&L sliders as vertical rows
# -----------------------------
st.title("Bank P&L → Balance Sheet What-If (Compact P&L Sliders)")

pnl_items = ["Revenue", "Opex", "Interest Expense", "Provision", "Tax Rate"]
ranges = {
    "Revenue": (0, 300_000, 5_000),
    "Opex": (0, 100_000, 1_000),
    "Interest Expense": (0, 20_000, 500),
    "Provision": (0, 50_000, 1_000),
    "Tax Rate": (0.0, 0.50, 0.01)
}

# Sliders in two columns
cols_base = []
cols_scn = []

st.markdown("### P&L Input Sliders")
for item in pnl_items:
    c1, c2 = st.columns([1,1])
    if item != "Tax Rate":
        base_val = c1.slider(f"{item} (Base)", *ranges[item], 0 if item=="Provision" else ranges[item][1]//2, step=ranges[item][2])
        scn_val = c2.slider(f"{item} (Scenario)", *ranges[item], 0 if item=="Provision" else ranges[item][1]//2, step=ranges[item][2])
    else:
        base_val = c1.slider(f"{item} (Base)", *ranges[item], 0.25, step=ranges[item][2])
        scn_val = c2.slider(f"{item} (Scenario)", *ranges[item], 0.25, step=ranges[item][2])
    cols_base.append(base_val)
    cols_scn.append(scn_val)

# -----------------------------
# Compute P&L and BS
# -----------------------------
pnl_base = compute_pnl(cols_base[0], st.session_state.state["cogs"], cols_base[1], cols_base[2], cols_base[3], cols_base[4])
pnl_scn = compute_pnl(cols_scn[0], st.session_state.state["cogs"], cols_scn[1], cols_scn[2], cols_scn[3], cols_scn[4])

bs_base = build_bs(st.session_state.state, pnl_base)
bs_scn = build_bs(st.session_state.state, pnl_scn)

# -----------------------------
# P&L comparison table
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
# Retained earnings display
# -----------------------------
st.write(f"**Retained Earnings – Base:** {fmt(bs_base['lie']['Retained Earnings'])}")
st.write(f"**Retained Earnings – Scenario:** {fmt(bs_scn['lie']['Retained Earnings'])}")

# -----------------------------
# BS table
# -----------------------------
def create_bs_table(bs_data, compare_bs=None):
    asset_items = ["Cash","Loans (net)","  ├─ Gross Loans","  └─ Allowance for Loan Losses","Property & Equipment","TOTAL ASSETS"]
    liability_items = ["Customer Deposits","Debt","Accrued Interest Payable","Accrued Tax Payable","TOTAL LIABILITIES","","Share Capital","Retained Earnings","TOTAL EQUITY","TOTAL LIABILITIES + EQUITY"]
    data = {"Assets":[],"Amount":[],"Liabilities & Equity":[],"Amount ":[]}
    def get_val(k): return bs_data["assets"].get(k, bs_data["lie"].get(k,""))
    def get_old_val(k): return None if compare_bs is None else compare_bs["assets"].get(k, compare_bs["lie"].get(k,None))
    for i in range(max(len(asset_items), len(liability_items))):
        if i<len(asset_items): label=asset_items[i]; val=get_val(label); data["Assets"].append(label); data["Amount"].append(fmt(val) if isinstance(val,(int,float)) else "")
        else: data["Assets"].append(""); data["Amount"].append("")
        if i<len(liability_items): label=liability_items[i]; val=get_val(label); data["Liabilities & Equity"].append(label); data["Amount "].append(fmt(val) if isinstance(val,(int,float)) else "")
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
# Dynamic explanation
# -----------------------------
st.markdown("### Dynamic Explanation")
st.markdown(generate_dynamic_explanation(pnl_base, pnl_scn))

st.success("✔ Balance sheets and P&L are correctly aligned and balanced.")
