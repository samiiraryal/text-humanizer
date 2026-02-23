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
    </style>
    """, unsafe_allow_html=True)

# --- Sidebar: API Key & Settings ---
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Groq API Key", type="password", help="Get one free at console.groq.com")
    st.markdown("---")
    tone = st.selectbox("Target Tone", ["Natural & Casual", "Professional & Polished", "Creative & Expressive", "Academic & Formal"])
    creativity = st.slider("Creativity Level", 0.0, 1.0, 0.7)
    
    st.markdown("---")
    st.info("💡 **Privacy Note:** Text is sent to Groq API. Do not upload sensitive personal data.")
    st.markdown("### History (Local)")
    if 'history' not in st.session_state:
        st.session_state.history = []
    for item in st.session_state.history[-5:]:
        st.markdown(f"- {item[:30]}...")

# --- Helper Functions ---
def get_cache_key(text, tone):
    """Generate a unique ID for caching to save API calls."""
    return hashlib.md5(f"{text}{tone}".encode()).hexdigest()

def humanize_text(text, tone, creativity, client):
    """Send text to Groq for rewriting."""
    
    # System Prompts based on Tone
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
            model="llama3-70b-8192", # High quality free model on Groq
            temperature=creativity,
            max_tokens=2048,
            top_p=1.0,
            stream=False
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

# --- Main App UI ---
st.title("✍️ Authentica: AI Text Humanizer")
st.markdown("Transform robotic AI text into natural, human-like writing instantly.")

# Disclaimer
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
            # Initialize Client
            client = Groq(api_key=api_key)
            
            with st.spinner("Rewriting with human nuance..."):
                # Check Cache (Session State)
                cache_key = get_cache_key(input_text, tone)
                if 'cache' not in st.session_state:
                    st.session_state.cache = {}
                
                if cache_key in st.session_state.cache:
                    result = st.session_state.cache[cache_key]
                    time.sleep(0.5) # Fake delay for UX
                else:
                    result = humanize_text(input_text, tone, creativity, client)
                    st.session_state.cache[cache_key] = result # Save to cache
                
                if result.startswith("Error:"):
                    st.error(result)
                else:
                    output_placeholder.text_area("Result", value=result, height=300)
                    # Add to history
                    st.session_state.history.append(input_text[:50])
                    st.success("Done!")

# Footer
st.markdown("---")
st.markdown("Powered by Llama 3 70B via Groq Cloud | Hosted on Streamlit")