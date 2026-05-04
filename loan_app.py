import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Pro Loan Architect", layout="wide", initial_sidebar_state="expanded")

# --- UTILITY: NUMBER FORMATTING ---
def format_num(num, system="Western"):
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

fmt_system = st.sidebar.radio("Number Format",["Western", "Indian (Lakhs/Crores)"], index=1, horizontal=True)

st.sidebar.header("📝 Basic Details")
principal = st.sidebar.number_input("Loan Amount", min_value=1000.0, value=get_param("p", 5000000.0, float), step=100000.0)
annual_rate = st.sidebar.number_input("Initial Interest Rate (%)", min_value=0.10, max_value=25.00, value=get_param("r", 8.50, float), step=0.05, format="%.2f")
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
    st.markdown("**1. Regular Prepayments**")
    extra_payment = st.number_input("Extra per Payment", min_value=0.0, value=0.0, step=1000.0)
    recurring_lump = st.number_input("Annual Bonus Lump Sum", min_value=0.0, value=0.0, step=10000.0)
    recurring_month = st.selectbox("Month for Annual Bonus", range(1, 13), index=11, format_func=lambda x: datetime(2000, x, 1).strftime('%B'))
    
    st.markdown("---")
    st.markdown("**2. Irregular / Random Lump Sums**")
    default_lumps = pd.DataFrame([{"Payment Date": date.today(), "Amount": 0.0}])
    edited_lumps = st.data_editor(
        default_lumps, 
        num_rows="dynamic", 
        hide_index=True,
        column_config={
            "Payment Date": st.column_config.DateColumn("Date", required=True),
            "Amount": st.column_config.NumberColumn("Amount", min_value=0.0, step=10000.0, required=True)
        }
    )
    
    # QA FIX: Empty Grid safety handler
    custom_lump_sums =[]
    if not edited_lumps.empty:
        for _, row in edited_lumps.iterrows():
            if pd.notna(row.get("Payment Date")) and pd.notna(row.get("Amount")) and row.get("Amount") > 0:
                custom_lump_sums.append((pd.to_datetime(row["Payment Date"]), float(row["Amount"])))
    custom_lump_tuple = tuple(custom_lump_sums)

with st.sidebar.expander("📈 Floating Rate / Trends", expanded=False):
    rate_trend_active = st.checkbox("Enable Interest Rate Changes")
    
    # QA FIX: Business Logic for Indian Banking (RLLR) vs Western Banking
    rate_action = st.radio("When Rates Change, the Bank will:",[
        "Keep EMI Same (Adjust Tenure)", 
        "Recalculate EMI (Loan Recasting)"
    ], help="Indian banks default to keeping your EMI the same and extending your tenure when rates rise.")

    rate_mode = st.radio("Rate Change Mode",["Predictable Trend", "Custom Schedule (RBI Style)"])
    
    if rate_mode == "Predictable Trend":
        trend_amount = st.number_input("Increase rate by (%)", value=0.25, step=0.05)
        trend_months = st.number_input("Every X months", min_value=1, value=12)
        custom_rates_dict = {}
    else:
        st.markdown("<small>Enter specific months (e.g., 18 = 1.5 years from start) and the **New Total Rate**.</small>", unsafe_allow_html=True)
        default_schedule = pd.DataFrame([{"Month": 14, "New Rate (%)": 9.25}, {"Month": 36, "New Rate (%)": 8.50}])
        edited_df = st.data_editor(default_schedule, num_rows="dynamic", hide_index=True)
        
        custom_rates_dict = {}
        if not edited_df.empty:
            for _, row in edited_df.iterrows():
                if pd.notna(row.get("Month")) and pd.notna(row.get("New Rate (%)")):
                    try:
                        custom_rates_dict[int(row["Month"])] = float(row["New Rate (%)"])
                    except ValueError:
                        pass
        trend_amount = 0.0
        trend_months = 1

# --- CORE MATH ENGINE ---
@st.cache_data
def run_amortization(p, r_annual, yrs, start_dt, freq, comp, ext_pay, rec_lump, rec_mo, irregular_lumps, trnd_act, rate_mode_sel, rate_action_sel, trnd_amt, trnd_mo, custom_rates):
    data =[]
    balance = float(p)
    current_date = pd.to_datetime(start_dt)
    start_datetime = pd.to_datetime(start_dt)
    
    periods_per_year = 26 if freq == "Accelerated Bi-Weekly" else 12
    total_periods = yrs * periods_per_year
    failsafe_cap = total_periods * 3
    
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
    neg_amortization_flag = False
    infinite_loan_flag = False
    last_applied_custom_month = -1
    applied_lump_indices = set()

    period_tax = annual_tax / periods_per_year
    period_ins = annual_ins / periods_per_year
    trend_period_interval = int(round(trnd_mo * (26/12))) if periods_per_year == 26 else int(trnd_mo)

    for period in range(1, failsafe_cap):
        if freq == "Monthly":
            current_date += pd.DateOffset(months=1)
        else:
            current_date += pd.Timedelta(days=14)
            
        months_elapsed = (current_date.year - start_datetime.year) * 12 + (current_date.month - start_datetime.month)
        rate_changed = False
        
        # --- FLOATING RATE ENGINE ---
        if trnd_act:
            if rate_mode_sel == "Predictable Trend":
                if period > 1 and (period - 1) % trend_period_interval == 0:
                    current_rate += trnd_amt
                    rate_changed = True
            elif rate_mode_sel == "Custom Schedule (RBI Style)":
                if months_elapsed in custom_rates and months_elapsed != last_applied_custom_month:
                    current_rate = custom_rates[months_elapsed]
                    last_applied_custom_month = months_elapsed
                    rate_changed = True
                    
        if rate_changed:
            # QA FIX: Handle Prepayment/Tenure logic correctly based on user choice
            if rate_action_sel == "Recalculate EMI (Loan Recasting)":
                rem_periods = total_periods - period + 1
                if rem_periods > 0 and balance > 0:
                    base_payment = get_emi(balance, get_period_rate(current_rate), rem_periods)
            # If "Keep EMI Same", we explicitly do nothing to base_payment.
        
        period_r = get_period_rate(current_rate)
        interest = balance * period_r
        
        principal_pay = base_payment - interest
        actual_principal = principal_pay + ext_pay
        
        # Process Prepayments
        if rec_lump > 0 and current_date.month == rec_mo and current_date.year > last_rec_year:
            actual_principal += rec_lump
            last_rec_year = current_date.year
            
        for i, (l_date, l_amt) in enumerate(irregular_lumps):
            if i not in applied_lump_indices and current_date >= l_date:
                actual_principal += l_amt
                applied_lump_indices.add(i)

        if actual_principal < 0:
            neg_amortization_flag = True

        if actual_principal >= balance:
            actual_principal = balance
            balance = 0
        else:
            balance -= actual_principal

        data.append({
            "Period": period,
            "Date": current_date.date(),
            "Rate (%)": round(current_rate, 3), 
            "Payment Outflow": interest + actual_principal + period_tax + period_ins,
            "Interest": interest,
            "Principal": actual_principal,
            "Taxes & Ins": period_tax + period_ins,
            "Remaining Balance": balance
        })

        if balance <= 0:
            break
            
        # QA FIX: Catch if loan hits failsafe cap without paying off
        if period == failsafe_cap - 1 and balance > 0:
            infinite_loan_flag = True

    return pd.DataFrame(data), neg_amortization_flag, infinite_loan_flag

# --- EXECUTE ENGINE ---
df_base, _, _ = run_amortization(principal, annual_rate, years, start_date, "Monthly", "Monthly", 0, 0, 1, (), False, "Predictable Trend", "Keep EMI Same (Adjust Tenure)", 0, 1, {})
df_actual, has_neg_amortization, is_infinite = run_amortization(principal, annual_rate, years, start_date, payment_freq, compounding, extra_payment, recurring_lump, recurring_month, custom_lump_tuple, rate_trend_active, rate_mode, rate_action, trend_amount, trend_months, custom_rates_dict)

# --- METRICS & ALERTS ---
st.title("🏦 Pro Loan Architect")

if has_neg_amortization:
    st.error("⚠️ **CRITICAL WARNING: Negative Amortization Detected!** Your interest rate has climbed so high that your payments no longer cover the monthly interest. Your loan balance is actually *growing*.")
if is_infinite:
    st.error("🚨 **INFINITE LOAN DETECTED:** Your current parameters will never pay off the loan. The calculation was capped to prevent a server crash.")

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

# QA FIX: Mask output if loan is infinite
if is_infinite:
    c2.metric("Actual Total Interest", "Infinite 🚨")
    c3.metric("Status", "Will Never Pay Off", "-∞")
    c4.metric("Actual Payoff Date", "NEVER")
else:
    c2.metric("Actual Total Interest", format_num(actual_interest, fmt_system))
    if interest_saved >= 0:
        c3.metric("Interest Saved 🎉", format_num(interest_saved, fmt_system), f"+{format_num(interest_saved, fmt_system)}")
        c4.metric("Actual Payoff Date", payoff_date_actual.strftime('%b %Y'), f"Saved {month_diff} mos")
    else:
        c3.metric("Extra Interest Paid 📉", format_num(abs(interest_saved), fmt_system), f"-{format_num(abs(interest_saved), fmt_system)}")
        c4.metric("Actual Payoff Date", payoff_date_actual.strftime('%b %Y'), f"Extended by {abs(month_diff)} mos")

if cross_over_date and not has_neg_amortization and not is_infinite:
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
