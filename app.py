import streamlit as st
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import datetime
import os

# -----------------------------
# 1️⃣ Streamlit page config
# -----------------------------
st.set_page_config(page_title="💬 Financial Chatbot", layout="wide")
st.title("💬 Personal Financial Chatbot")

# -----------------------------
# 2️⃣ User input
# -----------------------------
user_input = st.text_input("Ask a financial question:")
send_button = st.button("Send")

# -----------------------------
# 3️⃣ Device and Model config
# -----------------------------
device = "cuda" if torch.cuda.is_available() else "cpu"
model_path = "ibm-granite/granite-3.3-2b-instruct"

# Load Hugging Face token from Streamlit secrets
HF_TOKEN = os.getenv("HF_TOKEN")

# Load tokenizer and model
tokenizer = AutoTokenizer.from_pretrained(model_path, use_auth_token=HF_TOKEN)
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    use_auth_token=HF_TOKEN,
    torch_dtype=torch.bfloat16 if device=="cuda" else torch.float32,
    device_map="auto" if device=="cuda" else None,
    low_cpu_mem_usage=True
)
model.to(device)
model.eval()

# -----------------------------
# 4️⃣ Query function
# -----------------------------
def query_local_granite(input_text):
    try:
        input_ids = tokenizer(input_text, return_tensors="pt").to(device)
        set_seed(42)
        output = model.generate(**input_ids, max_new_tokens=2048)
        prediction = tokenizer.batch_decode(output, skip_special_tokens=True)[0]
        return prediction
    except Exception as e:
        return f"Model error: {str(e)}"

# -----------------------------
# 5️⃣ Handle user query
# -----------------------------
if send_button and user_input:
    answer = query_local_granite(user_input)
    st.text_area("Chatbot Response", answer, height=300)

    # -----------------------------
    # 6️⃣ Export chat to PDF
    # -----------------------------
    if st.button("Export Chat to PDF"):
        filename = f"Chat_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        doc = SimpleDocTemplate(filename)
        styles = getSampleStyleSheet()
        elements = [Paragraph(f"User: {user_input}", styles['Normal'])]
        elements.append(Paragraph(f"Bot: {answer}", styles['Normal']))
        doc.build(elements)
        st.success(f"Chat exported to {filename}")
