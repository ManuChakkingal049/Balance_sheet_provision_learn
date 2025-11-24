import streamlit as st
import pandas as pd
from copy import deepcopy

st.set_page_config(layout="wide", page_title="Bank P&L → Balance Sheet (Option B2)")

# -----------------------
# Initial constants / defaults
# -----------------------
ORIGINAL_DEFAULTS = {
    # P&L starting assumptions (these will be used to compute the initial closed P&L)
    "revenue": 120_000.0,
    "cogs": 45_000.0,
    "opex": 25_000.0,
    "interest_expense": 3_000.0,
    "tax_rate": 0.25,
    "provision_expense": 0.0,

    # Balance sheet opening numbers (historical)
    "cash": 50_000.0,
    "gross_loans": 400_000.0,
    "allowance": 0.0,
    "ppe": 30_000.0,
    "deposits": 300_000.0,
    "debt": 80_000.0,
    "accrued_tax_payable": 0.0,
    "share_capital": 50_000.0,
    # retained_earnings initially reflect history only; we'll add initial NI to it when we "close"
    "retained_earnings": 0.0,
}

# We'll keep a copy of the original P&L defaults to seed scenario sliders
SCENARIO_SEED = {
    "revenue": ORIGINAL_DEFAULTS["revenue"],
    "cogs": ORIGINAL_DEFAULTS["cogs"],
    "opex": ORIGINAL_DEFAULTS["opex"],
    "interest_expense": ORIGINAL_DEFAULTS["interest_expense"],
    "provision_expense": ORIGINAL_DEFAULTS["provision_expense"],
    "tax_rate": ORIGINAL_DEFAULTS["tax_rate"],
}

# Save initial data in session_state on first load
if "app" not in st.session_state:
    st.session_state.app = {}
    # The "historical" opening balance sheet before we close initial P&L:
    st.session_state.app["historical_state"] = deepcopy(ORIGINAL_DEFAULTS)
    # mark whether we've executed the initial close
    st.session_state.app["initial_closed"] = False

def fmt(x):
    return f"{x:,.0f}" if isinstance(x, (int, float)) else ""

# -----------------------
# P&L computation (correct handling of negative EBT)
# -----------------------
def compute_pnl(s):
    # s expected to contain revenue, cogs, opex, provision_expense, interest_expense, tax_rate
    net_interest_income = s["revenue"] - s["cogs"]
    operating_income = net_interest_income - s["opex"] - s["provision_expense"]
    ebt = operating_income - s["interest_expense"]

    # tax can be negative (tax credit) when ebt < 0
    tax = ebt * s["tax_rate"]

    net_income = ebt - tax

    return {
        "Net Income": net_income,
        "Provision Expense": s["provision_expense"],
        "Tax Expense": tax,
        "EBT": ebt,
    }

# -----------------------
# Balance sheet builder (applies P&L impacts passed in pnl)
# -----------------------
def build_bs(state, pnl):
    """
    state: dict containing balance sheet line items (cash, gross_loans, allowance, ppe, deposits, debt, accrued_tax_payable, share_capital, retained_earnings)
    pnl: dict with 'Provision Expense', 'Tax Expense', 'Net Income' which are the *current period* amounts to apply
    """
    # Apply P&L impacts to balance sheet (note: caller decides whether pnl is zero for Before)
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

# -----------------------
# INITIAL CLOSE (Option B2): compute initial P&L from historical_state and "close" it into balance sheet
# -----------------------
def execute_initial_close():
    """
    Compute initial P&L using the historical_state values and close it:
    - allowance += provision
    - accrued_tax_payable += tax
    - retained_earnings += net_income (after tax)
    Then reset the 'current-year' P&L inputs to zero in the opening_state.
    """
    hist = deepcopy(st.session_state.app["historical_state"])
    initial_pnl = compute_pnl(hist)

    # Build opening state by applying initial P&L impacts to historical numbers
    opening_state = deepcopy(hist)
    opening_state["allowance"] = opening_state.get("allowance", 0.0) + initial_pnl["Provision Expense"]
    opening_state["accrued_tax_payable"] = opening_state.get("accrued_tax_payable", 0.0) + initial_pnl["Tax Expense"]
    opening_state["retained_earnings"] = opening_state.get("retained_earnings", 0.0) + initial_pnl["Net Income"]

    # After closing, we want the BEFORE P&L to be zero (start of new year)
    # But keep tax_rate for later scenarios
    opening_state["revenue"] = 0.0
    opening_state["cogs"] = 0.0
    opening_state["opex"] = 0.0
    opening_state["interest_expense"] = 0.0
    opening_state["provision_expense"] = 0.0
    # keep tax rate for scenarios
    opening_state["tax_rate"] = hist.get("tax_rate", 0.25)

    # Save into session_state
    st.session_state.app["opening_state"] = opening_state
    st.session_state.app["initial_pnl"] = initial_pnl
    st.session_state.app["initial_closed"] = True

# Execute initial close on first run
if not st.session_state.app["initial_closed"]:
    execute_initial_close()

# For convenience
opening_state = deepcopy(st.session_state.app["opening_state"])
initial_pnl = st.session_state.app["initial_pnl"]

# -----------------------
# UI: scenario inputs (these are independent from opening_state P&L which is now zero)
# -----------------------
st.title("Bank P&L → Balance Sheet What-If (Option B2 — initial closed into RE)")

st.markdown(
    "This app uses **Option B2**: initial P&L (from the historical P&L inputs) "
    "was computed and **closed into the opening balance sheet**. The 'Before' sheet "
    "shows the start-of-year balances (no current-year P&L). Use the sliders to run a what-if scenario."
)

# Show the initial closed P&L summary
col_intro = st.columns([1, 2])
with col_intro[0]:
    st.metric("Initial Net Income (closed to RE)", fmt(initial_pnl["Net Income"]))
with col_intro[1]:
    st.caption(
        f"Initial EBT = {fmt(initial_pnl['EBT'])}; "
        f"Initial Tax = {fmt(initial_pnl['Tax Expense'])}; "
        f"Initial Provision = {fmt(initial_pnl['Provision Expense'])}."
    )

with st.form("scenario_form"):
    st.subheader("Scenario P&L Inputs (current year what-if)")
    c1, c2, c3 = st.columns(3)
    # seeds come from SCENARIO_SEED so users have reasonable starting numbers for scenarios
    with c1:
        revenue = st.slider("Interest Income", 0.0, 500_000.0, SCENARIO_SEED["revenue"], 5_000.0)
        cogs = st.number_input("Funding Cost (COGS)", value=SCENARIO_SEED["cogs"], step=1_000.0, format="%f")
    with c2:
        opex = st.number_input("Opex", value=SCENARIO_SEED["opex"], step=1_000.0, format="%f")
        interest_expense = st.number_input("Other Interest Expense", value=SCENARIO_SEED["interest_expense"], step=500.0, format="%f")
    with c3:
        provision = st.slider("Provision for Loan Losses (scenario)", 0.0, 100_000.0, SCENARIO_SEED["provision_expense"], 1_000.0)
        tax_rate = st.slider("Tax Rate", 0.0, 0.5, SCENARIO_SEED["tax_rate"], 0.01)

    apply = st.form_submit_button("Apply Scenario", type="primary")

# -----------------------
# Compute "Before" and "After"
# -----------------------
# Before: opening_state with NO current-year P&L (we closed initial P&L already)
base_pnl = {"Net Income": 0.0, "Provision Expense": 0.0, "Tax Expense": 0.0}
bs_before = build_bs(opening_state, base_pnl)

# After: apply scenario P&L on top of opening_state
temp_state = deepcopy(opening_state)
# put scenario P&L inputs into temp_state for compute_pnl only
temp_state.update({
    "revenue": revenue,
    "cogs": cogs,
    "opex": opex,
    "interest_expense": interest_expense,
    "provision_expense": provision,
    "tax_rate": tax_rate,
})
scenario_pnl = compute_pnl(temp_state)
# scenario_pnl contains EBT, Tax Expense (may be negative), Provision Expense, Net Income

bs_after = build_bs(opening_state, scenario_pnl)  # note: apply scenario pnl to the opening_state

# -----------------------
# Table / display helpers
# -----------------------
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
