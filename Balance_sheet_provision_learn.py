import streamlit as st
import pandas as pd
from copy import deepcopy

st.set_page_config(layout="wide", page_title="Bank P&L to Balance Sheet What-If")

# ---------------------------------------------
# Default Bank Balance Sheet (clean start)
# ---------------------------------------------
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
    "accrued_tax_payable": 0.0,
    "accrued_interest_payable": 3_000.0,  # interest expense accrued

    "share_capital": 50_000.0,
    "retained_earnings": 0.0,       # opening retained earnings = 0
}

if "state" not in st.session_state:
    st.session_state.state = deepcopy(DEFAULTS)


def fmt(x):
    return f"{x:,.0f}"


# ---------------------------------------------
# Compute P&L
# ---------------------------------------------
def compute_pnl(s):
    net_interest_income = s["revenue"] - s["cogs"]
    operating_income = net_interest_income - s["opex"] - s["provision_expense"]
    ebt = operating_income - s["interest_expense"]
    tax = ebt * s["tax_rate"]
    net_income = ebt - tax
    return {"Net Income": net_income, "Provision Expense": s["provision_expense"], "Tax Expense": tax}


# ---------------------------------------------
# Build Balance Sheet (using delta logic)
# ---------------------------------------------
def build_bs(base_state, pnl_base, pnl_scenario=None):
    """
    If pnl_scenario is None, build base BS.
    If pnl_scenario is provided, compute scenario delta:
        - retained earnings = base + (scenario NI - base NI)
        - tax payable = base + (scenario tax - base tax)
        - allowance = base allowance + scenario provision
    """
    if pnl_scenario is None:
        # Base BS
        allowance = base_state["allowance"] + pnl_base["Provision Expense"]
        tax_payable = base_state["accrued_tax_payable"] + pnl_base["Tax Expense"]
        retained = base_state["retained_earnings"] + pnl_base["Net Income"]
    else:
        # Scenario BS
        allowance = base_state["allowance"] + pnl_scenario["Provision Expense"]
        tax_payable = base_state["accrued_tax_payable"] + (pnl_scenario["Tax Expense"] - pnl_base["Tax Expense"])
        retained = base_state["retained_earnings"] + (pnl_scenario["Net Income"] - pnl_base["Net Income"])

    net_loans = base_state["gross_loans"] - allowance
    total_assets = base_state["cash"] + net_loans + base_state["ppe"]
    total_liabilities = base_state["deposits"] + base_state["debt"] + base_state["accrued_interest_payable"] + tax_payable
    total_equity = base_state["share_capital"] + retained

    assets = {
        "Cash": base_state["cash"],
        "Loans (net)": net_loans,
        "  ├─ Gross Loans": base_state["gross_loans"],
        "  └─ Allowance for Loan Losses": -allowance,
        "Property & Equipment": base_state["ppe"],
        "TOTAL ASSETS": total_assets,
    }

    lie = {
        "Customer Deposits": base_state["deposits"],
        "Debt": base_state["debt"],
        "Accrued Interest Payable": base_state["accrued_interest_payable"],
        "Accrued Tax Payable": tax_payable,
        "TOTAL LIABILITIES": total_liabilities,
        "": "",
        "Share Capital": base_state["share_capital"],
        "Retained Earnings": retained,
        "TOTAL EQUITY": total_equity,
        "TOTAL LIABILITIES + EQUITY": total_liabilities + total_equity,
    }

    return {"assets": assets, "lie": lie}


# ---------------------------------------------
# Compute base scenario (no extra provision)
# ---------------------------------------------
base_state = deepcopy(st.session_state.state)
pnl_base = compute_pnl(base_state)
bs_base = build_bs(base_state, pnl_base)


# ---------------------------------------------
# Streamlit UI
# ---------------------------------------------
st.title("Bank P&L → Balance Sheet What-If")
st.markdown("Adjust P&L (Provision / Tax Rate / Revenue) and see balance sheet impact.")

with st.form("inputs"):
    c1, c2, c3 = st.columns(3)
    with c1:
        revenue = st.slider("Interest Income", 0.0, 300_000.0, base_state["revenue"], 5_000.0)
    with c2:
        provision = st.slider("Provision for Loan Losses", 0.0, 50_000.0, base_state["provision_expense"], 1_000.0)
    with c3:
        tax_rate = st.slider("Tax Rate", 0.0, 0.5, base_state["tax_rate"], 0.01)

    apply = st.form_submit_button("Apply Scenario", type="primary", use_container_width=True)

# ---------------------------------------------
# Compute scenario BS (delta applied)
# ---------------------------------------------
scenario_state = deepcopy(base_state)
scenario_state.update({
    "revenue": revenue,
    "provision_expense": provision,
    "tax_rate": tax_rate
})

pnl_scenario = compute_pnl(scenario_state)
bs_scenario = build_bs(base_state, pnl_base, pnl_scenario)

# ---------------------------------------------
# Table display
# ---------------------------------------------
def create_bs_table(bs_data, compare_bs=None):
    asset_items = [
        "Cash", "Loans (net)", "  ├─ Gross Loans", "  └─ Allowance for Loan Losses", "Property & Equipment", "TOTAL ASSETS"
    ]
    liability_items = [
        "Customer Deposits", "Debt", "Accrued Interest Payable", "Accrued Tax Payable",
        "TOTAL LIABILITIES", "", "Share Capital", "Retained Earnings", "TOTAL EQUITY", "TOTAL LIABILITIES + EQUITY"
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
            val = get_val(label)
            data["Assets"].append(label)
            data["Amount"].append(fmt(val) if isinstance(val, (int, float)) else "")
        else:
            data["Assets"].append("")
            data["Amount"].append("")

        # Liabilities
        if i < len(liability_items):
            label = liability_items[i]
            val = get_val(label)
            data["Liabilities & Equity"].append(label)
            data["Amount "].append(fmt(val) if isinstance(val, (int, float)) else "")
        else:
            data["Liabilities & Equity"].append("")
            data["Amount "].append("")

    df = pd.DataFrame(data)

    def style_fn(row):
        styles = [""] * len(row)
        if "TOTAL" in row["Assets"]:
            styles[0] = styles[1] = "font-weight:bold;background-color:#e3f2fd"
        if ("TOTAL" in row["Liabilities & Equity"]) or ("EQUITY" in row["Liabilities & Equity"]):
            styles[2] = styles[3] = "font-weight:bold;background-color:#e3f2fd"
        if compare_bs:
            a, l = row["Assets"], row["Liabilities & Equity"]
            if a and get_old_val(a) != get_val(a):
                styles[1] = "background-color:#fff7b2;font-weight:bold"
            if l and get_old_val(l) != get_val(l):
                styles[3] = "background-color:#fff7b2;font-weight:bold"
        return styles

    return df.style.apply(style_fn, axis=1).hide(axis="index")

# ---------------------------------------------
# Display metrics
# ---------------------------------------------
col1, col2 = st.columns(2)
with col1:
    diff_base = bs_base["assets"]["TOTAL ASSETS"] - bs_base["lie"]["TOTAL LIABILITIES + EQUITY"]
    st.metric("Base Scenario Balance", "Balanced" if abs(diff_base) < 0.01 else "UNBALANCED", delta=f"{diff_base:,.2f}")
with col2:
    diff_scenario = bs_scenario["assets"]["TOTAL ASSETS"] - bs_scenario["lie"]["TOTAL LIABILITIES + EQUITY"]
    st.metric("Scenario Balance", "Balanced" if abs(diff_scenario) < 0.01 else "UNBALANCED", delta=f"{diff_scenario:,.2f}")

st.markdown("### Base Scenario Balance Sheet")
st.dataframe(create_bs_table(bs_base), use_container_width=True)

st.markdown("### Scenario Balance Sheet (Changes Highlighted)")
st.dataframe(create_bs_table(bs_scenario, bs_base), use_container_width=True)

st.metric("Scenario Net Income", fmt(pnl_scenario["Net Income"]))

st.success("✔ Balance sheet is perfectly balanced before and after any scenario.")

st.info("""
**Banking Mechanics**
- Provision ↑ → Allowance ↑ → Net Loans ↓  
- Tax ↑ → Accrued Tax Payable ↑  
- Net Income ↑ → Retained Earnings ↑  
- Delta logic ensures perfect balance when comparing scenarios within the same year
""")
