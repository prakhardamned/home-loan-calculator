
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Pro Loan Architect", layout="wide", initial_sidebar_state="expanded")

# --- SIDEBAR_BUTTON_STYLES ---
st.markdown(
    """
<style>
  section[data-testid="stSidebar"] button {
    font-weight: 600 !important;
    border-radius: 12px !important;
  }
  /* Brighten both action buttons */
  section[data-testid="stSidebar"] button[kind="primary"] {
    background: #2563eb !important;
    border: 1px solid #1d4ed8 !important;
    color: white !important;
  }
  section[data-testid="stSidebar"] button[kind="secondary"] {
    background: #e2e8f0 !important;
    border: 1px solid #94a3b8 !important;
    color: #0f172a !important;
  }
</style>
""",
    unsafe_allow_html=True,
)

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
            parts = []
            while rem:
                parts.append(rem[-2:])
                rem = rem[:-2]
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
        except Exception:
            return default
    return default

# --- SHAREABLE URL ENCODERS/DECODERS ---
def _drop_none(d: dict) -> dict:
    return {k: v for k, v in d.items() if v not in (None, "", [])}


def enc_freq(freq: str) -> str:
    return "B" if freq == "Accelerated Bi-Weekly" else "M"


def dec_freq(v: str) -> str:
    return "Accelerated Bi-Weekly" if str(v).upper() == "B" else "Monthly"


def enc_comp(comp: str) -> str:
    return {"Monthly": "M", "Daily": "D", "Semi-Annual (Canadian)": "S"}.get(comp, "M")


def dec_comp(v: str) -> str:
    return {"M": "Monthly", "D": "Daily", "S": "Semi-Annual (Canadian)"}.get(str(v).upper(), "Monthly")


def enc_rate_action(a: str) -> str:
    return "R" if a.startswith("Recalculate") else "K"


def dec_rate_action(v: str) -> str:
    return "Recalculate EMI (Loan Recasting)" if str(v).upper() == "R" else "Keep EMI Same (Adjust Tenure)"


def enc_rate_mode(m: str) -> str:
    return "C" if m.startswith("Custom") else "T"


def dec_rate_mode(v: str) -> str:
    return "Custom Schedule (RBI Style)" if str(v).upper() == "C" else "Predictable Trend"


def encode_rate_schedule(d: dict) -> str:
    items = sorted(d.items(), key=lambda x: x[0])
    return ";".join(f"{k}:{float(v):.4f}" for k, v in items)


def decode_rate_schedule(s: str) -> dict:
    out = {}
    if not s:
        return out
    for part in str(s).split(";"):
        try:
            d, r = part.split(":")
            out[d] = float(r)
        except Exception:
            pass
    return out


def encode_lumps(lumps: tuple) -> str:
    parts = []
    for d, a in lumps:
        try:
            parts.append(f"{pd.to_datetime(d).date().isoformat()}:{float(a):.2f}")
        except Exception:
            pass
    return ";".join(parts)


def decode_lumps(s: str) -> tuple:
    out = []
    if not s:
        return tuple(out)
    for part in str(s).split(";"):
        try:
            d, a = part.split(":")
            out.append((pd.to_datetime(d), float(a)))
        except Exception:
            pass
    return tuple(out)


# --- DEFAULTS FROM URL (restore scenario from shared link) ---
principal_default = get_param("p", 5_000_000.0, float)
annual_rate_default = get_param("r", 8.50, float)
years_default = get_param("y", 20, int)

sd = get_param("sd", date.today().isoformat(), str)
try:
    start_date_default = pd.to_datetime(sd).date()
except Exception:
    start_date_default = date.today()

fmt_default = get_param("fmt", "I", str).upper()
fmt_system_default = "Indian (Lakhs/Crores)" if fmt_default == "I" else "Western"

annual_tax_default = get_param("at", 0.0, float)
annual_ins_default = get_param("ai", 0.0, float)

payment_freq_default = dec_freq(get_param("f", "M", str))
compounding_default = dec_comp(get_param("c", "M", str))

extra_payment_default = get_param("ep", 0.0, float)

recurring_lump_default = 0.0
recurring_month_default = 12
if "ab" in st.query_params:
    try:
        amt, mo = str(st.query_params["ab"]).split("@")
        recurring_lump_default = float(amt)
        recurring_month_default = int(mo)
    except Exception:
        pass

custom_lump_tuple_default = decode_lumps(st.query_params.get("ls", ""))
custom_rates_dict_default = decode_rate_schedule(st.query_params.get("rs", ""))

rate_trend_active_default = str(st.query_params.get("rt", "0")).lower() in ("1", "true", "yes", "y")
rate_action_default = dec_rate_action(st.query_params.get("ra", "K"))
rate_mode_default = dec_rate_mode(st.query_params.get("rm", "T"))
trend_amount_default = get_param("ta", 0.25, float)
trend_months_default = get_param("tm", 12, int)


# -------------------------------------------------
# SIDEBAR
# -------------------------------------------------
st.sidebar.markdown("### ⚙️ Loan Parameters")

# All primary inputs in a form (prevents constant reruns)
with st.sidebar.form("loan_form", clear_on_submit=False):
    # Top action row: Reset + Calculate
    b1, b2 = st.columns(2)
    with b1:
        reset_submit = st.form_submit_button("🔄 Reset", use_container_width=True, type="secondary")
    with b2:
        calc_submit = st.form_submit_button("🚀 Calculate", use_container_width=True, type="primary")

    st.markdown('---')

    fmt_system = st.radio(
        "Number Format",
        ["Western", "Indian (Lakhs/Crores)"],
        index=1 if fmt_system_default.startswith("Indian") else 0,
        horizontal=True,
    )

    st.header("📝 Basic Details")
    principal = st.number_input("Loan Amount", min_value=1000.0, value=float(principal_default), step=100000.0)
    annual_rate = st.number_input("Initial Interest Rate (%)", min_value=0.10, max_value=25.00, value=float(annual_rate_default), step=0.05, format="%.2f")
    years = st.slider("Loan Term (Years)", 1, 50, int(years_default))
    start_date = st.date_input("Loan Start Date", value=start_date_default)

    with st.expander("🏦 PITI (Taxes & Insurance)", expanded=False):
        annual_tax = st.number_input("Annual Property Tax", min_value=0.0, value=float(annual_tax_default), step=500.0)
        annual_ins = st.number_input("Annual Home Insurance", min_value=0.0, value=float(annual_ins_default), step=100.0)

    with st.expander("⏱️ Compounding & Frequencies", expanded=False):
        payment_freq = st.selectbox(
            "Payment Frequency",
            ["Monthly", "Accelerated Bi-Weekly"],
            index=0 if payment_freq_default == "Monthly" else 1,
        )
        compounding = st.selectbox(
            "Interest Compounding",
            ["Monthly", "Daily", "Semi-Annual (Canadian)"],
            index=["Monthly", "Daily", "Semi-Annual (Canadian)"].index(compounding_default),
        )

    with st.expander("🚀 Prepayment Strategies", expanded=False):
        st.markdown("**1. Regular Prepayments**")
        extra_payment = st.number_input("Extra per Payment", min_value=0.0, value=float(extra_payment_default), step=1000.0)
        recurring_lump = st.number_input("Annual Bonus Lump Sum", min_value=0.0, value=float(recurring_lump_default), step=10000.0)
        recurring_month = st.selectbox(
            "Month for Annual Bonus",
            range(1, 13),
            index=max(0, min(11, int(recurring_month_default) - 1)),
            format_func=lambda x: datetime(2000, x, 1).strftime('%B'),
        )

    with st.expander("📈 Floating Rate / Trends", expanded=False):
        rate_trend_active = st.checkbox("Enable Interest Rate Changes", value=rate_trend_active_default)
        rate_action = st.radio(
            "When Rates Change, the Bank will:",
            ["Keep EMI Same (Adjust Tenure)", "Recalculate EMI (Loan Recasting)"],
            index=0 if rate_action_default.startswith("Keep") else 1,
            help="Indian banks often keep EMI same and extend tenure when rates rise.",
        )

        rate_mode = st.radio(
            "Rate Change Mode",
            ["Predictable Trend", "Custom Schedule (RBI Style)"],
            index=0 if rate_mode_default.startswith("Predictable") else 1,
        )

        if rate_mode == "Predictable Trend":
            trend_amount = st.number_input("Increase rate by (%)", value=float(trend_amount_default), step=0.05)
            trend_months = st.number_input("Every X months", min_value=1, value=int(trend_months_default))
        else:
            trend_amount = 0.0
            trend_months = 1

# Handle Reset immediately
if reset_submit:
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.query_params.clear()
    st.rerun()

submitted = calc_submit

# -------------------------------------------------
# Editors (outside form). They can rerun, but will not recompute engine unless submitted.
# -------------------------------------------------

with st.sidebar.expander("🚀 Prepayment Strategies", expanded=False):
    st.markdown("---")
    st.markdown("**2. Irregular / Random Lump Sums**")

    if custom_lump_tuple_default:
        default_lumps = pd.DataFrame([{"Payment Date": d.date(), "Amount": float(a)} for d, a in custom_lump_tuple_default])
    else:
        default_lumps = pd.DataFrame([{"Payment Date": date.today(), "Amount": 0.0}])

    edited_lumps = st.data_editor(
        default_lumps,
        num_rows="dynamic",
        hide_index=True,
        key="custom_lump_editor",
        column_config={
            "Payment Date": st.column_config.DateColumn("Date", required=True),
            "Amount": st.column_config.NumberColumn("Amount", min_value=0.0, step=10000.0, required=True),
        },
    )

with st.sidebar.expander("📈 Floating Rate / Trends", expanded=False):
    if rate_mode == "Custom Schedule (RBI Style)":
        st.markdown(
            "<small>Enter effective dates and the <b>New Total Rate</b>. "
            "The new rate applies from the first payment date that is <b>on/after</b> the effective date.</small>",
            unsafe_allow_html=True,
        )

        if custom_rates_dict_default:
            default_schedule = pd.DataFrame(
                [{"Effective Date": pd.to_datetime(d).date(), "New Rate (%)": float(r)} for d, r in sorted(custom_rates_dict_default.items())]
            )
        else:
            default_schedule = pd.DataFrame(
                [
                    {"Effective Date": pd.to_datetime(start_date) + pd.DateOffset(months=14), "New Rate (%)": float(annual_rate) + 0.25},
                    {"Effective Date": pd.to_datetime(start_date) + pd.DateOffset(months=36), "New Rate (%)": float(annual_rate)},
                ]
            )

        edited_rates = st.data_editor(
            default_schedule,
            num_rows="dynamic",
            hide_index=True,
            key="custom_rate_editor",
            column_config={
                "Effective Date": st.column_config.DateColumn("Effective Date", required=True),
                "New Rate (%)": st.column_config.NumberColumn("New Rate (%)", min_value=0.10, max_value=25.00, step=0.05, required=True),
            },
        )
    else:
        edited_rates = pd.DataFrame(columns=["Effective Date", "New Rate (%)"])

# Build advanced inputs from editors
custom_lump_sums = []
if edited_lumps is not None and not edited_lumps.empty:
    for _, row in edited_lumps.iterrows():
        if pd.notna(row.get("Payment Date")) and pd.notna(row.get("Amount")) and float(row.get("Amount", 0)) > 0:
            custom_lump_sums.append((pd.to_datetime(row["Payment Date"]).normalize(), float(row["Amount"])))
custom_lump_tuple = tuple(custom_lump_sums)

custom_rates_dict = {}
if edited_rates is not None and not edited_rates.empty:
    start_dt_norm = pd.to_datetime(start_date).normalize()
    for _, row in edited_rates.iterrows():
        if pd.notna(row.get("Effective Date")) and pd.notna(row.get("New Rate (%)")):
            try:
                eff_dt = pd.to_datetime(row["Effective Date"]).normalize()
                if eff_dt < start_dt_norm:
                    continue
                custom_rates_dict[eff_dt.date().isoformat()] = float(row["New Rate (%)"])
            except Exception:
                pass

custom_rates_tuple = tuple(sorted(custom_rates_dict.items(), key=lambda x: x[0]))


def update_url_params():
    params = {
        "p": principal,
        "r": round(float(annual_rate), 4),
        "y": int(years),
        "sd": pd.to_datetime(start_date).date().isoformat(),
        "fmt": "I" if fmt_system.startswith("Indian") else "W",
        "at": round(float(annual_tax), 2),
        "ai": round(float(annual_ins), 2),
        "f": enc_freq(payment_freq),
        "c": enc_comp(compounding),
        "ep": round(float(extra_payment), 2) if extra_payment > 0 else None,
        "ab": f"{round(float(recurring_lump),2)}@{int(recurring_month)}" if recurring_lump > 0 else None,
        "ls": encode_lumps(custom_lump_tuple) if len(custom_lump_tuple) else None,
        "rt": "1" if rate_trend_active else None,
        "ra": enc_rate_action(rate_action) if rate_trend_active else None,
        "rm": enc_rate_mode(rate_mode) if rate_trend_active else None,
        "ta": round(float(trend_amount), 4) if (rate_trend_active and rate_mode == "Predictable Trend") else None,
        "tm": int(trend_months) if (rate_trend_active and rate_mode == "Predictable Trend") else None,
        "rs": encode_rate_schedule(custom_rates_dict) if (rate_trend_active and rate_mode == "Custom Schedule (RBI Style)" and custom_rates_dict) else None,
    }
    st.query_params.update(_drop_none(params))

with st.sidebar.expander("🔗 Shareable Link", expanded=False):
    st.caption("Press **Calculate** to refresh the link with the latest scenario.")
    components.html(
        """
        <div style='display:flex; gap:8px; align-items:center;'>
          <input id='sharelink' style='flex:1; padding:8px; border:1px solid #ddd; border-radius:8px;' readonly />
          <button id='copybtn' style='padding:8px 12px; border-radius:10px; border:1px solid #888; background:#f7f7f7; cursor:pointer;'>Copy</button>
        </div>
        <div id='copystatus' style='margin-top:6px; font-size:12px; color:#2e7d32;'></div>
        <script>
          const link = window.location.origin + window.location.pathname + window.location.search;
          document.getElementById('sharelink').value = link;
          document.getElementById('copybtn').addEventListener('click', async () => {
            try {
              await navigator.clipboard.writeText(link);
              document.getElementById('copystatus').innerText = 'Copied!';
              setTimeout(()=>document.getElementById('copystatus').innerText='', 1500);
            } catch (e) {
              document.getElementById('copystatus').innerText = 'Copy failed — please copy manually.';
            }
          });
        </script>
        """,
        height=90,
    )


# -------------------------------------------------
# CORE MATH ENGINE
# -------------------------------------------------
@st.cache_data(show_spinner=False, ttl="1h", max_entries=20)
def run_amortization(
    p,
    r_annual,
    yrs,
    start_dt,
    freq,
    comp,
    ext_pay,
    rec_lump,
    rec_mo,
    irregular_lumps,
    trnd_act,
    rate_mode_sel,
    rate_action_sel,
    trnd_amt,
    trnd_mo,
    custom_rates,
    annual_tax,
    annual_ins,
):
    data = []
    balance = float(p)
    current_date = pd.to_datetime(start_dt)

    periods_per_year = 26 if freq == "Accelerated Bi-Weekly" else 12
    total_periods = yrs * periods_per_year
    failsafe_cap = total_periods * 3

    # custom_rates may be tuple of (effective_date_iso, rate)
    if not isinstance(custom_rates, dict):
        custom_rates = dict(custom_rates)

    # sorted effective schedule for smooth application (Option A)
    custom_rate_schedule = []
    for d, rr in custom_rates.items():
        try:
            custom_rate_schedule.append((pd.to_datetime(d).normalize(), float(rr)))
        except Exception:
            pass
    custom_rate_schedule.sort(key=lambda x: x[0])
    next_rate_idx = 0

    def get_period_rate(annual_pct):
        r = annual_pct / 100
        if comp == "Monthly":
            return r / 12 if periods_per_year == 12 else ((1 + r / 12) ** (12 / 26) - 1)
        elif comp == "Daily":
            return (1 + r / 365) ** (365 / periods_per_year) - 1
        elif comp == "Semi-Annual (Canadian)":
            return (1 + r / 2) ** (2 / periods_per_year) - 1
        return r / periods_per_year

    def get_emi(princ, rate_per_period, periods_left):
        if rate_per_period <= 0:
            return princ / periods_left if periods_left > 0 else 0
        return princ * (rate_per_period * (1 + rate_per_period) ** periods_left) / ((1 + rate_per_period) ** periods_left - 1)

    base_monthly_emi = get_emi(p, get_period_rate(r_annual) if comp != "Monthly" else (r_annual / 100 / 12), yrs * 12)
    base_payment = base_monthly_emi if periods_per_year == 12 else base_monthly_emi / 2

    current_rate = r_annual
    last_rec_year = current_date.year - 1
    neg_amortization_flag = False
    infinite_loan_flag = False

    applied_lump_indices = set()

    period_tax = annual_tax / periods_per_year
    period_ins = annual_ins / periods_per_year

    trend_period_interval = int(round(trnd_mo * (26 / 12))) if periods_per_year == 26 else int(trnd_mo)

    for period in range(1, failsafe_cap):
        if freq == "Monthly":
            current_date += pd.DateOffset(months=1)
        else:
            current_date += pd.Timedelta(days=14)

        rate_changed = False

        if trnd_act:
            if rate_mode_sel == "Predictable Trend":
                if period > 1 and (period - 1) % max(1, trend_period_interval) == 0:
                    current_rate += trnd_amt
                    rate_changed = True
            elif rate_mode_sel == "Custom Schedule (RBI Style)":
                while next_rate_idx < len(custom_rate_schedule) and custom_rate_schedule[next_rate_idx][0] <= current_date:
                    _, new_r = custom_rate_schedule[next_rate_idx]
                    current_rate = new_r
                    next_rate_idx += 1
                    rate_changed = True

        if rate_changed and rate_action_sel == "Recalculate EMI (Loan Recasting)":
            rem_periods = total_periods - period + 1
            if rem_periods > 0 and balance > 0:
                base_payment = get_emi(balance, get_period_rate(current_rate), rem_periods)

        period_r = get_period_rate(current_rate)
        interest = balance * period_r
        principal_pay = base_payment - interest
        actual_principal = principal_pay + ext_pay

        if rec_lump > 0 and current_date.month == rec_mo and current_date.year > last_rec_year:
            actual_principal += rec_lump
            last_rec_year = current_date.year

        # Apply irregular lumps once
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

        data.append(
            {
                "Period": period,
                "Date": current_date.date(),
                "Rate (%)": round(current_rate, 4),
                "Payment Outflow": interest + actual_principal + period_tax + period_ins,
                "Interest": interest,
                "Principal": actual_principal,
                "Taxes & Ins": period_tax + period_ins,
                "Remaining Balance": balance,
            }
        )

        if balance <= 0:
            break

        if period == failsafe_cap - 1 and balance > 0:
            infinite_loan_flag = True

    return pd.DataFrame(data), neg_amortization_flag, infinite_loan_flag


# -------------------------------------------------
# EXECUTION CONTROL
# -------------------------------------------------
if "results" not in st.session_state:
    st.session_state["results"] = None

if submitted:
    update_url_params()

    df_base, _, _ = run_amortization(
        principal,
        annual_rate,
        years,
        start_date,
        "Monthly",
        "Monthly",
        0,
        0,
        1,
        tuple(),
        False,
        "Predictable Trend",
        "Keep EMI Same (Adjust Tenure)",
        0,
        1,
        tuple(),
        annual_tax,
        annual_ins,
    )

    df_actual, has_neg_amortization, is_infinite = run_amortization(
        principal,
        annual_rate,
        years,
        start_date,
        payment_freq,
        compounding,
        extra_payment,
        recurring_lump,
        recurring_month,
        custom_lump_tuple,
        rate_trend_active,
        rate_mode,
        rate_action,
        float(trend_amount),
        int(trend_months),
        custom_rates_tuple,
        annual_tax,
        annual_ins,
    )

    st.session_state["results"] = {
        "df_base": df_base,
        "df_actual": df_actual.copy(),
        "has_neg": has_neg_amortization,
        "is_inf": is_infinite,
    }

if st.session_state["results"] is None:
    st.title("🏦 Pro Loan Architect")
    st.info("Set your parameters in the sidebar, then press **Calculate**.")
    st.stop()

res = st.session_state["results"]
df_base = res["df_base"]
df_actual = res["df_actual"]
has_neg_amortization = res["has_neg"]
is_infinite = res["is_inf"]


# -------------------------------------------------
# METRICS & ALERTS
# -------------------------------------------------
st.title("🏦 Pro Loan Architect")

if has_neg_amortization:
    st.error("⚠️ **CRITICAL WARNING: Negative Amortization Detected!** Your payments no longer cover interest; balance may grow.")
if is_infinite:
    st.error("🚨 **INFINITE LOAN DETECTED:** This scenario may never pay off. Calculation was capped.")

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
    st.success(f"🔥 **Cross-Over Milestone:** In **{cross_over_date}**, you start paying more to Principal than Interest!")

st.markdown("---")

# --- UI CHARTS ---
tab1, tab2 = st.tabs(["📊 Visual Analytics", "📑 Detailed Schedule"])

with tab1:
    fig_bal = go.Figure()
    fig_bal.add_trace(go.Scatter(x=df_base["Date"], y=df_base["Remaining Balance"], name="Standard Balance", line=dict(color='gray', dash='dash')))
    fig_bal.add_trace(go.Scatter(x=df_actual["Date"], y=df_actual["Remaining Balance"], fill='tozeroy', name="Optimised Balance", line=dict(color='royalblue' if not has_neg_amortization else 'crimson')))
    fig_bal.update_layout(title="Loan Paydown Trajectory", xaxis_title="Timeline", yaxis_title="Balance", hovermode="x unified", height=450)
    st.plotly_chart(fig_bal, use_container_width=True)

    col_l, col_r = st.columns(2)
    with col_l:
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Scatter(x=df_actual["Date"], y=df_actual["Interest"], name="Interest", line=dict(color='tomato')))
        fig_comp.add_trace(go.Scatter(x=df_actual["Date"], y=df_actual["Principal"], name="Principal", line=dict(color='mediumseagreen')))
        fig_comp.update_layout(title="Principal vs Interest", xaxis_title="Timeline", yaxis_title="Amount per Period", hovermode="x unified", height=400)
        st.plotly_chart(fig_comp, use_container_width=True)

    with col_r:
        df_cash = df_actual.assign(Cum_Outflow=df_actual["Payment Outflow"].cumsum())
        fig_cash = go.Figure()
        fig_cash.add_trace(go.Scatter(x=df_cash["Date"], y=df_cash["Cum_Outflow"], fill='tozeroy', name="Total Cash Outflow", line=dict(color='orange')))
        fig_cash.update_layout(title="Total Cash Outflow (PITI)", xaxis_title="Timeline", yaxis_title="Cumulative Outflow", hovermode="x unified", height=400)
        st.plotly_chart(fig_cash, use_container_width=True)

    fig_rate = go.Figure()
    fig_rate.add_trace(go.Scatter(x=df_actual["Date"], y=df_actual["Rate (%)"], name="Rate (%)", line=dict(color='purple')))
    fig_rate.update_layout(title="Interest Rate Timeline", xaxis_title="Timeline", yaxis_title="Rate (%)", hovermode="x unified", height=320)
    st.plotly_chart(fig_rate, use_container_width=True)

with tab2:
    st.subheader("Amortisation Ledger")
    display_df = df_actual.copy()
    display_cols = ["Payment Outflow", "Interest", "Principal", "Taxes & Ins", "Remaining Balance"]
    for col in display_cols:
        display_df[col] = display_df[col].apply(lambda x: format_num(x, fmt_system))

    st.dataframe(display_df, use_container_width=True, height=500)
    st.download_button(
        "📥 Download Ledger (CSV)",
        data=df_actual.to_csv(index=False).encode('utf-8'),
        file_name="pro_amortization.csv",
        mime="text/csv",
    )
