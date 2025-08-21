import re
import datetime
import streamlit as st
import matplotlib.pyplot as plt
from ibm_watson import AssistantV2
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from transformers import pipeline

# --------------------------
# IBM Watson Setup
# --------------------------
API_KEY = "YOUR_IBM_WATSON_API_KEY"
ASSISTANT_ID = "YOUR_ASSISTANT_ID"
URL = "YOUR_ASSISTANT_URL"

authenticator = IAMAuthenticator(API_KEY)
assistant = AssistantV2(
    version='2021-11-27',
    authenticator=authenticator
)
assistant.set_service_url(URL)

if "watson_session" not in st.session_state:
    session = assistant.create_session(assistant_id=ASSISTANT_ID).get_result()
    st.session_state.watson_session = session["session_id"]

# --------------------------
# Hugging Face Setup
# --------------------------
ner = pipeline("ner", model="dslim/bert-base-NER")

# --------------------------
# Helpers
# --------------------------
def fmt(n: float) -> str:
    return f"₹{float(n):,.0f}"

# --------------------------
# Streamlit App
# --------------------------
st.set_page_config(page_title="💰 AI Financial Chatbot", layout="centered")
st.title("🤖 Financial Chatbot ")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "history" not in st.session_state:
    st.session_state.history = {}

# --------------------------
# User Input
# --------------------------
user_input = st.chat_input("Type your finances (e.g. I earned 50000 and spent 15000 on rent)")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    # --- Step 1: Watson Assistant for intent ---
    watson_response = assistant.message(
        assistant_id=ASSISTANT_ID,
        session_id=st.session_state.watson_session,
        input={"message_type": "text", "text": user_input}
    ).get_result()

    watson_text = ""
    if watson_response.get("output", {}).get("generic"):
        for msg in watson_response["output"]["generic"]:
            if msg["response_type"] == "text":
                watson_text += msg["text"] + "\n"

    # --- Step 2: Hugging Face NER to extract money values ---
    entities = ner(user_input)
    amounts = [e for e in entities if "MONEY" in e["entity"]]

    # For demo, assume simple parsing
    income, expenses = 0, 0
    if "income" in user_input.lower() or "salary" in user_input.lower():
        # take first amount as income
        if amounts:
            income = int(float(re.sub(r"[^\d]", "", amounts[0]["word"])))
    if "rent" in user_input.lower() or "spent" in user_input.lower():
        if len(amounts) > 1:
            expenses = int(float(re.sub(r"[^\d]", "", amounts[1]["word"])))

    savings = income - expenses
    now = datetime.datetime.now().strftime("%B %Y")

    # --- Save history
    st.session_state.history[now] = {
        "income": income,
        "expenses": expenses,
        "savings": savings
    }

    # --- Build reply
    reply = watson_text
    reply += f"📊 *Budget Summary ({now}):*\n- Income: {fmt(income)}\n- Expenses: {fmt(expenses)}\n- Savings: {fmt(savings)}"

    st.session_state.messages.append({"role": "bot", "content": reply})

    # --- Chart
    if expenses > 0:
        fig, ax = plt.subplots()
        ax.pie([expenses, savings], labels=["Expenses", "Savings"], autopct="%1.1f%%", startangle=90)
        ax.axis("equal")
        st.session_state.messages.append({"role": "bot_chart", "content": fig})

# --------------------------
# Display Conversation
# --------------------------
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
