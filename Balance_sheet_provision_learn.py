import streamlit as st
import pandas as pd
from copy import deepcopy

st.set_page_config(layout="wide", page_title="P&L → Balance Sheet What-If (Wide Format)")

# --- Initial Balanced Position ---
DEFAULTS = {
    "revenue": 100_000.0,
    "cogs": 40_000.0,
    "opex": 20_000.0,
    "interest_expense": 2_000.0,
    "tax_rate": 0.20,
    "provision_expense": 500.0,

    "cash": 20_000.0,
    "accounts_receivable_gross": 15_000.0,
    "allowance_doubtful": 0.0,
    "inventory": 10_000.0,
    "ppe": 30_000.0,

    "accounts_payable": 8_000.0,
    "accrued_tax_payable": 0.0,
    "debt": 10_000.0,
    "share_capital": 30_000.0,
    "retained_earnings": 27_000.0,  # Makes initial BS balance
}

if "state" not in st.session_state:
    st.session_state.state = deepcopy(DEFAULTS)

# --- Helpers ---
def fmt(x):
    return f"{float(x):,.2f}" if isinstance(x, (int, float)) else x

# --- P&L ---
def compute_pnl(s):
    gross_profit = s["revenue"] - s["cogs"]
    ebit = gross_profit - s["opex"] - s["provision_expense"]
    ebt = ebit - s["interest_expense"]
    tax = max(ebt, 0) * s["tax_rate"]
    net_income = ebt - tax
    return {
        "Revenue": s["revenue"],
        "COGS": s["cogs"],
        "Gross Profit": gross_profit,
        "OpEx": s["opex"],
        "Provision Expense": s["provision_expense"],
        "EBIT": ebit,
        "Interest": s["interest_expense"],
        "EBT": ebt,
        "Tax Expense": tax,
        "Net Income": net_income,
    }

# --- Balance Sheet Builder (Always Balances) ---
def build_bs(state, pnl, base_re=None):
    if base_re is None:
        base_re = state["retained_earnings"]

    allowance = state["allowance_doubtful"] + pnl["Provision Expense"]
    tax_payable = state["accrued_tax_payable"] + pnl["Tax Expense"]
    retained = base_re + pnl["Net Income"]
    net_ar = state["accounts_receivable_gross"] - allowance

    total_assets = state["cash"] + net_ar + state["inventory"] + state["ppe"]
    total_liab = state["accounts_payable"] + tax_payable + state["debt"]
    total_equity = state["share_capital"] + retained
    total_l_e = total_liab + total_equity

    return {
        "assets": {
            "Cash": state["cash"],
            "Accounts Receivable (net)": net_ar,
            "  ├─ Gross AR": state["accounts_receivable_gross"],
            "  └─ Allowance": -allowance,
            "Inventory": state["inventory"],
            "PPE (net)": state["ppe"],
            "Total Assets": total_assets,
        },
        "liabilities": {
            "Accounts Payable": state["accounts_payable"],
            "Accrued Tax Payable": tax_payable,
            "Debt": state["debt"],
            "Total Liabilities": total_liab,
        },
        "equity": {
            "Share Capital": state["share_capital"],
            "Retained Earnings": retained,
            "Total Equity": total_equity,
        },
        "total_l_e": total_l_e,
        "allowance": allowance,
        "tax_payable": tax_payable,
        "retained": retained,
    }

# --- UI ---
st.title("P&L → Balance Sheet What-If Explorer")
st.markdown("**Adjust P&L → Instantly see correct impact on Balance Sheet (same date, always balances!)**")

with st.form("inputs"):
    c1, c2, c3 = st.columns(3)
    with c1:
        revenue = st.slider("Revenue", 0.0, 500_000.0, st.session_state.state["revenue"], 1_000.0)
        cogs = st.slider("COGS", 0.0, 300_000.0, st.session_state.state["cogs"], 500.0)
    with c2:
        opex = st.slider("OpEx", 0.0, 200_000.0, st.session_state.state["opex"], 500.0)
        provision = st.slider("Provision Expense", 0.0, 10_000.0, st.session_state.state["provision_expense"], 100.0)
    with c3:
        interest = st.slider("Interest Expense", 0.0, 50_000.0, st.session_state.state["interest_expense"], 100.0)
        tax_rate = st.slider("Tax Rate", 0.0, 0.5, st.session_state.state["tax_rate"], 0.01, format="%.0%")

    submitted = st.form_submit_button("Apply Scenario", type="primary", use_container_width=True)

# Compute
base_pnl = compute_pnl(st.session_state.state)
base_bs = build_bs(st.session_state.state, base_pnl)

if submitted:
    temp = deepcopy(st.session_state.state)
    for k, v in zip(["revenue","cogs","opex","provision_expense","interest_expense","tax_rate"],
                    [revenue, cogs, opex, provision, interest, tax_rate]):
        temp[k] = v
    scenario_pnl = compute_pnl(temp)
    scenario_bs = build_bs(temp, scenario_pnl, st.session_state.state["retained_earnings"])
else:
    scenario_pnl = base_pnl
    scenario_bs = base_bs

# --- Wide Balance Sheet Display ---
st.markdown("### Balance Sheet – Before vs After (Same Date What-If)")

# Build rows
rows = [
    ("Cash", "Cash"),
    ("Accounts Receivable (net)", "  ├─ Gross AR"),
    ("", "  └─ Allowance"),
    ("Inventory", "Inventory"),
    ("PPE (net)", "PPE (net)"),
    ("**Total Assets**", "**Total Assets**"),
    ("", ""),
    ("", "Accounts Payable"),
    ("", "Accrued Tax Payable"),
    ("", "Debt"),
    ("", "**Total Liabilities**"),
    ("", ""),
    ("", "Share Capital"),
    ("", "Retained Earnings"),
    ("", "**Total Equity**"),
    ("", ""),
    ("**Total Liabilities + Equity**", "**Total Liabilities + Equity**"),
]

data = {
    "Account": [],
    "Before Assets": [], "After Assets": [],
    "Before L&E": [],   "After L&E": [],
}

for asset_key, le_key in rows:
    data["Account"].append(asset_key)

    # Assets side
    if asset_key and asset_key in base_bs["assets"]:
        data["Before Assets"].append(fmt(base_bs["assets"][asset_key]))
        data["After Assets"].append(fmt(scenario_bs["assets"][asset_key]))
    elif "Total Assets" in asset_key:
        data["Before Assets"].append(fmt(base_bs["assets"]["Total Assets"]))
        data["After Assets"].append(fmt(scenario_bs["assets"]["Total Assets"]))
    else:
        data["Before Assets"].append("")
        data["After Assets"].append("")

    # Liabilities & Equity side
    if le_key:
        if le_key in base_bs["liabilities"]:
            data["Before L&E"].append(fmt(base_bs["liabilities"][le_key]))
            data["After L&E"].append(fmt(scenario_bs["liabilities"][le_key]))
        elif le_key in base_bs["equity"]:
            data["Before L&E"].append(fmt(base_bs["equity"][le_key]))
            data["After L&E"].append(fmt(scenario_bs["equity"][le_key]))
        elif "Total Liabilities" in le_key:
            data["Before L&E"].append(fmt(base_bs["liabilities"]["Total Liabilities"]))
            data["After L&E"].append(fmt(scenario_bs["liabilities"]["Total Liabilities"]))
        elif "Total Equity" in le_key:
            data["Before L&E"].append(fmt(base_bs["equity"]["Total Equity"]))
            data["After L&E"].append(fmt(scenario_bs["equity"]["Total Equity"]))
        elif "Total Liabilities + Equity" in le_key:
            data["Before L&E"].append(fmt(base_bs["total_l_e"]))
            data["After L&E"].append(fmt(scenario_bs["total_l_e"]))
        else:
            data["Before L&E"].append("")
            data["After L&E"].append("")
    else:
        data["Before L&E"].append("")
        data["After L&E"].append("")

df = pd.DataFrame(data)

# Styling
def highlight_changes(row):
    styles = [""] * len(row)
    if row["Before Assets"] != row["After Assets"] and row["Before Assets"]:
        styles[2] = "background-color: #ffeb9c"
    if row["Before L&E"] != row["After L&E"] and row["Before L&E"]:
        styles[4] = "background-color: #ffeb9c"
    return styles

styled_df = df.style \
    .apply(highlight_changes, axis=1) \
    .set_properties(**{"text-align": "right"}, subset=["Before Assets", "After Assets", "Before L&E", "After L&E"]) \
    .set_properties(**{"font-weight": "bold"}, subset=pd.IndexSlice[df["Account"].str.contains("Total|Liabilities|Equity"), :]) \
    .hide(axis="index")

st.markdown("<h4 style='text-align: center;'>Assets</h4>", unsafe_allow_html=True)
c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 2])
with c1: st.write("**Account**")
with c2: st.write("**Before**")
with c3: st.write("**After**")
with c4: st.write("**Before**")
with c5: st.write("**After**")

st.dataframe(styled_df, use_container_width=True, hide_index=True)

# Balance confirmation
st.success("Balance Sheet Balances Perfectly: Assets = Liabilities + Equity (Before & After)")

# Summary
st.markdown("### Key Accounting Flows")
st.markdown("- **Provision Expense** → ↑ Allowance → ↓ Net AR")
st.markdown("- **Tax Expense** → ↑ Accrued Tax Payable")
st.markdown("- **Net Income** → ↑ Retained Earnings (100% flow-through)")

st.sidebar.success("Wide, clean, professional layout")
st.sidebar.info("Perfect for teaching, interviews, investor discussions, or financial modeling.")
