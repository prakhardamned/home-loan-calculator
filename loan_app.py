import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Advanced Home Loan Calculator", layout="wide")

st.title("🏠 Advanced Home Loan Calculator")
st.markdown("Calculate your amortization, simulate **prepayments**, and model **interest rate changes**.")

# --- SIDEBAR INPUTS ---
st.sidebar.header("Loan Parameters")
principal = st.sidebar.number_input("Loan Amount ($)", min_value=1000, value=300000, step=5000)
annual_interest_rate = st.sidebar.slider("Initial Interest Rate (%)", 0.1, 15.0, 6.5, 0.1)
loan_term_years = st.sidebar.slider("Loan Term (Years)", 1, 30, 30)

st.sidebar.header("Prepayment Strategy")
extra_monthly_payment = st.sidebar.number_input("Extra Monthly Prepayment ($)", min_value=0, value=0, step=100)
extra_lump_sum = st.sidebar.number_input("One-time Lump Sum Prepayment ($)", min_value=0, value=0, step=1000)
lump_sum_month = st.sidebar.number_input("Lump Sum Month (e.g., month 12)", min_value=1, value=12)

st.sidebar.header("Interest Rate Change Scenario")
rate_change_trigger = st.sidebar.checkbox("Enable Interest Rate Change")
new_rate = st.sidebar.number_input("New Interest Rate (%)", min_value=0.1, max_value=20.0, value=7.5, step=0.1)
rate_change_month = st.sidebar.number_input("Month when rate changes", min_value=1, value=60)

# --- CALCULATION LOGIC ---

def calculate_amortization(principal, annual_rate, years, extra_monthly, lump_sum, lump_sum_mo, rate_change_mo, new_rate, rate_change_active):
    data = []
    balance = principal
    monthly_rate = (annual_rate / 100) / 12
    total_months = years * 12
    
    # Calculate standard monthly payment (EMI)
    def get_emi(p, r, n):
        if r == 0: return p / n
        return p * (r * (1 + r)**n) / ((1 + r)**n - 1)

    current_emi = get_emi(balance, monthly_rate, total_months)

    for month in range(1, total_months + 1):
        # 1. Handle Interest Rate Change
        if rate_change_active and month == rate_change_mo:
            monthly_rate = (new_rate / 100) / 12
            # Recalculate EMI based on remaining balance and remaining months
            months_left = total_months - month + 1
            current_emi = get_emi(balance, monthly_rate, months_left)

        interest_payment = balance * monthly_rate
        principal_payment = current_emi - interest_payment
        
        # 2. Add Prepayments
        actual_principal_payment = principal_payment + extra_monthly
        
        # Apply Lump Sum
        if month == lump_sum_mo:
            actual_principal_payment += lump_sum

        # 3. Safety check: Don't overpay the loan
        if actual_principal_payment > balance:
            actual_principal_payment = balance
            interest_payment = max(0, interest_payment) # Simplified
            balance = 0
        else:
            balance -= actual_principal_payment

        data.append({
            "Month": month,
            "Payment": interest_payment + actual_principal_payment,
            "Interest": interest_payment,
            "Principal": actual_principal_payment,
            "Remaining Balance": max(0, balance)
        })

        if balance <= 0:
            break

    return pd.DataFrame(data)

# Run Calculation
df = calculate_amortization(
    principal, annual_interest_rate, loan_term_years, 
    extra_monthly_payment, extra_lump_sum, lump_sum_month,
    rate_change_month, new_rate, rate_change_trigger
)

# --- DASHBOARD LAYOUT ---

# Metrics
col1, col2, col3, col4 = st.columns(4)
total_paid = df["Payment"].sum()
total_interest = df["Interest"].sum()
actual_term = len(df)

col1.metric("Total Paid", f"${total_paid:,.2f}")
col2.metric("Total Interest", f"${total_interest:,.2f}")
col3.metric("Months to Payoff", f"{actual_term} months")
col4.metric("Years to Payoff", f"{actual_term/12:.1f} years")

# Charts
st.subheader("Loan Balance Over Time")
fig_balance = go.Figure()
fig_balance.add_trace(go.Scatter(x=df["Month"], y=df["Remaining Balance"], fill='tozeroy', name="Remaining Balance", line=dict(color='royalblue')))
fig_balance.update_layout(xaxis_title="Month", yaxis_title="Balance ($)", height=400)
st.plotly_chart(fig_balance, use_container_width=True)

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Interest vs Principal")
    fig_comp = go.Figure()
    fig_comp.add_trace(go.Scatter(x=df["Month"], y=df["Interest"], name="Interest", line=dict(color='red')))
    fig_comp.add_trace(go.Scatter(x=df["Month"], y=df["Principal"], name="Principal", line=dict(color='green')))
    fig_comp.update_layout(xaxis_title="Month", yaxis_title="Amount ($)", height=400)
    st.plotly_chart(fig_comp, use_container_width=True)

with col_right:
    st.subheader("Cumulative Interest Paid")
    df["Cum_Interest"] = df["Interest"].cumsum()
    fig_cum = go.Figure()
    fig_cum.add_trace(go.Scatter(x=df["Month"], y=df["Cum_Interest"], name="Cumulative Interest", line=dict(color='orange')))
    fig_cum.update_layout(xaxis_title="Month", yaxis_title="Total Interest ($)", height=400)
    st.plotly_chart(fig_cum, use_container_width=True)

# Amortization Table
st.subheader("Amortization Schedule")
st.dataframe(df.style.format({
    "Payment": "${:,.2f}",
    "Interest": "${:,.2f}",
    "Principal": "${:,.2f}",
    "Remaining Balance": "${:,.2f}"
}), use_container_width=True)

# Download Button
csv = df.to_csv(index=False).encode('utf-8')
st.download_button("Download Schedule as CSV", data=csv, file_name="amortization_schedule.csv", mime="text/csv")