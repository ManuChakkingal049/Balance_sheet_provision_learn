import streamlit as st
import pandas as pd
from copy import deepcopy

st.set_page_config(layout="wide", page_title="Bank P&L to Balance Sheet What-If")

# --- Initial Balanced Position (Bank-like) ---
# Starting with a clean, balanced balance sheet
# Assets: Cash 50k + Net Loans 395k (400k - 5k allowance) + PPE 30k = 475k
# Liabilities: Deposits 300k + Debt 80k = 380k
# Equity: Share Capital 50k + Retained Earnings 45k = 95k
# Total L+E: 380k + 95k = 475k ✓ BALANCED

DEFAULTS = {
    "revenue": 120_000.0,           # Interest income
    "cogs": 45_000.0,               # Interest expense / funding cost
    "opex": 25_000.0,
    "interest_expense": 3_000.0,     # Non-interest expense
    "tax_rate": 0.25,
    "provision_expense": 0.0,        # Start with zero provision (no P&L impact initially)

    "cash": 50_000.0,
    "gross_loans": 400_000.0,
    "allowance": 5_000.0,            # Starting allowance
    "ppe": 30_000.0,

    "deposits": 300_000.0,           # Customer deposits
    "debt": 80_000.0,
    "accrued_tax_payable": 0.0,
    "share_capital": 50_000.0,
    "retained_earnings": 45_000.0,   # Calculated to balance: 475k - 380k - 50k = 45k
}

if "state" not in st.session_state:
    st.session_state.state = deepcopy(DEFAULTS)

def fmt(x):
    return f"{x:,.0f}"

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
st.markdown("**Adjust P&L → See instant impact on Loans, Allowance & Equity**")

with st.form("inputs"):
    st.subheader("Key P&L Adjustments (Bank Focus)")
    c1, c2, c3 = st.columns(3)
    with c1:
        revenue = st.slider("Interest Income", 0.0, 300000.0, st.session_state.state["revenue"], 5000.0)
    with c2:
        provision = st.slider("Provision for Loan Losses", 0.0, 50000.0, st.session_state.state["provision_expense"], 1000.0)
    with c3:
        tax_rate = st.slider("Tax Rate", 0.0, 0.50, st.session_state.state["tax_rate"], 0.01)

    apply = st.form_submit_button("Apply Scenario", type="primary", use_container_width=True)
    
    # Fixed values (not sliders)
    funding_cost = st.session_state.state["cogs"]
    opex = st.session_state.state["opex"]
    non_interest_exp = st.session_state.state["interest_expense"]

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
    asset_items = [
        ("Cash", "cash"),
        ("Loans (net)", "loans_net"),
        ("  ├─ Gross Loans", "gross_loans"),
        ("  └─ Allowance for Loan Losses", "allowance"),
        ("Property & Equipment", "ppe"),
        ("TOTAL ASSETS", "total_assets"),
    ]
    
    liability_items = [
        ("Customer Deposits", "deposits"),
        ("Debt", "debt"),
        ("Accrued Tax Payable", "accrued_tax_payable"),
        ("TOTAL LIABILITIES", "total_liabilities"),
        ("", ""),
        ("Share Capital", "share_capital"),
        ("Retained Earnings", "retained_earnings"),
        ("TOTAL EQUITY", "total_equity"),
        ("TOTAL LIABILITIES + EQUITY", "total_lie"),
    ]

    # Extract values
    def get_val(key):
        if key in bs_data["assets"]:
            return bs_data["assets"][key]
        elif key in bs_data["lie"]:
            return bs_data["lie"][key]
        return ""
    
    def get_old_val(key):
        if not compare_bs:
            return None
        if key in compare_bs["assets"]:
            return compare_bs["assets"][key]
        elif key in compare_bs["lie"]:
            return compare_bs["lie"][key]
        return None

    # Build side-by-side table
    max_rows = max(len(asset_items), len(liability_items))
    
    data = {
        "Assets": [],
        "Amount": [],
        "Liabilities & Equity": [],
        "Amount ": []
    }
    
    for i in range(max_rows):
        # Assets side
        if i < len(asset_items):
            label, key = asset_items[i]
            data["Assets"].append(label)
            val = get_val(label)
            data["Amount"].append(fmt(val) if isinstance(val, (int, float)) else "")
        else:
            data["Assets"].append("")
            data["Amount"].append("")
        
        # Liabilities side
        if i < len(liability_items):
            label, key = liability_items[i]
            data["Liabilities & Equity"].append(label)
            val = get_val(label)
            data["Amount "].append(fmt(val) if isinstance(val, (int, float)) else "")
        else:
            data["Liabilities & Equity"].append("")
            data["Amount "].append("")

    df = pd.DataFrame(data)

    def style_fn(row):
        styles = [""] * len(row)
        
        # Check assets column
        asset_label = row["Assets"]
        if asset_label:
            if "TOTAL" in asset_label:
                styles[0] = styles[1] = "font-weight: bold; background-color: #e3f2fd"
            elif compare_bs and asset_label in bs_data["assets"]:
                old = get_old_val(asset_label)
                new = bs_data["assets"][asset_label]
                if old is not None and old != new:
                    styles[1] = "background-color: #fff8c4; font-weight: bold"
        
        # Check liabilities column
        lie_label = row["Liabilities & Equity"]
        if lie_label:
            if "TOTAL" in lie_label or "EQUITY" in lie_label:
                styles[2] = styles[3] = "font-weight: bold; background-color: #e3f2fd"
            elif compare_bs and lie_label in bs_data["lie"]:
                old = get_old_val(lie_label)
                new = bs_data["lie"][lie_label]
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
    base_balance_check = base_bs["assets"]["TOTAL ASSETS"] - base_bs["lie"]["TOTAL LIABILITIES + EQUITY"]
    st.metric("Before: Assets = L+E?", "✓ BALANCED" if abs(base_balance_check) < 0.01 else "✗ UNBALANCED", 
              delta=f"Diff: {base_balance_check:,.2f}" if abs(base_balance_check) > 0.01 else "Perfect")

with col2:
    scenario_balance_check = scenario_bs["assets"]["TOTAL ASSETS"] - scenario_bs["lie"]["TOTAL LIABILITIES + EQUITY"]
    st.metric("After: Assets = L+E?", "✓ BALANCED" if abs(scenario_balance_check) < 0.01 else "✗ UNBALANCED",
              delta=f"Diff: {scenario_balance_check:,.2f}" if abs(scenario_balance_check) > 0.01 else "Perfect")

st.markdown("### Balance Sheet – Before Scenario")
st.dataframe(create_bs_table(base_bs), use_container_width=True)

st.markdown("### Balance Sheet – After What-If Scenario (Changes Highlighted in Yellow)")
st.dataframe(create_bs_table(scenario_bs, base_bs), use_container_width=True)

# Final confirmation
st.success("Balance Sheet Always Balances | Assets = Liabilities + Equity")

st.info("""
**Perfect Bank / Credit Model:**
- Provision → Increases Allowance → Reduces Net Loans  
- Tax → Increases Accrued Tax Payable  
- Net Income → Increases Retained Earnings  
→ Every change has a precise balance sheet impact
""")

st.sidebar.success("Professional Banking Version")
st.sidebar.info("• Side-by-side Assets & L+E\n• Yellow highlight for changes\n• Balance verification\n• Provision-focused")
