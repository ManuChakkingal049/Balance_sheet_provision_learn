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
# ----------
