import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Advanced Loan Calculator", layout="wide", initial_sidebar_state="expanded")

st.title("📊 Interactive Loan Calculator")
st.markdown("Analyze your loan amortization, simulate **prepayments**, and visualize your **savings**.")

# --- SIDEBAR INPUTS ---
st.sidebar.header("📝 Basic Loan Details")
principal = st.sidebar.number_input("Loan Amount", min_value=1000, value=500000, step=10000)
annual_interest_rate = st.sidebar.slider("Annual Interest Rate (%)", 0.1, 20.0, 8.5, 0.1)
loan_term_years = st.sidebar.slider("Loan Term (Years)", 1, 40, 20)

# Prepayment Options in an expander
with st.sidebar.expander("🚀 Prepayment Options", expanded=False):
    extra_monthly_payment = st.number_input("Extra Monthly Payment", min_value=0, value=0, step=500)
    extra_lump_sum = st.number_input("One-time Lump Sum", min_value=0, value=0, step=5000)
    lump_sum_month = st.number_input("Lump Sum Month (e.g., Month 12)", min_value=1, value=12)

# Interest Rate Changes in an expander
with st.sidebar.expander("📈 Interest Rate Change", expanded=False):
    rate_change_trigger = st.checkbox("Simulate Rate Change")
    new_rate = st.number_input("New Interest Rate (%)", min_value=0.1, max_value=30.0, value=9.5, step=0.1)
    rate_change_month = st.number_input("Month rate changes", min_value=1, value=36)

# --- CORE LOGIC ENGINE ---
def calculate_amortization(principal, annual_rate, years, extra_monthly=0, lump_sum=0, lump_sum_mo=0, rate_change_active=False, new_rate=0.0, rate_change_mo=0):
    data =[]
    balance = principal
    monthly_rate = (annual_rate / 100) / 12
    total_months = int(years * 12)
    
    # Standard EMI formula
    def get_emi(p, r, n):
        if r == 0: return p / n
        return p * (r * (1 + r)**n) / ((1 + r)**n - 1)

    current_emi = get_emi(balance, monthly_rate, total_months)

    for month in range(1, total_months + 1):
        # 1. Handle Interest Rate Change
        if rate_change_active and month == rate_change_mo:
            monthly_rate = (new_rate / 100) / 12
            months_left = total_months - month + 1
            if months_left > 0 and balance > 0:
                current_emi = get_emi(balance, monthly_rate, months_left)

        interest_payment = balance * monthly_rate
        principal_payment = current_emi - interest_payment
        
        # 2. Add Prepayments
        actual_principal_payment = principal_payment + extra_monthly
        
        # Apply Lump Sum
        if month == lump_sum_mo:
            actual_principal_payment += lump_sum

        # 3. Safety check to prevent negative balance
        if actual_principal_payment >= balance:
            actual_principal_payment = balance
            balance = 0
        else:
            balance -= actual_principal_payment

        data.append({
            "Month": month,
            "Total Payment": interest_payment + actual_principal_payment,
            "Interest": interest_payment,
            "Principal": actual_principal_payment,
            "Remaining Balance": balance
        })

        if balance <= 0:
            break

    return pd.DataFrame(data)

# --- RUN CALCULATIONS ---
# Calculate Baseline (No prepayments, no rate changes)
df_base = calculate_amortization(principal, annual_interest_rate, loan_term_years)

# Calculate Actual Scenario
df_actual = calculate_amortization(
    principal, annual_interest_rate, loan_term_years, 
    extra_monthly_payment, extra_lump_sum, lump_sum_month,
    rate_change_trigger, new_rate, rate_change_month
)

# --- METRICS CALCULATIONS ---
base_interest = df_base["Interest"].sum()
actual_interest = df_actual["Interest"].sum()
interest_saved = base_interest - actual_interest

base_months = len(df_base)
actual_months = len(df_actual)
months_saved = base_months - actual_months

# --- UI DASHBOARD ---
st.markdown("### 💡 Savings & Summary")
col1, col2, col3, col4 = st.columns(4)

col1.metric("Original Total Interest", f"{base_interest:,.2f}")
col2.metric("Actual Total Interest", f"{actual_interest:,.2f}")

# Highlight savings in green if positive, red if negative (due to rate hikes)
if interest_saved >= 0:
    col3.metric("Interest Saved 🎉", f"{interest_saved:,.2f}", f"+{interest_saved:,.2f}")
    col4.metric("Time Saved ⏱️", f"{months_saved} months", f"-{months_saved / 12:.1f} years")
else:
    col3.metric("Extra Interest Paid", f"{abs(interest_saved):,.2f}", f"-{abs(interest_saved):,.2f}")
    col4.metric("Time Difference", f"{months_saved} months")

st.markdown("---")

# --- TABS FOR CHARTS AND TABLES ---
tab1, tab2 = st.tabs(["📈 Interactive Charts", "📋 Amortization Schedule"])

with tab1:
    st.subheader("Loan Balance: Baseline vs. Actual")
    fig_balance = go.Figure()
    
    # Baseline plot (Dotted line)
    fig_balance.add_trace(go.Scatter(
        x=df_base["Month"], y=df_base["Remaining Balance"], 
        name="Baseline Balance", line=dict(color='gray', dash='dash')
    ))
    
    # Actual plot (Solid fill area)
    fig_balance.add_trace(go.Scatter(
        x=df_actual["Month"], y=df_actual["Remaining Balance"], 
        fill='tozeroy', name="Actual Balance", line=dict(color='royalblue')
    ))
    
    fig_balance.update_layout(xaxis_title="Month", yaxis_title="Remaining Balance", height=450, hovermode="x unified")
    st.plotly_chart(fig_balance, use_container_width=True)

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Payment Breakdown (Actual)")
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Scatter(x=df_actual["Month"], y=df_actual["Interest"], name="Interest Paid", line=dict(color='tomato')))
        fig_comp.add_trace(go.Scatter(x=df_actual["Month"], y=df_actual["Principal"], name="Principal Paid", line=dict(color='mediumseagreen')))
        fig_comp.update_layout(xaxis_title="Month", yaxis_title="Amount", height=400, hovermode="x unified")
        st.plotly_chart(fig_comp, use_container_width=True)

    with col_right:
        st.subheader("Cumulative Interest Paid")
        df_actual["Cum_Interest"] = df_actual["Interest"].cumsum()
        df_base["Cum_Interest_Base"] = df_base["Interest"].cumsum()
        
        fig_cum = go.Figure()
        fig_cum.add_trace(go.Scatter(x=df_base["Month"], y=df_base["Cum_Interest_Base"], name="Baseline Interest", line=dict(color='gray', dash='dash')))
        fig_cum.add_trace(go.Scatter(x=df_actual["Month"], y=df_actual["Cum_Interest"], name="Actual Interest", line=dict(color='orange')))
        fig_cum.update_layout(xaxis_title="Month", yaxis_title="Cumulative Interest", height=400, hovermode="x unified")
        st.plotly_chart(fig_cum, use_container_width=True)

with tab2:
    st.subheader("Detailed Amortization Table")
    
    # Format the dataframe without currency symbols, keeping 2 decimal places
    styled_df = df_actual.style.format({
        "Total Payment": "{:,.2f}",
        "Interest": "{:,.2f}",
        "Principal": "{:,.2f}",
        "Remaining Balance": "{:,.2f}"
    })
    
    st.dataframe(styled_df, use_container_width=True, height=500)

    # Download Button (no changes required here)
    csv = df_actual.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Schedule as CSV",
        data=csv,
        file_name="amortization_schedule.csv",
        mime="text/csv"
    )