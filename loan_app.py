import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Pro Loan Architect", layout="wide", initial_sidebar_state="expanded")

# --- UTILITY: NUMBER FORMATTING ---
def format_num(num, system="Western"):
    # QA Check: Handle NaNs or Infinity just in case
    if pd.isna(num) or num == float('inf'):
        return "N/A"
        
    if system == "Indian (Lakhs/Crores)":
        is_negative = num < 0
        num_str = f"{abs(num):.2f}"
        int_part, dec_part = num_str.split('.')
        if len(int_part) > 3:
            last_3 = int_part[-3:]
            rem = int_part[:-3]
            parts =[rem[max(0, i-2):i] for i in range(len(rem), 0, -2)]
            parts.reverse()
            int_part = ",".join(parts) + "," + last_3
        res = f"{int_part}.{dec_part}"
        return f"-{res}" if is_negative else res
    return f"{num:,.2f}"

# --- URL PARAMETER MANAGEMENT ---
def get_param(key, default, cast_type):
    if key in st.query_params:
        try:
            return cast_type(st.query_params[key])
        except ValueError:
            return default
    return default

# --- SIDEBAR: INPUTS & SETTINGS ---
st.sidebar.title("⚙️ Loan Parameters")

fmt_system = st.sidebar.radio("Number Format", ["Western", "Indian (Lakhs/Crores)"], horizontal=True)

st.sidebar.header("📝 Basic Details")
principal = st.sidebar.number_input("Loan Amount", min_value=1000.0, value=float(get_param("p", 500000)), step=10000.0)
annual_rate = st.sidebar.slider("Annual Interest Rate (%)", 0.1, 25.0, get_param("r", 8.5, float), 0.1)
years = st.sidebar.slider("Loan Term (Years)", 1, 50, get_param("y", 20, int))
start_date = st.sidebar.date_input("Loan Start Date", value=date.today())

st.query_params.update({"p": principal, "r": annual_rate, "y": years})

with st.sidebar.expander("🏦 PITI (Taxes & Insurance)", expanded=False):
    annual_tax = st.number_input("Annual Property Tax", min_value=0.0, value=0.0, step=500.0)
    annual_ins = st.number_input("Annual Home Insurance", min_value=0.0, value=0.0, step=100.0)

with st.sidebar.expander("⏱️ Compounding & Frequencies", expanded=False):
    payment_freq = st.selectbox("Payment Frequency", ["Monthly", "Accelerated Bi-Weekly"])
    compounding = st.selectbox("Interest Compounding", ["Monthly", "Daily", "Semi-Annual (Canadian)"])

with st.sidebar.expander("🚀 Prepayment Strategies", expanded=False):
    extra_payment = st.number_input("Extra per Payment", min_value=0.0, value=0.0, step=100.0)
    st.markdown("---")
    recurring_lump = st.number_input("Annual Bonus Lump Sum", min_value=0.0, value=0.0, step=1000.0)
    recurring_month = st.selectbox("Month for Annual Bonus", range(1, 13), index=11, format_func=lambda x: datetime(2000, x, 1).strftime('%B'))
    st.markdown("---")
    one_time_lump = st.number_input("One-Time Lump Sum", min_value=0.0, value=0.0, step=5000.0)
    one_time_date = st.date_input("Date of One-Time Lump Sum", value=date.today())

with st.sidebar.expander("📈 Floating Rate / Trends", expanded=False):
    rate_trend_active = st.checkbox("Enable Floating Rate Trend")
    trend_amount = st.number_input("Increase rate by (%)", value=0.25, step=0.05)
    trend_months = st.number_input("Every X months", min_value=1, value=12)

# --- CORE MATH ENGINE (QA VERIFIED) ---
@st.cache_data
def run_amortization(p, r_annual, yrs, start_dt, freq, comp, ext_pay, rec_lump, rec_mo, one_lump, one_dt, trnd_act, trnd_amt, trnd_mo):
    data =[]
    balance = float(p)
    current_date = pd.to_datetime(start_dt)
    
    periods_per_year = 26 if freq == "Accelerated Bi-Weekly" else 12
    total_periods = yrs * periods_per_year
    
    def get_period_rate(annual_pct):
        r = annual_pct / 100
        if comp == "Monthly":
            return r / 12 if periods_per_year == 12 else ((1 + r/12)**(12/26) - 1)
        elif comp == "Daily":
            return (1 + r / 365) ** (365 / periods_per_year) - 1
        elif comp == "Semi-Annual (Canadian)":
            return (1 + r / 2) ** (2 / periods_per_year) - 1

    def get_emi(princ, rate_per_period, periods_left):
        if rate_per_period <= 0: return princ / periods_left if periods_left > 0 else 0
        return princ * (rate_per_period * (1 + rate_per_period)**periods_left) / ((1 + rate_per_period)**periods_left - 1)

    base_monthly_emi = get_emi(p, get_period_rate(r_annual) if comp != "Monthly" else (r_annual/100/12), yrs * 12)
    base_payment = base_monthly_emi if periods_per_year == 12 else base_monthly_emi / 2

    current_rate = r_annual
    last_rec_year = current_date.year - 1
    applied_one_time = False
    neg_amortization_flag = False

    period_tax = annual_tax / periods_per_year
    period_ins = annual_ins / periods_per_year

    # QA FIX: Strict Integer Conversion for Modulo Logic
    trend_period_interval = int(round(trnd_mo * (26/12))) if periods_per_year == 26 else int(trnd_mo)

    for period in range(1, total_periods * 3): # Failsafe cap
        if freq == "Monthly":
            current_date += pd.DateOffset(months=1)
        else:
            current_date += pd.Timedelta(days=14)
            
        if trnd_act and period > 1 and (period - 1) % trend_period_interval == 0:
            current_rate += trnd_amt
            rem_periods = total_periods - period + 1
            if rem_periods > 0:
                base_payment = get_emi(balance, get_period_rate(current_rate), rem_periods)

        period_r = get_period_rate(current_rate)
        interest = balance * period_r
        
        principal_pay = base_payment - interest
        actual_principal = principal_pay + ext_pay
        
        if rec_lump > 0 and current_date.month == rec_mo and current_date.year > last_rec_year:
            actual_principal += rec_lump
            last_rec_year = current_date.year
            
        if one_lump > 0 and not applied_one_time and current_date >= pd.to_datetime(one_dt):
            actual_principal += one_lump
            applied_one_time = True

        # QA FIX: Detect Negative Amortization
        if actual_principal < 0:
            neg_amortization_flag = True

        # Safety Check to prevent overpayment math errors
        if actual_principal >= balance:
            actual_principal = balance
            balance = 0
        else:
            balance -= actual_principal

        data.append({
            "Period": period,
            "Date": current_date.date(),
            "Rate (%)": round(current_rate, 2),
            "Payment Outflow": interest + actual_principal + period_tax + period_ins,
            "Interest": interest,
            "Principal": actual_principal,
            "Taxes & Ins": period_tax + period_ins,
            "Remaining Balance": balance
        })

        if balance <= 0:
            break

    return pd.DataFrame(data), neg_amortization_flag

# --- EXECUTE ENGINE ---
df_base, _ = run_amortization(principal, annual_rate, years, start_date, "Monthly", "Monthly", 0, 0, 1, 0, start_date, False, 0, 1)
df_actual, has_neg_amortization = run_amortization(principal, annual_rate, years, start_date, payment_freq, compounding, extra_payment, recurring_lump, recurring_month, one_time_lump, one_time_date, rate_trend_active, trend_amount, trend_months)

# --- METRICS & ALERTS ---
st.title("🏦 Pro Loan Architect")

# QA UX FIX: Display Warning if Loan is growing
if has_neg_amortization:
    st.error("⚠️ **CRITICAL WARNING: Negative Amortization Detected!** Your interest rate has climbed so high that your payments no longer cover the monthly interest. Your loan balance is actually *growing*.")

base_interest = df_base["Interest"].sum()
actual_interest = df_actual["Interest"].sum()
interest_saved = base_interest - actual_interest

payoff_date_base = df_base.iloc[-1]["Date"]
payoff_date_actual = df_actual.iloc[-1]["Date"]
month_diff = (payoff_date_base.year - payoff_date_actual.year) * 12 + (payoff_date_base.month - payoff_date_actual.month)

cross_over_df = df_actual[df_actual["Principal"] > df_actual["Interest"]]
cross_over_date = cross_over_df.iloc[0]["Date"].strftime('%B %Y') if not cross_over_df.empty else None

st.markdown("### 🎯 Scenario Summary")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Original Total Interest", format_num(base_interest, fmt_system))
c2.metric("Actual Total Interest", format_num(actual_interest, fmt_system))

if interest_saved >= 0:
    c3.metric("Interest Saved 🎉", format_num(interest_saved, fmt_system), f"+{format_num(interest_saved, fmt_system)}")
    c4.metric("Actual Payoff Date", payoff_date_actual.strftime('%b %Y'), f"Saved {month_diff} mos")
else:
    c3.metric("Extra Interest Paid 📉", format_num(abs(interest_saved), fmt_system), f"-{format_num(abs(interest_saved), fmt_system)}")
    # QA FIX: Dynamic metric phrasing for extended loans
    c4.metric("Actual Payoff Date", payoff_date_actual.strftime('%b %Y'), f"Extended by {abs(month_diff)} mos")

if cross_over_date and not has_neg_amortization:
    st.success(f"🔥 **Cross-Over Milestone:** In **{cross_over_date}**, you will officially start paying more toward your Home's Principal than to the Bank's Interest!")

st.markdown("---")

# --- UI CHARTS ---
tab1, tab2 = st.tabs(["📊 Visual Analytics", "📑 Detailed Schedule"])

with tab1:
    fig_bal = go.Figure()
    fig_bal.add_trace(go.Scatter(x=df_base["Date"], y=df_base["Remaining Balance"], name="Standard Balance", line=dict(color='gray', dash='dash')))
    fig_bal.add_trace(go.Scatter(x=df_actual["Date"], y=df_actual["Remaining Balance"], fill='tozeroy', name="Optimized Balance", line=dict(color='royalblue' if not has_neg_amortization else 'crimson')))
    fig_bal.update_layout(title="Loan Paydown Trajectory", xaxis_title="Timeline", yaxis_title="Balance", hovermode="x unified", height=450)
    st.plotly_chart(fig_bal, use_container_width=True)

    col_l, col_r = st.columns(2)
    with col_l:
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Scatter(x=df_actual["Date"], y=df_actual["Interest"], name="Interest Paid", line=dict(color='tomato')))
        fig_comp.add_trace(go.Scatter(x=df_actual["Date"], y=df_actual["Principal"], name="Principal Paid", line=dict(color='mediumseagreen')))
        fig_comp.update_layout(title="Principal vs Interest Intersection", xaxis_title="Timeline", yaxis_title="Amount per Period", hovermode="x unified", height=400)
        st.plotly_chart(fig_comp, use_container_width=True)

    with col_r:
        df_actual["Cum_Outflow"] = df_actual["Payment Outflow"].cumsum()
        fig_cash = go.Figure()
        fig_cash.add_trace(go.Scatter(x=df_actual["Date"], y=df_actual["Cum_Outflow"], fill='tozeroy', name="Total Cash Outflow", line=dict(color='orange')))
        fig_cash.update_layout(title="Total Cash Outflow (PITI)", xaxis_title="Timeline", yaxis_title="Cumulative Outflow", hovermode="x unified", height=400)
        st.plotly_chart(fig_cash, use_container_width=True)

with tab2:
    st.subheader("Amortization Ledger")
    display_df = df_actual.copy()
    display_cols =["Payment Outflow", "Interest", "Principal", "Taxes & Ins", "Remaining Balance"]
    for col in display_cols:
        display_df[col] = display_df[col].apply(lambda x: format_num(x, fmt_system))
    
    st.dataframe(display_df, use_container_width=True, height=500)
    st.download_button("📥 Download Ledger (CSV)", data=df_actual.to_csv(index=False).encode('utf-8'), file_name="pro_amortization.csv", mime="text/csv")