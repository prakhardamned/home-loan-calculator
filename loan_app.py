import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Pro Loan Architect", layout="wide", initial_sidebar_state="expanded")

# --- UTILITY: NUMBER FORMATTING ---
def format_num(num, system="Western"):
    if system == "Indian (Lakhs/Crores)":
        is_negative = num < 0
        num_str = f"{abs(num):.2f}"
        int_part, dec_part = num_str.split('.')
        if len(int_part) > 3:
            last_3 = int_part[-3:]
            rem = int_part[:-3]
            parts = [rem[max(0, i-2):i] for i in range(len(rem), 0, -2)]
            parts.reverse()
            int_part = ",".join(parts) + "," + last_3
        res = f"{int_part}.{dec_part}"
        return f"-{res}" if is_negative else res
    return f"{num:,.2f}"

# --- URL PARAMETER MANAGEMENT (Shareable Links) ---
def get_param(key, default, cast_type):
    if key in st.query_params:
        try:
            return cast_type(st.query_params[key])
        except ValueError:
            return default
    return default

# --- SIDEBAR: INPUTS & SETTINGS ---
st.sidebar.title("⚙️ Loan Parameters")

# 1. Formatting Settings
fmt_system = st.sidebar.radio("Number Format",["Western", "Indian (Lakhs/Crores)"], horizontal=True)

# 2. Basic Details
st.sidebar.header("📝 Basic Details")
principal = st.sidebar.number_input("Loan Amount", min_value=1000, value=get_param("p", 500000, int), step=10000)
annual_rate = st.sidebar.slider("Annual Interest Rate (%)", 0.1, 20.0, get_param("r", 8.5, float), 0.1)
years = st.sidebar.slider("Loan Term (Years)", 1, 40, get_param("y", 20, int))
start_date = st.sidebar.date_input("Loan Start Date", value=date.today())

# Update base Query Params for sharing
st.query_params.update({"p": principal, "r": annual_rate, "y": years})

# 3. PITI Options
with st.sidebar.expander("🏦 PITI (Taxes & Insurance)", expanded=False):
    annual_tax = st.number_input("Annual Property Tax", min_value=0, value=0, step=500)
    annual_ins = st.number_input("Annual Home Insurance", min_value=0, value=0, step=100)

# 4. Advanced Math Frequencies
with st.sidebar.expander("⏱️ Frequencies & Compounding", expanded=False):
    payment_freq = st.selectbox("Payment Frequency",["Monthly", "Accelerated Bi-Weekly"], help="Bi-Weekly takes your monthly payment, splits it in half, and pays it every 2 weeks. This results in 1 extra full payment a year.")
    compounding = st.selectbox("Interest Compounding",["Monthly", "Daily", "Semi-Annual (Canadian)"])

# 5. Prepayments
with st.sidebar.expander("🚀 Prepayment Strategies", expanded=False):
    extra_payment = st.number_input("Extra per Payment", min_value=0, value=0, step=100, help="Added to every single payment you make.")
    st.markdown("---")
    recurring_lump = st.number_input("Annual Bonus Lump Sum", min_value=0, value=0, step=1000, help="A recurring payment made once every year.")
    recurring_month = st.selectbox("Month for Annual Bonus", range(1, 13), index=11, format_func=lambda x: datetime(2000, x, 1).strftime('%B'))
    st.markdown("---")
    one_time_lump = st.number_input("One-Time Lump Sum", min_value=0, value=0, step=5000)
    one_time_date = st.date_input("Date of One-Time Lump Sum", value=date.today())

# 6. Floating Rates
with st.sidebar.expander("📈 Floating Rate / Trends", expanded=False):
    rate_trend_active = st.checkbox("Enable Floating Rate Trend")
    trend_amount = st.number_input("Increase rate by (%)", value=0.25, step=0.05, help="Simulate central bank hikes.")
    trend_months = st.number_input("Every X months", min_value=1, value=12)

# --- CORE MATH ENGINE ---
@st.cache_data
def run_amortization(p, r_annual, yrs, start_dt, freq, comp, ext_pay, rec_lump, rec_mo, one_lump, one_dt, trnd_act, trnd_amt, trnd_mo):
    data =[]
    balance = p
    current_date = pd.to_datetime(start_dt)
    
    periods_per_year = 26 if freq == "Accelerated Bi-Weekly" else 12
    total_periods = yrs * periods_per_year
    
    # Compounding Logic
    def get_period_rate(annual_pct):
        r = annual_pct / 100
        if comp == "Monthly":
            return r / 12 if periods_per_year == 12 else ((1 + r/12)**(12/26) - 1)
        elif comp == "Daily":
            return (1 + r / 365) ** (365 / periods_per_year) - 1
        elif comp == "Semi-Annual (Canadian)":
            return (1 + r / 2) ** (2 / periods_per_year) - 1

    # Standard EMI Formula
    def get_emi(princ, rate_per_period, periods_left):
        if rate_per_period == 0: return princ / periods_left
        return princ * (rate_per_period * (1 + rate_per_period)**periods_left) / ((1 + rate_per_period)**periods_left - 1)

    # Base monthly calculation to find accelerated bi-weekly true amount
    monthly_rate = get_period_rate(r_annual) if periods_per_year == 12 else (((1 + r_annual/100/12)**12)**(1/12) - 1)
    base_monthly_emi = get_emi(p, r_annual/100/12 if comp=="Monthly" else get_period_rate(r_annual), yrs * 12)
    
    base_payment = base_monthly_emi if periods_per_year == 12 else base_monthly_emi / 2

    current_rate = r_annual
    last_rec_year = current_date.year - 1
    applied_one_time = False

    # Tax & Ins breakdown per period
    period_tax = annual_tax / periods_per_year
    period_ins = annual_ins / periods_per_year

    for period in range(1, total_periods * 3): # Cap at 3x term length to prevent infinite loops on crazy rate hikes
        # Advance Date
        if freq == "Monthly":
            current_date += pd.DateOffset(months=1)
        else:
            current_date += pd.Timedelta(days=14)
            
        # Floating Rate adjustments
        if trnd_act and period > 1 and period % (trnd_mo * (26/12 if periods_per_year==26 else 1)) == 0:
            current_rate += trnd_amt
            rem_periods = total_periods - period + 1
            if rem_periods > 0:
                base_payment = get_emi(balance, get_period_rate(current_rate), rem_periods)

        period_r = get_period_rate(current_rate)
        interest = balance * period_r
        
        # Payment application
        principal_pay = base_payment - interest
        actual_principal = principal_pay + ext_pay
        
        # Recurring Annual Lump Sum
        if rec_lump > 0 and current_date.month == rec_mo and current_date.year > last_rec_year:
            actual_principal += rec_lump
            last_rec_year = current_date.year
            
        # One Time Lump Sum
        if one_lump > 0 and not applied_one_time and current_date >= pd.to_datetime(one_dt):
            actual_principal += one_lump
            applied_one_time = True

        # Safety Check
        if actual_principal >= balance:
            actual_principal = balance
            balance = 0

        total_period_outflow = interest + actual_principal + period_tax + period_ins
        balance -= actual_principal

        data.append({
            "Period": period,
            "Date": current_date.date(),
            "Rate (%)": current_rate,
            "Payment Outflow": total_period_outflow,
            "Interest": interest,
            "Principal": actual_principal,
            "Taxes & Ins": period_tax + period_ins,
            "Remaining Balance": balance
        })

        if balance <= 0:
            break

    return pd.DataFrame(data)

# --- EXECUTE ENGINE ---
df_base = run_amortization(principal, annual_rate, years, start_date, "Monthly", "Monthly", 0, 0, 1, 0, start_date, False, 0, 1)
df_actual = run_amortization(principal, annual_rate, years, start_date, payment_freq, compounding, extra_payment, recurring_lump, recurring_month, one_time_lump, one_time_date, rate_trend_active, trend_amount, trend_months)

# --- METRICS CALCULATIONS ---
base_interest = df_base["Interest"].sum()
actual_interest = df_actual["Interest"].sum()
interest_saved = base_interest - actual_interest

payoff_date_base = df_base.iloc[-1]["Date"]
payoff_date_actual = df_actual.iloc[-1]["Date"]

# Find Cross-Over Date (Where Principal > Interest)
cross_over_df = df_actual[df_actual["Principal"] > df_actual["Interest"]]
cross_over_date = cross_over_df.iloc[0]["Date"].strftime('%B %Y') if not cross_over_df.empty else "N/A"

# --- MAIN DASHBOARD UI ---
st.title("🏦 Pro Loan Architect")
st.markdown("Analyze amortization schedules, compare compounding methods, and discover your true **Total Cost of Ownership (PITI)**.")
st.info("💡 **Pro Tip:** Look at your URL bar. As you change settings, your URL updates automatically. Copy and paste it to a friend to share this exact scenario!")

st.markdown("### 🎯 Scenario Summary")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Original Total Interest", format_num(base_interest, fmt_system))
c2.metric("Actual Total Interest", format_num(actual_interest, fmt_system))

if interest_saved >= 0:
    c3.metric("Interest Saved 🎉", format_num(interest_saved, fmt_system), f"+{format_num(interest_saved, fmt_system)}")
    c4.metric("Actual Payoff Date", payoff_date_actual.strftime('%b %Y'), f"Saved {(payoff_date_base.year - payoff_date_actual.year)*12 + (payoff_date_base.month - payoff_date_actual.month)} mos")
else:
    c3.metric("Extra Interest Paid 📉", format_num(abs(interest_saved), fmt_system), f"-{format_num(abs(interest_saved), fmt_system)}")
    c4.metric("Actual Payoff Date", payoff_date_actual.strftime('%b %Y'))

if cross_over_date != "N/A":
    st.success(f"🔥 **Cross-Over Milestone:** In **{cross_over_date}**, you will officially start paying more toward your Home's Principal than to the Bank's Interest!")

st.markdown("---")

tab1, tab2 = st.tabs(["📊 Visual Analytics", "📑 Detailed Schedule"])

with tab1:
    fig_bal = go.Figure()
    fig_bal.add_trace(go.Scatter(x=df_base["Date"], y=df_base["Remaining Balance"], name="Standard Balance", line=dict(color='gray', dash='dash')))
    fig_bal.add_trace(go.Scatter(x=df_actual["Date"], y=df_actual["Remaining Balance"], fill='tozeroy', name="Optimized Balance", line=dict(color='royalblue')))
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
        fig_cash.add_trace(go.Scatter(x=df_actual["Date"], y=df_actual["Cum_Outflow"], fill='tozeroy', name="Total Cash Outflow (Inc. Tax & Ins)", line=dict(color='orange')))
        fig_cash.update_layout(title="Total Cash Outflow (PITI)", xaxis_title="Timeline", yaxis_title="Cumulative Outflow", hovermode="x unified", height=400)
        st.plotly_chart(fig_cash, use_container_width=True)

with tab2:
    st.subheader("Amortization Ledger")
    
    # Create display dataframe using the chosen number format
    display_df = df_actual.copy()
    display_cols =["Payment Outflow", "Interest", "Principal", "Taxes & Ins", "Remaining Balance"]
    for col in display_cols:
        display_df[col] = display_df[col].apply(lambda x: format_num(x, fmt_system))
    
    st.dataframe(display_df, use_container_width=True, height=500)

    st.download_button("📥 Download Ledger (CSV)", data=df_actual.to_csv(index=False).encode('utf-8'), file_name="pro_amortization.csv", mime="text/csv")