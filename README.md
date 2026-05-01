# 🏦 Pro Loan Architect: Advanced FinTech Amortization Engine

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?logo=streamlit&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-Data%20Analysis-150458?logo=pandas&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-Interactive%20Charts-3F4F75?logo=plotly&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg)

**Live Application:** [Launch Pro Loan Architect Here](https://home-loan-calculator-vfggbjajyxlsyrsypjjjbx.streamlit.app) *(Replace with your actual URL)*

---

## 📖 Executive Summary
Standard online loan calculators are fundamentally flawed—they assume perfect, static conditions. In reality, borrowers get unpredictable bonuses, central banks (like the RBI) change repo rates irregularly, and banks handle rate hikes differently depending on your loan agreement. 

**Pro Loan Architect** is a production-grade FinTech tool designed to simulate real-world financial chaos. It empowers homeowners to model complex, date-specific prepayment strategies, stress-test floating interest rates, and visually discover the exact moment they stop paying the bank and start paying themselves.

---

## ✨ Key Features & Business Value

### 1. 🚀 Dynamic Prepayment Ledger (Real-World Cash Flows)
Unlike standard tools that only allow one generic "extra payment," our engine features an interactive, spreadsheet-like ledger.
- **Irregular Lump Sums:** Enter infinite, custom-dated prepayments (e.g., selling an asset on a random Tuesday in 2028).
- **Accelerated Bi-Weekly:** Invisibly shave years off a mortgage by splitting monthly payments into 14-day cycles.
- **Annual Recurring Bonuses:** Automate corporate bonuses or tax refunds into the principal every year at a specific month.

### 2. 📈 RBI-Style Floating Rate Simulator (RLLR Support)
Interest rates don't just "trend"—they jump unpredictably based on Central Bank Repo Rates.
- **Custom Rate Schedules:** Use an interactive grid to map exact interest rates to specific future months.
- **Tenure vs. EMI Adjustment Logic:** Choose how your bank reacts to rate changes. Simulate Indian banking standards by **Keeping the EMI Constant** and stretching the tenure, or choose standard **Loan Recasting** to force a new EMI.

### 3. 🛡️ Advanced Financial Failsafes
Borrowing money carries risk. This application detects and alerts users to critical financial dangers:
- **Negative Amortization Alerts:** Warns users if their interest rate hikes cause their loan balance to *grow* rather than shrink.
- **Infinite Loan Detection:** Safely caps the calculation engine and alerts the user if their loan parameters result in a debt that will mathematically never be paid off.

### 4. ⏱️ Global Compounding Flexibility
Designed for international finance standards, natively supporting:
- **Daily Accrual** (Modern Banking Standard)
- **Monthly Compounding** (Standard US/Global)
- **Semi-Annual Compounding** (Canadian Mortgage Requirement)

### 5. 📊 Actionable Visual Analytics & Virality
- **The "Cross-Over" Milestone:** Dynamically calculates and celebrates the exact month a user's payment goes more toward their home principal than bank interest.
- **Localized Number Formatting:** Seamlessly toggles between Western (Millions/Billions) and Indian (Lakhs/Crores) numbering systems.
- **Shareable Scenarios:** Every UI adjustment dynamically updates the URL parameters (`?p=5000000&r=8.5`). Craft the perfect strategy and send the exact URL to your spouse, financial advisor, or real estate agent.

---

## 🎯 Target Audience
*   **Prospective Homebuyers:** To budget true costs (including PITI) and understand how much home they can actually afford.
*   **Current Mortgage Holders:** To strategize how to deploy irregular cash injections to save lakhs/millions in interest.
*   **Real Estate Agents & Financial Planners:** As an interactive presentation tool to visually prove the ROI of aggressive loan paydowns to clients.

---

## 💻 Technical Architecture & Local Setup

This application is built using **Python**, leveraging **Streamlit** for the frontend UI and interactive data grids (`st.data_editor`), **Pandas** for the chronologically-aware amortization engine, and **Plotly** for responsive visualizations. Heavy math loops are optimized using Streamlit's `@st.cache_data` to ensure low-latency rendering and prevent server timeouts.

### Installation Instructions
1. Clone this repository:
   ```bash
   git clone https://github.com/prakhardamned/home-loan-calculator.git
   cd home-loan-calculator
