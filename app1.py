
import streamlit as st
import json
import os
import requests
import pandas as pd
import altair as alt
from datetime import datetime, timedelta

# ---------------- THEME & CSS ----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
        color: #1a202c;
    }
    
    /* Global Background */
    .stApp {
        background: linear-gradient(to bottom right, #f8fafc, #edf2f7);
    }

    /* Cards */
    .feature-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        margin-bottom: 1rem;
        border-left: 5px solid #3b82f6;
    }
    
    .investment-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        margin-bottom: 0.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .action-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
        border-top: 4px solid #cbd5e1;
    }
    
    .action-stop { border-top-color: #ef4444; }
    .action-continue { border-top-color: #22c55e; }
    .action-increase { border-top-color: #3b82f6; }
    .action-start { border-top-color: #8b5cf6; }

    .doctor-note {
        background: linear-gradient(135deg, #fef9c3 0%, #fef3c7 100%);
        padding: 1rem 1.2rem;
        border-radius: 10px;
        border-left: 4px solid #f59e0b;
        margin-bottom: 0.5rem;
        font-size: 0.95rem;
        color: #78350f;
    }

    .goal-card {
        background: white;
        padding: 1.5rem;
        border-radius: 14px;
        box-shadow: 0 8px 20px -4px rgba(0, 0, 0, 0.1);
        margin-bottom: 1.5rem;
        border-left: 5px solid #6366f1;
    }

    .rec-item {
        background: #f8fafc;
        padding: 0.8rem 1rem;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        margin-bottom: 0.4rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* Headers */
    h1 { font-weight: 700; color: #0f172a; }
    h2 { font-weight: 600; color: #334155; font-size: 1.5rem; }
    h3 { font-weight: 600; color: #475569; font-size: 1.2rem; }

    /* Buttons */
    div.stButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
        padding: 0.6rem 2rem;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
        width: 100%;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        color: #0f172a;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- STATE MGMT ----------------
if "step" not in st.session_state:
    st.session_state.step = 1

# Initialize Data Store
if "data" not in st.session_state:
    st.session_state.data = {
        "personal": {},
        "goals": [],
        "equity_holdings": [],
        "risk": {}
    }

# Ensure keys exist
for key in ["personal", "risk"]:
    if key not in st.session_state.data:
        st.session_state.data[key] = {}
for key in ["goals", "equity_holdings"]:
    if key not in st.session_state.data:
        st.session_state.data[key] = []

# --- SAVING / LOADING ---
SAVE_FILE = "user_criteria.json"

with st.sidebar:
    st.header("Data Management")
    if st.button("Save Current Criteria"):
        try:
            with open(SAVE_FILE, "w") as f:
                json.dump(st.session_state.data, f, indent=4)
            st.success("Criteria Saved!")
        except Exception as e:
            st.error(f"Save failed: {e}")

    if st.button("Load Saved Criteria"):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, "r") as f:
                    loaded_data = json.load(f)
                st.session_state.data = loaded_data
                st.success("Criteria Loaded! Please check each step.")
                st.rerun()
            except Exception as e:
                st.error(f"Load failed: {e}")
        else:
            st.warning("No saved file found.")


# ==================== HELPERS ====================

def add_goal():
    name = st.session_state.get("_g_name")
    desc = st.session_state.get("_g_desc", "")
    target_amt = st.session_state.get("_g_target_amt")
    years = st.session_state.get("_g_years")
    if name and target_amt and years:
        target_date = (datetime.now() + timedelta(days=365 * years)).strftime("%Y-%m-%dT00:00:00Z")
        st.session_state.data["goals"].append({
            "goal_name": name,
            "description": desc,
            "target_date": target_date,
            "target_amount": float(target_amt)
        })

def remove_goal(idx):
    st.session_state.data["goals"].pop(idx)


def add_holding():
    broker = st.session_state.get("_h_broker", "")
    ticker = st.session_state.get("_h_ticker", "")
    name = st.session_state.get("_h_name", "")
    shares = st.session_state.get("_h_shares", 0)
    avg_price = st.session_state.get("_h_avg_price", 0.0)
    exchange = st.session_state.get("_h_exchange", "NSE")
    if ticker and shares and avg_price:
        asset = {
            "ticker": ticker,
            "name": name or ticker,
            "shares": int(shares),
            "average_price": float(avg_price),
            "exchange": exchange
        }
        # Group by broker
        holdings = st.session_state.data["equity_holdings"]
        found = False
        for h in holdings:
            if h["broker_name"].strip().lower() == broker.strip().lower():
                h["assets"].append(asset)
                found = True
                break
        if not found:
            holdings.append({
                "broker_name": broker or "Default",
                "assets": [asset]
            })

def remove_holding(broker_idx, asset_idx):
    holdings = st.session_state.data["equity_holdings"]
    holdings[broker_idx]["assets"].pop(asset_idx)
    if not holdings[broker_idx]["assets"]:
        holdings.pop(broker_idx)


def calculate_fv(pv, years, rate=0.06):
    return pv * ((1 + rate) ** years)


def build_payload():
    """
    Transform the session data into EXACTLY the actions.md input format.
    Output keys: financial_survey, risk_profile, goals, equity_holdings
    Nothing else.
    """
    p = st.session_state.data["personal"]
    r = st.session_state.data["risk"]

    # ---- financial_survey (sections → questions) ----
    financial_survey = [
        {
            "section_name": "Personal Information",
            "questions": [
                {"question_text": "What is your Age Group?", "answer": str(p.get("age_group", ""))},
                {"question_text": "Occupation", "answer": str(p.get("occupation", ""))}
            ]
        },
        {
            "section_name": "Income",
            "questions": [
                {"question_text": "Monthly Income", "answer": str(p.get("monthly_income", 0)), "input_type": "currency"},
                {"question_text": "Monthly Expenses", "answer": str(p.get("monthly_expenses", 0)), "input_type": "currency"}
            ]
        },
        {
            "section_name": "Assets",
            "questions": [
                {"question_text": "Bank Savings", "answer": str(p.get("total_assets", 0)), "input_type": "currency"},
                {"question_text": "Emergency Fund", "answer": str(p.get("emergency_fund", 0)), "input_type": "currency"}
            ]
        },
        {
            "section_name": "Liabilities",
            "questions": [
                {"question_text": "Total Loans", "answer": str(p.get("total_liabilities", 0)), "input_type": "currency"}
            ]
        },
        {
            "section_name": "Insurance",
            "questions": [
                {"question_text": "Do you have Term Insurance?", "answer": "Yes" if p.get("has_term") else "No"},
                {"question_text": "Do you have Health Insurance?", "answer": "Yes" if p.get("has_health") else "No"}
            ]
        }
    ]

    # ---- risk_profile (sections → questions) ----
    risk_profile = [
        {
            "section_name": "Investment Behaviour",
            "questions": [
                {"question_text": "How much experience do you have with investing?", "answer": str(r.get("experience", ""))},
                {"question_text": "If your portfolio drops 20%, you would", "answer": str(r.get("market_fall_reaction", ""))},
                {"question_text": "Preferable Return Path", "answer": str(r.get("risk_reward", ""))},
                {"question_text": "Primary Goal Horizon", "answer": str(r.get("horizon", ""))}
            ]
        }
    ]

    # ---- goals (already in spec shape) ----
    goals = st.session_state.data["goals"]

    # ---- equity_holdings (already grouped by broker) ----
    equity_holdings = st.session_state.data["equity_holdings"]

    # Return EXACTLY the 4 keys from actions.md — nothing else
    return {
        "financial_survey": financial_survey,
        "risk_profile": risk_profile,
        "goals": goals,
        "equity_holdings": equity_holdings
    }


# ---------------- HEADER ----------------
st.markdown("<h1 style='text-align: center;'>Portfolio Doctor</h1>", unsafe_allow_html=True)

# Progress
steps = ["Profile", "Dream Board", "Holdings Scan", "Risk DNA", "The Prescription"]
curr_step = st.session_state.step
st.progress(curr_step / len(steps))


# ================= STEP 1: PROFILE =================
if curr_step == 1:
    st.subheader("Step 1: Financial Vitals")
    
    p_data = st.session_state.data.get("personal", {})
    
    with st.container():
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Personal Details")
            
            def get_idx(options, val):
                try: return options.index(val)
                except: return 0
                
            age_opts = ["18–25","26–35","36–45","46–55","56+"]
            occupation_opts = ["Salaried","Self-employed","Business","Retired"]
            
            age_group = st.selectbox("Age Group", age_opts, index=get_idx(age_opts, p_data.get("age_group")))
            occupation = st.selectbox("Occupation", occupation_opts, index=get_idx(occupation_opts, p_data.get("occupation")))
            
            st.markdown("### Cash Flow")
            monthly_income = st.number_input("Monthly Income (INR)", 0, step=5000, help="Take-home salary", value=p_data.get("monthly_income", 0))
            monthly_expenses = st.number_input("Monthly Expenses (INR)", 0, step=2000, help="Needs + Wants", value=p_data.get("monthly_expenses", 0))
            
        with c2:
            st.markdown("### Safety Net")
            emergency_fund = st.number_input("Emergency Savings (INR)", 0, step=10000, value=p_data.get("emergency_fund", 0))
            has_term = st.toggle("I have Term Insurance", value=p_data.get("has_term", False))
            has_health = st.toggle("I have Health Insurance", value=p_data.get("has_health", False))
            
            st.markdown("### Assets & Debts")
            assets = st.number_input("Total Savings (FD/Gold/Bank) (INR)", 0, step=50000, value=p_data.get("total_assets", 0))
            loans = st.number_input("Total Loans (Home/Car/Personal) (INR)", 0, step=50000, value=p_data.get("total_liabilities", 0))

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Next: Build Your Dream Board"):
        st.session_state.data["personal"] = {
            "age_group": age_group, "occupation": occupation,
            "monthly_income": monthly_income, "monthly_expenses": monthly_expenses,
            "emergency_fund": emergency_fund, "total_assets": assets, "total_liabilities": loans,
            "has_term": has_term, "has_health": has_health
        }
        st.session_state.step = 2
        st.rerun()


# ================= STEP 2: GOALS =================
elif curr_step == 2:
    st.subheader("Step 2: Dream Board")
    
    col_input, col_view = st.columns([1, 1.2])
    
    with col_input:
        st.markdown('<div class="feature-card">', unsafe_allow_html=True)
        st.markdown("#### Add a Goal")
        st.text_input("Goal Name", placeholder="e.g. Buy a House, Harvard MBA", key="_g_name")
        st.text_input("Description", placeholder="e.g. Down payment for a 2BHK", key="_g_desc")
        c1, c2 = st.columns(2) 
        c1.number_input("Target Amount (INR)", min_value=0, step=50000, key="_g_target_amt")
        c2.number_input("Years Away", min_value=1, max_value=40, key="_g_years")
        st.button("Add to Board", on_click=add_goal)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_view:
        st.markdown("#### Your Goals")
        if not st.session_state.data["goals"]:
            st.info("No goals added yet. Start by adding one!")
        else:
            for i, g in enumerate(st.session_state.data["goals"]):
                target_amt = g.get("target_amount", 0)
                target_date_str = g.get("target_date", "")
                try:
                    target_dt = datetime.strptime(target_date_str, "%Y-%m-%dT00:00:00Z")
                    years_away = max(1, (target_dt - datetime.now()).days // 365)
                except:
                    years_away = 0
                
                st.markdown(f"""
                <div class="investment-card">
                    <div>
                        <strong>{g['goal_name']}</strong><br>
                        <span style="font-size:0.8em; color:#64748b">{g.get('description', '')}</span><br>
                        <span style="font-size:0.75em; color:#94a3b8">In ~{years_away} years</span>
                    </div>
                    <div style="text-align:right">
                        <div style="font-size:0.8em; color:#64748b">Target Amount</div>
                        <div style="font-weight:bold; color:#6366f1">₹{int(target_amt):,}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Remove Goal {i+1}", key=f"rm_g_{i}"):
                    remove_goal(i)
                    st.rerun()

    c1, c2 = st.columns(2)
    if c1.button("Back"):
        st.session_state.step = 1
        st.rerun()
    if c2.button("Next: Holdings Scan"):
        st.session_state.step = 3
        st.rerun()


# ================= STEP 3: EQUITY HOLDINGS =================
elif curr_step == 3:
    st.subheader("Step 3: Equity Holdings Scan")
    st.caption("Add your equity holdings grouped by broker.")
    
    col_input, col_view = st.columns([1, 1.2])
    
    with col_input:
        st.markdown('<div class="feature-card">', unsafe_allow_html=True)
        st.markdown("#### Add Equity Holding")
        st.text_input("Broker Name", placeholder="e.g. Zerodha, Upstox, Groww", key="_h_broker")
        st.text_input("Ticker Symbol", placeholder="e.g. RELIANCE, INFY", key="_h_ticker")
        st.text_input("Company Name", placeholder="e.g. Reliance Industries Ltd", key="_h_name")
        c1, c2 = st.columns(2)
        c1.number_input("Number of Shares", min_value=0, step=1, key="_h_shares")
        c2.number_input("Average Price (INR)", min_value=0.0, step=10.0, key="_h_avg_price")
        st.selectbox("Exchange", ["NSE", "BSE"], key="_h_exchange")
        st.button("Add Holding", on_click=add_holding)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_view:
        st.markdown("#### Current Holdings")
        holdings = st.session_state.data["equity_holdings"]
        if not holdings:
            st.warning("No equity holdings added. Click Next if you are starting fresh.")
        else:
            total_value = 0
            for bi, broker in enumerate(holdings):
                st.markdown(f"**🏦 {broker['broker_name']}**")
                for ai, asset in enumerate(broker["assets"]):
                    value = asset["shares"] * asset["average_price"]
                    total_value += value
                    st.markdown(f"""
                    <div class="investment-card">
                        <div>
                            <strong>{asset['ticker']}</strong> — {asset['name']}<br>
                            <span style="font-size:0.8em; color:#3b82f6">{asset['exchange']} · {asset['shares']} shares @ ₹{asset['average_price']:,.2f}</span>
                        </div>
                        <div style="text-align:right">
                            <div style="font-weight:bold">₹{value:,.0f}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"Remove {asset['ticker']}", key=f"rm_h_{bi}_{ai}"):
                        remove_holding(bi, ai)
                        st.rerun()
            st.markdown(f"**Total Equity Value:** ₹{total_value:,.0f}")

    col1, col2 = st.columns(2)
    if col1.button("Back"):
        st.session_state.step = 2
        st.rerun()
    if col2.button("Next: Risk DNA"):
        st.session_state.step = 4
        st.rerun()


# ================= STEP 4: RISK PROFILE =================
elif curr_step == 4:
    st.subheader("Step 4: Risk DNA")
    
    p_risk = st.session_state.data.get("risk", {})
    
    def get_idx(options, val):
        try: return options.index(val)
        except: return 0

    with st.container():
        st.markdown("##### Investment Experience")
        
        exp_opts = ["Beginner", "Intermediate", "Advanced", "Expert"]
        experience = st.radio(
            "How much experience do you have with investing?",
            options=exp_opts,
            horizontal=True,
            index=get_idx(exp_opts, p_risk.get("experience"))
        )
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown("##### Psychology")
        
        mf_opts = ["Sell All", "Sell Some", "Do Nothing", "Buy More"]
        market_fall = st.radio(
            "If your portfolio drops 20% in a month, you would:", 
            options=mf_opts,
            horizontal=True,
            index=get_idx(mf_opts, p_risk.get("market_fall_reaction"))
        )
        st.markdown("<br>", unsafe_allow_html=True)
        
        rr_opts = ["Stable 7% Returns", "Bumpy 10% Returns", "Volatile 15% Returns"]
        risk_pref = st.radio(
            "Preferable Return Path:",
            options=rr_opts,
            horizontal=True,
            index=get_idx(rr_opts, p_risk.get("risk_reward"))
        )
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown("##### Time & Capacity")
        h_opts = ["Short Term (<3y)", "Medium Term (3-7y)", "Long Term (7y+)"]
        horizon = st.selectbox("Primary Goal Horizon", h_opts, index=get_idx(h_opts, p_risk.get("horizon")))
        
    col1, col2 = st.columns(2)
    if col1.button("Back"):
        st.session_state.step = 3
        st.rerun()
    if col2.button("GENERATE PRESCRIPTION"):
        st.session_state.data["risk"] = {
            "experience": experience,
            "market_fall_reaction": market_fall,
            "risk_reward": risk_pref,
            "horizon": horizon
        }
        
        with st.spinner("Diagnosis in progress... Analyzing holdings... Projecting inflation..."):
            try:
                payload = build_payload()
                response = requests.post(
                    "https://n8n.decuple.work/webhook/portfolio-doctor",
                    json=payload,
                    timeout=90
                )
                if response.status_code == 200:
                    st.session_state.report = response.json()
                    st.session_state.step = 5
                    st.rerun()
                else:
                    st.error(f"Error {response.status_code}: {response.text}")
            except Exception as e:
                st.error(f"Connection Error: {e}")


# ================= STEP 5: REPORT (matches actions.md output) =================
elif curr_step == 5:
    report = st.session_state.report
    
    # --- Top Banner ---
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding:2rem; border-radius:15px; text-align:center; color:white; margin-bottom:2rem;">
        <h2 style="color:white; margin:0;">🩺 The Doctor's Prescription</h2>
        <p style="opacity:0.8">Personalized Wealth Surgery Report</p>
    </div>
    """, unsafe_allow_html=True)

    # --- Doctor's Notes ---
    doctor_notes = report.get("doctorNote", [])
    if doctor_notes:
        st.markdown("### 📋 Doctor's Notes")
        for note in doctor_notes:
            st.markdown(f'<div class="doctor-note">💡 {note}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # --- Goal-Wise Recommendations ---
    goal_recs = report.get("goalWiseRecommendations", [])
    if goal_recs:
        st.markdown("### 🎯 Goal-Wise Recommendations")
        
        for goal in goal_recs:
            goal_name = goal.get("goalName", "Unnamed Goal")
            current_alloc = goal.get("currentAllocation", 0)
            recommended_alloc = goal.get("recommendedAllocation", 0)
            additional_needed = goal.get("additionalInvestmentNeeded", 0)
            monthly_required = goal.get("monthlyInvestmentRequired", 0)
            
            st.markdown(f'<div class="goal-card">', unsafe_allow_html=True)
            st.markdown(f"#### 🏷️ {goal_name}")
            
            # KPI row
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Current Allocation", f"₹{current_alloc:,}")
            k2.metric("Recommended", f"₹{recommended_alloc:,}")
            k3.metric("Additional Needed", f"₹{additional_needed:,}")
            k4.metric("Monthly Required", f"₹{monthly_required:,}")

            # Recommended Portfolio for this goal
            rec_portfolio = goal.get("recommendedPortfolio", [])
            if rec_portfolio:
                st.markdown("##### Recommended Portfolio Adjustments")
                
                for item in rec_portfolio:
                    action = item.get("action", "")
                    action_upper = action.upper()
                    
                    # Determine color
                    if "STOP" in action_upper or "SELL" in action_upper or "REDUCE" in action_upper:
                        css_class = "action-stop"
                        icon = "🔴"
                    elif "CONTINUE" in action_upper or "HOLD" in action_upper or "MAINTAIN" in action_upper:
                        css_class = "action-continue"
                        icon = "🟢"
                    elif "INCREASE" in action_upper:
                        css_class = "action-increase"
                        icon = "🔵"
                    elif "START" in action_upper or "NEW" in action_upper or "ADD" in action_upper:
                        css_class = "action-start"
                        icon = "🟣"
                    else:
                        css_class = ""
                        icon = "⚪"
                    
                    current_amt = item.get("currentAmount", 0)
                    rec_add = item.get("recommendedAdditionalInvestment", 0)
                    rec_monthly = item.get("recommendedMonthlyContribution", 0)
                    asset_class = item.get("assetClass", "")
                    
                    st.markdown(f"""
                    <div class="action-card {css_class}">
                        <div style="display:flex; justify-content:space-between; margin-bottom:0.5rem;">
                            <span style="font-weight:700; font-size:1.1rem;">{icon} {item.get('name', '')}</span>
                            <span style="background:#f1f5f9; padding:0.2rem 0.6rem; border-radius:5px; font-size:0.8rem; font-weight:600;">{action}</span>
                        </div>
                        <div style="color:#64748b; font-size:0.85rem; margin-bottom:0.5rem;">Asset Class: {asset_class}</div>
                        <div style="margin-top:0.8rem; padding-top:0.8rem; border-top:1px dashed #e2e8f0; display:flex; justify-content:space-around; text-align:center;">
                            <div>
                                <div style="font-size:0.8rem; color:#94a3b8;">Current</div>
                                <div style="font-weight:700;">₹{current_amt:,}</div>
                            </div>
                            <div>
                                <div style="font-size:0.8rem; color:#94a3b8;">Add Investment</div>
                                <div style="font-weight:700; color:#3b82f6;">₹{rec_add:,}</div>
                            </div>
                            <div>
                                <div style="font-size:0.8rem; color:#94a3b8;">Monthly Contribution</div>
                                <div style="font-weight:700; color:#22c55e;">₹{rec_monthly:,}</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

        # --- Summary Chart: Allocation across all goals ---
        st.markdown("### 📊 Allocation Overview")
        chart_data = []
        for g in goal_recs:
            chart_data.append({
                "Goal": g.get("goalName", ""),
                "Current": g.get("currentAllocation", 0),
                "Recommended": g.get("recommendedAllocation", 0)
            })
        
        if chart_data:
            df = pd.DataFrame(chart_data)
            df_melted = df.melt(id_vars=["Goal"], var_name="Type", value_name="Amount")
            
            chart = alt.Chart(df_melted).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
                x=alt.X("Goal:N", title="Goals"),
                y=alt.Y("Amount:Q", title="Amount (₹)"),
                color=alt.Color("Type:N", scale=alt.Scale(
                    domain=["Current", "Recommended"],
                    range=["#94a3b8", "#6366f1"]
                )),
                xOffset="Type:N",
                tooltip=["Goal", "Type", alt.Tooltip("Amount:Q", format=",")]
            ).properties(height=350)
            
            st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No goal-wise recommendations received.")

    st.markdown("---")
    if st.button("Start New Consultation"):
        st.session_state.step = 1
        st.session_state.data = {"personal": {}, "goals": [], "equity_holdings": [], "risk": {}}
        st.rerun()
