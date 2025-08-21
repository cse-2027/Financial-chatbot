import re
import datetime
import streamlit as st
import matplotlib.pyplot as plt

# --- Page Config ---
st.set_page_config(page_title="Financial Chatbot", layout="centered")
st.title("🤖 Financial Chatbot with Memory")

# --- Session State for chat history & past months ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "history" not in st.session_state:
    st.session_state.history = {}  # stores month -> (income, expenses, savings)

# ---- Helpers ----
def fmt(n: float) -> str:
    """Format rupees with thousands separators."""
    try:
        return f"₹{float(n):,.0f}"
    except Exception:
        return f"₹{n}"

def parse_amount(raw: str) -> int:
    """
    Parse amounts like '50,000', '₹15,000', ' 3000 ', '50k', '1.5k'.
    (Keeps it simple; supports commas, ₹, optional k/K.)
    """
    s = raw.strip().lower()
    s = s.replace("₹", "").replace(",", "").replace("rs.", "").replace("rs", "")
    mult = 1
    if s.endswith("k"):
        mult = 1000
        s = s[:-1]
    # Keep digits and optional dot
    m = re.search(r"(\d+(\.\d+)?)", s)
    if not m:
        return 0
    val = float(m.group(1)) * mult
    return int(round(val))

# Map common aliases/typos to our canonical keys
ALIASES = {
    "income": "income", "salary": "income", "pay": "income", "wage": "income", "wages": "income",
    "food": "food", "dining": "food", "groceries": "food", "eatout": "food",
    "rent": "rent", "house": "rent", "housing": "rent", "home": "rent",
    "transport": "transport", "transportation": "transport", "travel": "transport", "commute": "transport", "fuel": "transport",
    "entertainment": "entertainment", "fun": "entertainment", "leisure": "entertainment", "movies": "entertainment",
    "shopping": "shopping", "clothes": "shopping", "apparel": "shopping",
    "others": "others", "other": "others", "misc": "others", "miscellaneous": "others",

    # Things we will ignore (computed or not needed)
    "saving": "_ignore", "savings": "_ignore", "save": "_ignore"
}

VALID_KEYS = ["income", "food", "rent", "transport", "entertainment", "shopping", "others"]

def parse_kv_input(text: str):
    """
    Robustly parse "key=value" pairs anywhere in the text.
    Handles commas inside numbers and ₹.
    """
    # Find key=value where value can include digits, commas, ₹, dots, k/K
    pairs = re.findall(r"([a-zA-Z_]+)\s*=\s*([₹\s]*[\d,\.]+k?)", text)
    data = {k: 0 for k in VALID_KEYS}
    recognized = []

    for raw_key, raw_val in pairs:
        key = raw_key.strip().lower()
        key = ALIASES.get(key, key)  # map alias -> canonical or keep as-is
        if key in VALID_KEYS:
            amt = parse_amount(raw_val)
            data[key] = amt
            recognized.append((key, amt))
        # ignore unknown keys (including savings)

    return data, recognized

# --- User Input ---
user_input = st.chat_input(
    "Enter your finances (e.g., income=50,000, food=18,000, rent=15000, entertainment=15,000)..."
)

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    data, recognized = parse_kv_input(user_input)

    if data["income"] <= 0 and not recognized:
        st.session_state.messages.append({
            "role": "bot",
            "content": "⚠ Please use format like: `income=50000, food=9000, rent=15000`.\n"
                       "Accepted keys: income, food, rent, transport, entertainment, shopping, others."
        })
    else:
        # --- Calculate summary ---
        expenses = sum([data["food"], data["rent"], data["transport"],
                        data["entertainment"], data["shopping"], data["others"]])
        savings = data["income"] - expenses

        # --- Save history (overwrites for the same month) ---
        month = datetime.datetime.now().strftime("%B %Y")
        st.session_state.history[month] = {
            "income": data["income"],
            "expenses": expenses,
            "savings": savings
        }

        # --- Budget Summary ---
        bot_reply = f"""
📊 *Budget Summary ({month})*  
- Income: {fmt(data['income'])}  
- Expenses: {fmt(expenses)}  
- Savings: {fmt(savings)}  

💡 *Insights:*  
"""
        if data["income"] > 0 and data["food"] > 0.2 * data["income"]:
            bot_reply += "🍔 Food expenses are high (>20% of income). Try cooking at home more often.\n"
        if data["income"] > 0 and data["entertainment"] > 0.1 * data["income"]:
            bot_reply += "🎬 Entertainment >10% of income. Consider trimming OTT/subscriptions.\n"
        if data["income"] > 0 and savings < 0.2 * data["income"]:
            bot_reply += "⚠ Savings below 20% of income. Try reducing discretionary spends.\n"
        else:
            bot_reply += "✅ Great job! You’re saving a healthy portion of your income.\n"

        # --- Compare with Previous Month ---
        if len(st.session_state.history) > 1:
            months = list(st.session_state.history.keys())
            prev_month = months[-2]
            prev = st.session_state.history[prev_month]
            exp_diff = expenses - prev["expenses"]
            save_diff = savings - prev["savings"]
            bot_reply += f"\n📈 *Comparison with {prev_month}:*\n"
            bot_reply += f"- Expenses: {'↑' if exp_diff > 0 else '↓'} {fmt(abs(exp_diff))}\n"
            bot_reply += f"- Savings: {'↑' if save_diff > 0 else '↓'} {fmt(abs(save_diff))}\n"

        # Show what we actually recognized (helps users fix input typos)
        if recognized:
            seen = ", ".join([f"{k}={fmt(v)}" for k, v in recognized])
            bot_reply += f"\n📝 *Parsed:* {seen}"

        st.session_state.messages.append({"role": "bot", "content": bot_reply})

        # --- Create Pie Chart (safe) ---
        categories = ["Food", "Rent", "Transport", "Entertainment", "Shopping", "Others"]
        values = [data["food"], data["rent"], data["transport"],
                  data["entertainment"], data["shopping"], data["others"]]

        if sum(values) > 0:
            fig, ax = plt.subplots()
            ax.pie(values, labels=categories, autopct="%1.1f%%", startangle=90)
            ax.axis("equal")
            st.session_state.messages.append({"role": "bot_chart", "content": fig})
        else:
            st.session_state.messages.append({
                "role": "bot",
                "content": "📊 No non-zero expenses provided, so the chart was skipped."
            })

# --- Display Conversation ---
for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.write(msg["content"])
    elif msg["role"] == "bot":
        with st.chat_message("assistant"):
            st.markdown(msg["content"])
    elif msg["role"] == "bot_chart":
        with st.chat_message("assistant"):
            st.pyplot(msg["content"])
