import streamlit as st
import pandas as pd
from copy import deepcopy

st.set_page_config(layout="wide", page_title="P&L & Balance Sheet Interactive Explorer")

# --- Helpers and defaults -------------------------------------------------
DEFAULTS = {
    # P&L
    "revenue": 100000.0,
    "cogs": 40000.0,
    "opex": 20000.0,
    "interest_expense": 2000.0,
    "tax_rate": 0.20,
    # Balance sheet
    "cash": 20000.0,
    "accounts_receivable": 15000.0,
    "inventory": 10000.0,
    "ppe": 30000.0,
    "allowance_for_doubtful_accounts": 500.0,  # contra-asset (provision)
    "accounts_payable": 8000.0,
    "debt": 10000.0,
    "share_capital": 30000.0,
    # retained earnings will be calculated from historical net income
    "retained_earnings": 12000.0,
}

if "state" not in st.session_state:
    st.session_state.state = deepcopy(DEFAULTS)
    st.session_state.prev = deepcopy(DEFAULTS)
    st.session_state.messages = []

# Utility for formatting
def fmt(x):
    return f"{x:,.2f}"

# --- Accounting logic -----------------------------------------------------

def compute_pnl(s):
    revenue = s["revenue"]
    cogs = s["cogs"]
    gross_profit = revenue - cogs
    opex = s["opex"]
    provision_expense = s["allowance_for_doubtful_accounts"]  # automatically included
    ebit = gross_profit - opex - provision_expense
    interest = s["interest_expense"]
    ebt = ebit - interest
    tax = max(0.0, ebt) * s["tax_rate"]
    net_income = ebt - tax
    return {
        "Revenue": revenue,
        "COGS": cogs,
        "Gross Profit": gross_profit,
        "Operating Expenses": opex,
        "Provision Expense": provision_expense,
        "EBIT": ebit,
        "Interest Expense": interest,
        "EBT": ebt,
        "Tax": tax,
        "Net Income": net_income,
    }


def compute_balance_sheet(s, include_retained=True):
    # Assets
    assets = {
        "Cash": s["cash"],
        "Accounts Receivable (gross)": s["accounts_receivable"],
        "Less: Allowance for Doubtful Accounts": -s["allowance_for_doubtful_accounts"],
        "Inventory": s["inventory"],
        "PPE (net)": s["ppe"],
    }
    total_assets = sum(assets.values())

    # Liabilities
    liabilities = {
        "Accounts Payable": s["accounts_payable"],
        "Debt": s["debt"],
    }
    total_liabilities = sum(liabilities.values())

    # Equity
    retained = s["retained_earnings"] if include_retained else 0.0
    equity = {
        "Share Capital": s["share_capital"],
        "Retained Earnings": retained,
    }
    total_equity = sum(equity.values())

    return assets, liabilities, equity, total_assets, total_liabilities, total_equity


def balance_sheet_gap(s):
    _, _, _, total_assets, total_liabilities, total_equity = compute_balance_sheet(s)
    return total_assets - (total_liabilities + total_equity)

# --- Interaction: when user updates values --------------------------------

def push_message(msg):
    st.session_state.messages.insert(0, msg)
    if len(st.session_state.messages) > 12:
        st.session_state.messages = st.session_state.messages[:12]


def apply_changes(new_vals, auto_balance_cash=True):
    prev = st.session_state.prev
    s = st.session_state.state

    # Update provision first (Allowance affects P&L and Assets automatically)
    delta_allowance = new_vals["allowance_for_doubtful_accounts"] - prev["allowance_for_doubtful_accounts"]
    if abs(delta_allowance) > 0.005:
        s["allowance_for_doubtful_accounts"] = new_vals["allowance_for_doubtful_accounts"]
        push_message(f"Provision (Allowance for Doubtful Accounts) changed by {fmt(delta_allowance)}. Automatically affects P&L (Provision Expense) and reduces Net Income and Equity.")

    # Update other P&L items
    s["revenue"] = new_vals["revenue"]
    s["cogs"] = new_vals["cogs"]
    s["opex"] = new_vals["opex"]
    s["interest_expense"] = new_vals["interest_expense"]
    s["tax_rate"] = new_vals["tax_rate"]

    # Compute new Net Income automatically
    pnl_before = compute_pnl(prev)["Net Income"]
    pnl_after = compute_pnl(s)["Net Income"]
    delta_net_income = pnl_after - pnl_before
    if abs(delta_net_income) > 0.005:
        s["retained_earnings"] += delta_net_income
        push_message(f"Net Income changed by {fmt(delta_net_income)}. Retained Earnings (Equity) updated automatically.")

    # Update Balance Sheet items
    s["accounts_receivable"] = new_vals["accounts_receivable"]
    s["inventory"] = new_vals["inventory"]
    s["ppe"] = new_vals["ppe"]
    s["accounts_payable"] = new_vals["accounts_payable"]
    s["debt"] = new_vals["debt"]
    s["share_capital"] = new_vals["share_capital"]
    s["cash"] = new_vals["cash"]

    # Auto-balance by adjusting Cash if needed
    gap = balance_sheet_gap(s)
    if auto_balance_cash and abs(gap) > 0.005:
        s["cash"] -= gap
        push_message(f"Auto-balancing: Cash adjusted by {-gap:,.2f} to maintain Assets = Liabilities + Equity.")

    st.session_state.prev = deepcopy(s)
