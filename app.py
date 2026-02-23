import streamlit as st
from groq import Groq
import time
import hashlib

# --- Page Config ---
st.set_page_config(page_title="Authentica Humanizer", page_icon="✍️", layout="wide")

# --- CSS Styling ---
st.markdown("""
    <style>
    .stTextArea label {font-weight: bold;}
    .success-box {padding: 10px; background-color: #d4edda; border-radius: 5px; color: #155724;}
    .warning-box {padding: 10px; background-color: #fff3cd; border-radius: 5px; color: #856404;}
    .error-box {padding: 10px; background-color: #f8d7da; border-radius: 5px; color: #721c24;}
    </style>
    """, unsafe_allow_html=True)

# --- Sidebar: Configuration ---
with st.sidebar:
    st.header("⚙️ Settings")
    
    # API Key
    api_key = st.text_input("Groq API Key", type="password", help="Get one free at console.groq.com")
    
    st.markdown("---")
    
    # MODEL SELECTOR (Crucial Fix)
    st.subheader("Model Selection")
    model_options = {
        "Llama 3.3 70B (Best Quality)": "llama-3.3-70b-versatile",
        "Llama 3.1 8B (Fastest)": "llama-3.1-8b-instant",
        "Mixtral 8x7B (Alternative)": "mixtral-8x7b-32768",
        "Gemma 2 9B (Alternative)": "gemma2-9b-it"
    }
    selected_model_name = st.selectbox("Choose Model", list(model_options.keys()))
    selected_model_id = model_options[selected_model_name]
    
    st.markdown("---")
    
    # Tone & Creativity
    tone = st.selectbox("Target Tone", ["Natural & Casual", "Professional & Polished", "Creative & Expressive", "Academic & Formal"])
    creativity = st.slider("Creativity Level", 0.0, 1.0, 0.7)
    
    st.markdown("---")
    st.info("💡 **Privacy Note:** Text is sent to Groq API. Do not upload sensitive personal data.")
    
    # History
    st.markdown("### History (Local)")
    if 'history' not in st.session_state:
        st.session_state.history = []
    for item in st.session_state.history[-5:]:
        st.markdown(f"- {item[:30]}...")

# --- Helper Functions ---
def get_cache_key(text, tone, model):
    """Generate a unique ID for caching to save API calls."""
    return hashlib.md5(f"{text}{tone}{model}".encode()).hexdigest()

def humanize_text(text, tone, creativity, client, model_id):
    """Send text to Groq for rewriting."""
    
    prompts = {
        "Natural & Casual": "Rewrite this text to sound like a friendly human conversation. Use contractions, varied sentence lengths, and occasional colloquialisms. Avoid robotic perfection.",
        "Professional & Polished": "Rewrite this text to sound like a seasoned professional. Clear, concise, active voice, but warm and engaging. Avoid overly stiff corporate jargon.",
        "Creative & Expressive": "Rewrite this text with flair. Use metaphors, vivid adjectives, and varied rhythm. Make it engaging and unique.",
        "Academic & Formal": "Rewrite this text for an academic audience. Precise vocabulary, complex sentence structures, objective tone, but ensure flow and readability."
    }
    
    system_instruction = prompts.get(tone, prompts["Natural & Casual"])
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": f"{system_instruction} \n\nIMPORTANT: Do not output any explanation, just the rewritten text."
                },
                {
                    "role": "user",
                    "content": f"Please humanize this text:\n\n{text}"
                }
            ],
            model=model_id,
            temperature=creativity,
            max_tokens=2048,
            top_p=1.0,
            stream=False
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        error_msg = str(e)
        if "decommissioned" in error_msg or "model" in error_msg:
            return f"Error: Model '{model_id}' might be deprecated. Please select a different model in the sidebar."
        return f"Error: {error_msg}"

# --- Main App UI ---
st.title("✍️ Authentica: AI Text Humanizer")
st.markdown("Transform robotic AI text into natural, human-like writing instantly.")

st.markdown("""
    <div class="warning-box">
        <strong>Ethical Use:</strong> This tool is designed to improve readability and style. 
        Do not use this to bypass academic integrity checks or misrepresent authorship.
    </div>
    """, unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Input Text")
    input_text = st.text_area("Paste AI-generated text here", height=300, placeholder="e.g., The utilization of this method is highly recommended...")

with col2:
    st.subheader("Humanized Output")
    output_placeholder = st.empty()
    
    if st.button("✨ Humanize Text", type="primary"):
        if not api_key:
            st.error("Please enter your Groq API Key in the sidebar.")
        elif not input_text:
            st.warning("Please enter some text to rewrite.")
        else:
            client = Groq(api_key=api_key)
            
            with st.spinner(f"Rewriting using {selected_model_name}..."):
                # Check Cache
                cache_key = get_cache_key(input_text, tone, selected_model_id)
                if 'cache' not in st.session_state:
                    st.session_state.cache = {}
                
                if cache_key in st.session_state.cache:
                    result = st.session_state.cache[cache_key]
                    time.sleep(0.5)
                else:
                    result = humanize_text(input_text, tone, creativity, client, selected_model_id)
                    st.session_state.cache[cache_key] = result
                
                if result.startswith("Error:"):
                    st.markdown(f'<div class="error-box">{result}</div>', unsafe_allow_html=True)
                    if "deprecated" in result:
                        st.warning("👈 Go to the sidebar and select a different model (e.g., Llama 3.1 8B).")
                else:
                    output_placeholder.text_area("Result", value=result, height=300)
                    st.session_state.history.append(input_text[:50])
                    st.success("Done!")

st.markdown("---")
st.markdown("Powered by Groq Cloud | Hosted on Streamlit")
