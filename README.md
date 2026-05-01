# 🏦 Pro Loan Architect: Advanced FinTech Amortization Engine

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?logo=streamlit&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-Data%20Analysis-150458?logo=pandas&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-Interactive%20Charts-3F4F75?logo=plotly&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg)

**Live Application:** [Launch Pro Loan Architect Here](https://home-loan-calculator-vfggbjajyxlsyrsypjjjbx.streamlit.app) *(Replace with your actual URL)*

---

## 📖 Executive Summary
Standard online loan calculators are fundamentally flawed—they assume perfect, static conditions. In reality, borrowers get annual bonuses, central banks change interest rates, and loan compounding methods vary globally. 

**Pro Loan Architect** is a production-grade FinTech tool designed to simulate real-world financial scenarios. It empowers prospective homeowners and current borrowers to model complex prepayment strategies, understand their true Total Cost of Ownership (PITI), and visually discover the exact moment they stop paying the bank and start paying themselves.

---

## ✨ Key Features & Business Value

### 1. 🚀 Advanced Prepayment Engine
Most tools allow a generic "extra monthly payment." This tool supports real-life cash flows:
- **Accelerated Bi-Weekly Payments:** Invisibly shave years off a mortgage by splitting monthly payments into 14-day cycles.
- **Annual Recurring Bonuses:** Simulate dropping corporate bonuses or tax refunds into the principal every year at a specific month.
- **One-Time Capital Injections:** Model the impact of inheritances or asset sales on a specific date.

### 2. 📈 Floating Rate Simulator (Stress Testing)
Interest rates fluctuate. Users can simulate macro-economic trends (e.g., *"What happens if the central bank raises rates by 0.25% every 12 months?"*) to stress-test their financial resilience.

### 3. ⏱️ Global Compounding Flexibility
Designed for international finance standards, supporting:
- **Monthly Compounding** (Standard US/Global)
- **Daily Accrual** (Modern Banking Standard)
- **Semi-Annual Compounding** (Canadian Mortgage Requirement)

### 4. 📊 Actionable Visual Analytics
- **The "Cross-Over" Milestone:** Dynamically calculates and celebrates the exact month a user's payment goes more toward their home principal than bank interest.
- **PITI Integration:** Tracks Principal, Interest, Taxes, and Insurance to show true monthly cash outflow.
- **Comparative Baseline Charts:** Visually compares the user's custom strategy against a standard, 30-year static loan.

### 5. 🔗 Frictionless UX & Virality
- **Shareable Scenarios:** Every UI adjustment updates the URL parameters. Users can craft the perfect prepayment strategy and send the exact URL to their spouse, financial advisor, or real estate agent.
- **Localized Number Formatting:** Seamlessly toggle between Western (Millions/Billions) and Indian (Lakhs/Crores) numbering systems.

---

## 🎯 Target Audience
*   **Prospective Homebuyers:** To budget true costs and understand how much home they can afford.
*   **Current Mortgage Holders:** To strategize how to pay off debt faster and save hundreds of thousands in interest.
*   **Real Estate Agents & Financial Advisors:** As a presentation tool to show clients how to structure their home financing.

---

## 💻 Technical Architecture & Local Setup

This application is built using **Python**, leveraging **Streamlit** for the frontend UI, **Pandas** for the amortization dataframe engine, and **Plotly** for responsive visualizations. Heavy math calculations are optimized using Streamlit's `@st.cache_data` to ensure low-latency rendering.

### Installation Instructions
1. Clone this repository:
   ```bash
   git clone https://github.com/prakhardamned/home-loan-calculator.git
   cd home-loan-calculator
