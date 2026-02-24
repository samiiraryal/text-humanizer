"""
Authentica v6 — AI Humanizer
Changelog vs v5:
  • Added OpenRouter provider — access Qwen3-235B, Llama 4 Maverick, DeepSeek V3, Mistral Large 3 free
  • Working clipboard via JavaScript injection (no pyperclip, no server-side hack)
  • Removed contraction injection entirely from all post-processing
  • 20 content types, 5 groups — all with locked, document-aware system prompts
  • Structural 4-pass pipeline for general content (breaks AI paragraph patterns first)
  • Fixed preamble stripping ("Here is the rewritten version:" etc.)
  • Cleaned up all UI elements — consistent dark theme, better spacing, readable fonts
  • Detector targeting for GPTZero, Originality, Turnitin, ZeroGPT, Quillbot — at prompt level, not post-proc
"""

import streamlit as st
import streamlit.components.v1 as components
import hashlib, re, random, time

# ─────────────────────────────────────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Authentica v6", page_icon="✍️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fraunces:ital,wght@0,700;1,400&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
h1, h2, h3 { font-family: 'Fraunces', serif !important; }

/* App background */
.stApp { background: #0c0c10 !important; }
.main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1280px; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #111117 !important;
    border-right: 1px solid #1e1e2e !important;
}
section[data-testid="stSidebar"] * { color: #b0b0c0 !important; font-size: 13px !important; }
section[data-testid="stSidebar"] h3 { color: #e0e0f0 !important; font-size: 14px !important; font-family: 'Inter', sans-serif !important; font-weight: 600 !important; }
section[data-testid="stSidebar"] .stRadio > label { color: #888 !important; }
section[data-testid="stSidebar"] hr { border-color: #1e1e2e !important; }

/* Inputs */
div[data-testid="stTextArea"] textarea {
    background: #13131a !important;
    border: 1.5px solid #252535 !important;
    border-radius: 10px !important;
    color: #d8d8e8 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    line-height: 1.75 !important;
    resize: vertical !important;
}
div[data-testid="stTextArea"] textarea:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.12) !important;
    outline: none !important;
}
div[data-testid="stTextArea"] textarea::placeholder { color: #3a3a55 !important; }
div[data-testid="stTextArea"] label { color: #4a4a6a !important; font-size: 11px !important; }
div[data-testid="stTextInput"] input {
    background: #13131a !important;
    border: 1.5px solid #252535 !important;
    border-radius: 8px !important;
    color: #c0c0d8 !important;
    font-size: 13px !important;
}
div[data-testid="stSelectbox"] > div > div {
    background: #13131a !important;
    border: 1.5px solid #252535 !important;
    border-radius: 8px !important;
    color: #c0c0d8 !important;
}
.stSelectbox label { color: #5a5a7a !important; font-size: 11px !important; }
.stCheckbox label { color: #9090b0 !important; }
.stRadio label { color: #9090b0 !important; }

/* Primary button */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 12px 20px !important;
    letter-spacing: 0.02em !important;
    box-shadow: 0 4px 24px rgba(99,102,241,0.28) !important;
    transition: all 0.2s !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 32px rgba(99,102,241,0.42) !important;
    transform: translateY(-1px) !important;
}
/* Secondary button */
.stButton > button[kind="secondary"] {
    background: #1a1a28 !important;
    color: #9090c0 !important;
    border: 1px solid #2a2a40 !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 8px 16px !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #4f46e5 !important;
    color: #b0b0e0 !important;
}

/* Metric cards */
div[data-testid="stMetric"] {
    background: #13131a;
    border: 1px solid #1e1e2e;
    border-radius: 10px;
    padding: 12px 14px;
}
div[data-testid="stMetric"] label { color: #4a4a6a !important; font-size: 11px !important; }
div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #8080c8 !important; font-size: 20px !important; font-weight: 700 !important; }

/* Expander */
details summary { color: #7070a8 !important; font-size: 13px !important; }
details { border: 1px solid #1e1e2e !important; border-radius: 10px !important; background: #111117 !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #0c0c10; }
::-webkit-scrollbar-thumb { background: #252535; border-radius: 4px; }

/* Alert boxes */
div[data-testid="stAlert"] { border-radius: 8px !important; border-width: 1px !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  JAVASCRIPT CLIPBOARD HELPER
#  The only reliable cross-platform clipboard approach in Streamlit is
#  injecting JS through an iframe via st.components.v1.html
# ─────────────────────────────────────────────────────────────────────────────
def clipboard_button(text_to_copy: str, button_label: str = "📋 Copy to Clipboard", height: int = 52):
    """Injects a working JS copy-to-clipboard button via iframe."""
    # Safely encode the text for embedding in JS
    escaped = text_to_copy.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
    html = f"""
    <html>
    <head>
    <style>
      body {{ margin:0; padding:0; background:transparent; display:flex; align-items:center; }}
      button {{
        background: linear-gradient(135deg, #4f46e5, #7c3aed);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-family: 'Inter', -apple-system, sans-serif;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        width: 100%;
        letter-spacing: 0.03em;
        transition: opacity 0.15s;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
      }}
      button:hover {{ opacity: 0.88; }}
      button.done {{
        background: linear-gradient(135deg, #059669, #10b981);
      }}
    </style>
    </head>
    <body>
    <button id="cb" onclick="doCopy()">
      {button_label}
    </button>
    <script>
      const txt = `{escaped}`;
      function doCopy() {{
        if (navigator.clipboard && navigator.clipboard.writeText) {{
          navigator.clipboard.writeText(txt).then(function() {{
            const b = document.getElementById('cb');
            b.innerText = '✓ Copied!';
            b.className = 'done';
            setTimeout(() => {{ b.innerText = '{button_label}'; b.className = ''; }}, 2200);
          }}).catch(fallback);
        }} else {{ fallback(); }}
      }}
      function fallback() {{
        const ta = document.createElement('textarea');
        ta.value = txt;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.focus(); ta.select();
        try {{
          document.execCommand('copy');
          const b = document.getElementById('cb');
          b.innerText = '✓ Copied!';
          b.className = 'done';
          setTimeout(() => {{ b.innerText = '{button_label}'; b.className = ''; }}, 2200);
        }} catch(e) {{
          alert('Copy failed. Please use Ctrl+A → Ctrl+C on the text area above.');
        }}
        document.body.removeChild(ta);
      }}
    </script>
    </body>
    </html>
    """
    components.html(html, height=height)


# ─────────────────────────────────────────────────────────────────────────────
#  PROVIDER & MODEL DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

# OpenRouter free models — all accessible via one API key, OpenAI-compatible
OPENROUTER_MODELS = {
    "Qwen3-235B-A22B ✦ Best quality (free)":          "qwen/qwen3-235b-a22b:free",
    "Llama 4 Maverick ✦ Meta's flagship (free)":      "meta-llama/llama-4-maverick:free",
    "DeepSeek V3 ✦ Strong reasoning (free)":          "deepseek/deepseek-chat-v3-0324:free",
    "Mistral Large 3 ✦ EU-based, reliable (free)":    "mistral/mistral-large-3:free",
    "Llama 3.3 70B ✦ Fast & reliable (free)":         "meta-llama/llama-3.3-70b-instruct:free",
    "Qwen3-30B-A3B ✦ Lighter Qwen (free)":            "qwen/qwen3-30b-a3b:free",
}

# Groq models (fast inference, separate API key)
GROQ_MODELS = {
    "Llama 3.3 70B ✦ Fastest inference":   "llama-3.3-70b-versatile",
    "Llama 3.1 8B ✦ Quickest responses":   "llama-3.1-8b-instant",
    "Mixtral 8x7B ✦ Alternative":          "mixtral-8x7b-32768",
}

# Gemini models (Google AI Studio, free tier)
GEMINI_MODELS = {
    "Gemini 2.0 Flash ✦ Fast & capable":   "gemini-2.0-flash",
    "Gemini 1.5 Flash ✦ Lightweight":      "gemini-1.5-flash",
}

PROVIDER_LABELS = {
    "OpenRouter (Free models — recommended)": "openrouter",
    "Groq (Free — fastest inference)":        "groq",
    "Google Gemini (Free tier)":              "gemini",
}

PROVIDER_KEY_HINTS = {
    "openrouter": ("OpenRouter API Key", "sk-or-...", "openrouter.ai/keys — Free account"),
    "groq":       ("Groq API Key",       "gsk_...",   "console.groq.com — Free, no card"),
    "gemini":     ("Gemini API Key",     "AIza...",   "aistudio.google.com/apikey"),
}


# ─────────────────────────────────────────────────────────────────────────────
#  CONTENT TYPES — 20 types, 5 groups
# ─────────────────────────────────────────────────────────────────────────────

CONTENT_TYPES = {
    # ═══ ACADEMIC ═══════════════════════════════════════════════════════════
    "📄 Statement of Purpose (SOP)": {
        "group": "Academic",
        "pipeline": "formal",
        "tone_locked": "Reflective & Personal",
        "system": """You are an elite SOP editor. Rewrite this Statement of Purpose to sound like a real, thoughtful applicant wrote it after months of careful reflection — not an AI template.

ABSOLUTE RULES:
1. Keep every fact exactly: GPA, institutions, research projects, internships, publications, career goals. NEVER fabricate anything.
2. Warm, genuine first-person voice. The reader must feel a specific human behind the words.
3. Replace all templated openers ("I am writing to express my passion for...") with direct, specific ones rooted in what the text already says.
4. Vary sentence lengths unpredictably. Some sentences: 5-6 words. Some wind through clauses and land somewhere unexpected.
5. Not all paragraphs should be the same length. Include at least one short 1-2 sentence paragraph.
6. NEVER use: passionate, leverage, cutting-edge, robust, seamlessly, paradigm, synergy, pivotal, delve, multifaceted, testament, impactful, groundbreaking.
7. NO casual phrases: "Look,", "Honestly,", "Here's the thing:" — this is formal personal writing.
8. At least one paragraph should open with something concrete and specific rather than an abstract claim.
9. Do NOT add experiences, achievements, or motivations not present in the original.
10. Output ONLY the rewritten SOP. No preamble like "Here is the rewritten version:"."""
    },

    "📝 Personal Statement": {
        "group": "Academic",
        "pipeline": "formal",
        "tone_locked": "Authentic & Reflective",
        "system": """You are a personal statement editor who makes essays sound like real human beings wrote them.

RULES:
1. Preserve all factual content. Zero fabrication.
2. First-person voice. Warm but not sentimental or melodramatic.
3. Replace abstract motivations with concrete, specific ones grounded in what's already in the text.
4. One moment of genuine, understated self-assessment — not dramatic.
5. Vary sentence rhythm: short punchy declarations mixed with longer reflective ones.
6. Avoid: "I have always been fascinated by", "This experience taught me that", "I am passionate about", "deeply impacted."
7. Remove all AI buzzwords.
8. Do NOT add emotions, experiences, or insights not implied by the original.
9. Output ONLY the rewritten statement. No preamble."""
    },

    "🎓 College Application Essay": {
        "group": "Academic",
        "pipeline": "formal",
        "tone_locked": "Vivid & Authentic",
        "system": """You are a college essay coach. Make this essay sound like a genuine, self-aware high school student wrote it — not a consultant or an AI.

RULES:
1. Preserve all actual events, people, and details. Never invent.
2. The voice should feel like a smart 17-18 year old with a distinct personality.
3. Concrete over abstract. Show moments, not summaries.
4. Short punchy sentences mixed with longer, more reflective ones.
5. One small unexpected detail that makes it feel real and personal.
6. Avoid adult corporate-speak. Avoid: "I am passionate", "deeply impacted", "transformative experience", "I have always been."
7. Output ONLY the rewritten essay. No preamble."""
    },

    "🔬 Research Paper / Academic Writing": {
        "group": "Academic",
        "pipeline": "formal",
        "tone_locked": "Scholarly & Precise",
        "system": """You are an academic editor. Refine this text to read as naturally human-written while preserving full scholarly integrity.

RULES:
1. Preserve all citations, data, methodology, technical terminology, and factual claims exactly.
2. Academic transitions (however, therefore, although, moreover) are APPROPRIATE here — keep them.
3. Remove only: hollow filler phrases ("It is important to note that", "It goes without saying"), bloated passive constructions.
4. Replace "delve into", "in the realm of", "as we can see" with direct scholarly equivalents.
5. Do NOT add casual language, contractions, or personal opinions.
6. Maintain argument structure and paragraph order.
7. Output ONLY the revised text. No preamble."""
    },

    "📚 High School / Undergraduate Essay": {
        "group": "Academic",
        "pipeline": "formal",
        "tone_locked": "Clear & Analytical",
        "system": """You are editing this academic essay to sound like a thoughtful student wrote it — clear and analytical, not robotic.

RULES:
1. Keep the argument structure and all evidence intact.
2. Mix sentence lengths: some punchy thesis-like sentences, some longer analytical ones.
3. Replace AI transitions (moreover, furthermore, consequently) with cleaner equivalents (also, this means, and yet, as a result, which is why).
4. Remove AI buzzwords: delve, pivotal, groundbreaking, multifaceted, testament, robust, seamlessly.
5. One concrete example or analogy to anchor the argument where it's currently thin.
6. Formal enough for a classroom — no slang, no casual openers.
7. Output ONLY the rewritten essay. No preamble."""
    },

    # ═══ PROFESSIONAL ══════════════════════════════════════════════════════
    "📧 Professional Email": {
        "group": "Professional",
        "pipeline": "formal",
        "tone_locked": "Professional & Direct",
        "system": """You are lightly editing this professional email so it sounds naturally written — not robotic, not over-formatted.

STRICT RULES:
1. Keep the greeting and sign-off exactly (Dear / Best regards / Sincerely / Hi [Name]).
2. Keep ALL facts, names, dates, project details exactly as stated. Never invent.
3. Only change:
   · Remove filler openers: "I hope this email finds you well," "I am writing to inform you that," "I trust this message finds you well"
   · Replace stiff phrases with direct natural ones: "I am pleased to inform you" → "Wanted to share"
   · Break long run-on sentences into two clear ones
   · Remove redundant qualifiers: "very important" → "important"
4. Do NOT inject casual phrases, humor, or informality inappropriate for professional email.
5. Do NOT start sentences with And/But/So in formal context.
6. Keep bullet points intact if they exist.
7. Output ONLY the rewritten email. No preamble."""
    },

    "💼 Cover Letter": {
        "group": "Professional",
        "pipeline": "formal",
        "tone_locked": "Confident & Genuine",
        "system": """You are a professional editor refining this cover letter to sound authentic and human.

STRICT RULES:
1. Keep ALL factual claims: job titles, companies, skills, achievements, years of experience. Never fabricate.
2. Replace templated opener ("I am writing to express my strong interest") with a direct, confident one.
3. Make the motivation feel genuine — but only from what's already in the text.
4. Vary sentence length — avoid three identical-length sentences in a row.
5. Remove AI buzzwords: leverage, passionate, driven, dynamic, synergy, impactful, results-oriented, seasoned.
6. Keep the closing specific and real, not boilerplate.
7. Keep bullet points if present.
8. Do NOT add new achievements or stories.
9. Output ONLY the rewritten letter. No preamble."""
    },

    "🔗 LinkedIn Post / Bio": {
        "group": "Professional",
        "pipeline": "general",
        "tone_locked": "Authentic Professional",
        "system": """You are a LinkedIn content strategist. Rewrite this to sound like a credible professional, not a corporate AI.

RULES:
1. Keep all facts, titles, achievements, and companies exactly.
2. Confident but not boastful. Specific not vague.
3. Short punchy sentences. No walls of text.
4. Replace LinkedIn clichés: "passionate about", "excited to share", "thrilled to announce", "game-changer", "leverage", "synergy", "results-driven."
5. One concrete, specific detail to make a vague claim feel real.
6. Keep max 3 hashtags if they exist.
7. Output ONLY the rewritten content. No preamble."""
    },

    "📊 Business Report / Executive Summary": {
        "group": "Professional",
        "pipeline": "formal",
        "tone_locked": "Clear & Executive",
        "system": """You are a senior business writer editing this for clarity and executive readability.

RULES:
1. Preserve all data, findings, and recommendations exactly.
2. Replace passive constructions with active voice where it improves clarity.
3. Remove redundant throat-clearing: "It should be noted that", "In light of the above", "As mentioned previously."
4. Remove AI buzzwords: leverage, synergy, paradigm, robust, seamlessly, ecosystem, transformative.
5. Keep headers, bullets, and numbered lists intact.
6. Direct sentences. Shorter over longer where meaning is equal.
7. Output ONLY the revised text. No preamble."""
    },

    "📨 Cold Outreach / Sales Email": {
        "group": "Professional",
        "pipeline": "formal",
        "tone_locked": "Sharp & Personal",
        "system": """You are a sales copywriter editing this cold outreach email to feel human and compelling.

RULES:
1. Keep the core offer, value prop, and CTA exactly as stated. Never fabricate claims.
2. Open with the prospect's pain or gain — not "I wanted to reach out" or "I hope you're doing well."
3. Short paragraphs. Short sentences. Every sentence earns its place.
4. Remove: "I hope you're doing well", "I know you're busy", "circle back", "synergies", "leverage", "solutions."
5. End with one clear, low-friction ask.
6. Output ONLY the rewritten email. No preamble."""
    },

    # ═══ CREATIVE & CONTENT ═════════════════════════════════════════════════
    "✍️ Blog Post / Article": {
        "group": "Creative & Content",
        "pipeline": "general",
        "tone_locked": None,          # Tone selector enabled for this type
        "system": None,               # Built dynamically from tone selection
    },

    "🎯 Marketing Copy / Landing Page": {
        "group": "Creative & Content",
        "pipeline": "general",
        "tone_locked": "Persuasive & Human",
        "system": """You are a conversion copywriter rewriting this to sound like a sharp, experienced human marketer wrote it.

RULES:
1. Keep all product claims, features, and CTAs exactly. Never fabricate benefits.
2. Lead with the benefit, not the feature.
3. Short punchy sentences. Remove every word that doesn't earn its place.
4. Remove: cutting-edge, revolutionary, game-changing, innovative, robust, seamlessly, leverage, groundbreaking.
5. Active voice only.
6. One specific, concrete detail to make a vague claim feel real.
7. Output ONLY the rewritten copy. No preamble."""
    },

    "📱 Social Media Post": {
        "group": "Creative & Content",
        "pipeline": "general",
        "tone_locked": "Casual & Engaging",
        "system": """You are a social media writer. Rewrite this to sound like a real person posted it, not an AI content generator.

RULES:
1. Keep all facts and key messages exactly.
2. Casual, energetic tone. Very short sentences. Real human voice.
3. One conversational hook or rhetorical question.
4. Remove all corporate-speak and AI buzzwords.
5. Keep max 3-5 hashtags if they exist.
6. Output ONLY the rewritten post. No preamble."""
    },

    "📖 Creative / Narrative Writing": {
        "group": "Creative & Content",
        "pipeline": "general",
        "tone_locked": "Vivid & Literary",
        "system": """You are a literary editor helping this piece of creative writing sound authentically human and alive.

RULES:
1. Preserve all story elements: characters, plot points, invented details. Never fabricate.
2. Make the prose feel alive: sensory details, rhythm variation, tension.
3. Vary sentence length dramatically. Mix short fragments with long flowing sentences.
4. Replace generic descriptors ("beautiful", "amazing") with specific, evocative ones.
5. Remove AI tells: "it is worth noting", "needless to say", "as we can see."
6. If there's dialogue, make it sound like real speech — incomplete, alive.
7. Output ONLY the revised text. No preamble."""
    },

    "📰 News / Journalism": {
        "group": "Creative & Content",
        "pipeline": "general",
        "tone_locked": "Objective & Journalistic",
        "system": """You are a copy editor. Rewrite this in clean, neutral AP-style journalistic prose.

RULES:
1. Objective. No opinions or editorial asides.
2. Active voice. Clear, short sentences. Lead with the most important fact.
3. No jargon. No AI buzzwords.
4. Quotes (if present) stay verbatim.
5. Output ONLY the rewritten article. No preamble."""
    },

    # ═══ PERSONAL ═══════════════════════════════════════════════════════════
    "💬 Personal Message / Casual Text": {
        "group": "Personal",
        "pipeline": "general",
        "tone_locked": "Warm & Casual",
        "system": """You are rewriting this to sound like a real person wrote a personal message or text.

RULES:
1. Keep all factual content and intent intact.
2. Very casual, warm. Like texting or emailing a close friend.
3. Short sentences. Natural rhythm.
4. Remove ALL formal language, corporate phrasing, and AI buzzwords.
5. One small personal touch or honest aside if it fits naturally.
6. Output ONLY the rewritten message. No preamble."""
    },

    "💌 Personal Letter / Thank You Note": {
        "group": "Personal",
        "pipeline": "formal",
        "tone_locked": "Warm & Genuine",
        "system": """You are editing this personal letter or thank you note to sound heartfelt and genuinely human.

RULES:
1. Keep all specific details about the person or situation exactly.
2. Warm, personal tone — written with care for a specific person.
3. Remove templated phrases: "I am writing to express my sincere gratitude", "I cannot thank you enough."
4. One specific, concrete memory or detail to make it feel personal (only if it's implied in the original).
5. Vary sentence length. Let some sentences breathe.
6. Output ONLY the rewritten letter. No preamble."""
    },

    # ═══ SPECIALIZED ════════════════════════════════════════════════════════
    "⚖️ Legal / Contract Simplification": {
        "group": "Specialized",
        "pipeline": "formal",
        "tone_locked": "Clear & Precise",
        "system": """You are editing this legal or contract text to be clearer and more readable while preserving all legal meaning.

RULES:
1. Preserve ALL legal terms, obligations, parties, dates, and clauses exactly. Legal meaning must be identical.
2. Replace unnecessarily complex constructions with direct equivalents that preserve legal meaning exactly.
3. Do NOT remove any substantive legal content or alter the legal effect.
4. "in the event that" → "if". "hereinafter referred to as" → acceptable shorthand. "it is hereby agreed that" → "the parties agree that."
5. Output ONLY the revised text. No preamble."""
    },

    "🏥 Medical / Health Writing": {
        "group": "Specialized",
        "pipeline": "formal",
        "tone_locked": "Clear & Compassionate",
        "system": """You are a medical communications editor. Rewrite this health content to sound clear, human, and compassionate.

RULES:
1. Preserve ALL medical facts, dosages, diagnoses, instructions, and warnings exactly.
2. Replace overly clinical constructions with plain language equivalents where clarity is improved.
3. Warm but factual. Not alarmist. Not dismissive.
4. If patient-facing: use "you" language. If clinical: maintain appropriate register.
5. Output ONLY the revised text. No preamble."""
    },

    "🛠️ Technical Documentation": {
        "group": "Specialized",
        "pipeline": "formal",
        "tone_locked": "Clear & Technical",
        "system": """You are a technical writer editing this documentation for clarity and human readability.

RULES:
1. Preserve all technical details, commands, parameters, and specifications exactly.
2. Active voice: "Note that X" instead of "It should be noted that X."
3. Break overly long sentences into sequential steps where appropriate.
4. Remove filler phrases and AI-generic language.
5. Keep numbered lists and code blocks intact.
6. Output ONLY the revised text. No preamble."""
    },
}

# Build group index
CONTENT_GROUPS = {}
for k, v in CONTENT_TYPES.items():
    g = v["group"]
    if g not in CONTENT_GROUPS:
        CONTENT_GROUPS[g] = []
    CONTENT_GROUPS[g].append(k)


# ─────────────────────────────────────────────────────────────────────────────
#  TONE PROMPTS (Blog/Article only)
# ─────────────────────────────────────────────────────────────────────────────

TONE_PROMPTS = {
    "Conversational": (
        "Rewrite in a genuine, casual human voice — like a smart person explaining something to a friend. "
        "Mix very short sentences (3-6 words) with longer, rambling ones. Unpredictable vocabulary. Real opinions. "
        "Avoid uniform paragraph lengths. No AI buzzwords. No formal transitions. "
        "Output ONLY the rewritten text. No preamble."
    ),
    "Professional": (
        "Rewrite in a confident, direct professional voice — like a senior colleague giving a clear briefing, not a consultant writing a report. "
        "Direct. No fluff. Active voice. Mix short punchy sentences with medium explanatory ones. No jargon. "
        "Replace every stiff phrase with a natural professional equivalent. "
        "Output ONLY the rewritten text. No preamble."
    ),
    "Storyteller": (
        "Rewrite with narrative flow and rhythm. Make abstract concepts concrete and visual. "
        "Use em dashes — like this — for emphasis. Vary sentence length dramatically. "
        "Show cause and effect through narrative. One concrete scene-setting detail or analogy. "
        "Output ONLY the rewritten text. No preamble."
    ),
    "Opinionated": (
        "Rewrite in a bold, first-person opinionated voice. Use 'I' naturally. Be direct and confident. "
        "Rhetorical questions: 'Why does this matter? Because...' Some sentences start with 'Look,' or 'Here's the thing:' where natural. "
        "Challenge obvious points. Vary sentence rhythm wildly. "
        "Output ONLY the rewritten text. No preamble."
    ),
    "Witty": (
        "Rewrite with wit and sharpness — clever, occasionally irreverent without trying too hard. "
        "Smart observations. Light humor where natural. One well-placed subversion of expectation. "
        "Confident, breezy tone. Never forced. "
        "Output ONLY the rewritten text. No preamble."
    ),
    "Journalistic": (
        "Rewrite in clean, neutral, AP-style prose. Objective. No opinions or editorial asides. "
        "Active voice. Short clear sentences. Lead with the most important point. "
        "Output ONLY the rewritten text. No preamble."
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
#  DETECTOR TARGETING
# ─────────────────────────────────────────────────────────────────────────────

def detector_instructions(gpt: bool, ori: bool, tur: bool, zer: bool, qui: bool) -> str:
    parts = []
    if gpt:
        parts.append(
            "GPTZERO (perplexity + burstiness): Make at least 20% of sentences dramatically short (<7 words) "
            "and 20% deliberately long (>25 words with embedded clauses). Use at least one word that is correct "
            "but slightly unexpected in context. Include one rhetorical question. Never start two consecutive "
            "sentences with the same word."
        )
    if ori:
        parts.append(
            "ORIGINALITY.AI (semantic fingerprinting): Restructure the logical ORDER of ideas across paragraphs — "
            "do not just rephrase in the same sequence. Use at least two idiomatic or colloquial expressions. "
            "Introduce one concrete real-world detail (a number, a named scenario). Avoid clean topic-sentence → "
            "supporting-detail → conclusion paragraph structure. Let at least one paragraph begin mid-thought."
        )
    if tur:
        parts.append(
            "TURNITIN (stylometric patterns + personal voice): Break paragraph symmetry — not all 3-4 sentences; "
            "include at least one 1-sentence paragraph and one 6+ sentence paragraph. Include at least one "
            "subjective observation: 'which, in practice, works better than it sounds.' Avoid parallel list "
            "structures (First... Second... Third...). Vary where the main claim appears within paragraphs."
        )
    if zer:
        parts.append(
            "ZEROGPT (formal transitions + uniform clauses): Replace ALL of these: However / Furthermore / Moreover / "
            "Additionally / Consequently / Nevertheless / In conclusion. Use instead: But / Also / So / Plus / "
            "That said / Even so / And yet / Which means. Vary clause length within sentences. At least two "
            "sentences should begin with a conjunction (And, But, So). At least one sentence should be "
            "deliberately shorter than everything around it."
        )
    if qui:
        parts.append(
            "QUILLBOT (paraphrase-pattern detection): Do NOT simply swap synonyms — Quillbot detects this. "
            "Instead restructure sentences syntactically: change grammatical form, not just word choice. "
            "Convert some noun phrases to verb phrases and vice versa. Combine or split sentences. "
            "Change perspective/framing of claims. Introduce at least one informal phrase that no paraphraser "
            "would generate."
        )
    if not parts:
        return ""
    return "\n\nDETECTOR-SPECIFIC RULES:\n" + "\n".join(f"• {p}" for p in parts)


# ─────────────────────────────────────────────────────────────────────────────
#  CLICHE REMOVAL  (post-processing — cliché phrases only, no structural edits)
# ─────────────────────────────────────────────────────────────────────────────

CLICHES = {
    "delve into": ["dig into", "explore", "look at"],
    "delves into": ["digs into", "explores"],
    "delving into": ["digging into", "exploring"],
    "utilize": ["use", "apply"],
    "utilizes": ["uses", "applies"],
    "leverage": ["use", "tap into", "draw on"],
    "leverages": ["uses", "draws on"],
    "foster": ["build", "grow", "encourage"],
    "facilitate": ["help", "enable"],
    "harness": ["use", "tap into", "channel"],
    "realm": ["area", "field", "world"],
    "landscape": ["field", "scene", "environment"],
    "testament": ["proof", "sign", "evidence"],
    "paradigm": ["model", "approach", "framework"],
    "synergy": ["teamwork", "collaboration"],
    "ecosystem": ["system", "network", "environment"],
    "paramount": ["key", "critical", "essential"],
    "pivotal": ["key", "crucial", "central"],
    "groundbreaking": ["new", "innovative", "novel"],
    "cutting-edge": ["new", "modern", "latest"],
    "cutting edge": ["new", "modern", "latest"],
    "robust": ["strong", "solid", "reliable"],
    "comprehensive": ["complete", "thorough", "detailed"],
    "innovative": ["new", "creative", "fresh"],
    "transformative": ["significant", "major", "powerful"],
    "multifaceted": ["complex", "layered", "varied"],
    "seamlessly": ["smoothly", "easily", "naturally"],
    "in conclusion": ["to wrap up", "so", "in short"],
    "in summary": ["in short", "briefly"],
    "it is important to note that": ["worth noting,", "note that"],
    "it's important to note that": ["worth noting,", "note that"],
    "it is worth noting that": ["worth noting,"],
    "it's worth noting that": ["worth noting,"],
    "in order to": ["to"],
    "due to the fact that": ["because", "since"],
    "game-changer": ["big shift", "major change"],
    "game changer": ["big shift", "major change"],
    "needless to say": ["clearly", "obviously"],
    "as we can see": ["clearly", "as shown"],
    "it goes without saying": ["clearly"],
    "at the end of the day": ["ultimately", "in the end"],
}


def remove_cliches(text: str) -> str:
    for phrase, options in sorted(CLICHES.items(), key=lambda x: -len(x[0])):
        pattern = r'(?<![A-Za-z])' + re.escape(phrase) + r'(?![A-Za-z])'
        if re.search(pattern, text, flags=re.IGNORECASE):
            text = re.sub(pattern, random.choice(options), text, count=1, flags=re.IGNORECASE)
    return text


def clean_text(text: str) -> str:
    """Remove LLM preamble artifacts and fix punctuation spacing."""
    # Strip common LLM preamble patterns
    text = re.sub(
        r'^(Here is|Here\'s|Below is|Below\'s|This is|The following is)'
        r'[^:\n]*:?\s*\n+',
        '', text, flags=re.IGNORECASE
    )
    # Remove <think>...</think> blocks from reasoning models
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Fix double periods
    text = re.sub(r'\.{2,}', '.', text)
    # Fix space before punctuation
    text = re.sub(r' +([.,!?;:])', r'\1', text)
    # Collapse multiple spaces
    text = re.sub(r'  +', ' ', text)
    # Collapse excessive blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
#  API CALL WRAPPERS
# ─────────────────────────────────────────────────────────────────────────────

def call_openrouter(api_key: str, model: str, system: str, user: str, temperature: float, max_tokens: int = 3500) -> str:
    import requests
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://authentica-humanizer.app",
        "X-Title": "Authentica v6",
    }
    body = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    }
    r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=body, timeout=120)
    r.raise_for_status()
    data = r.json()
    # Handle cases where content may be empty (reasoning models)
    content = data["choices"][0]["message"].get("content") or ""
    return content.strip()


def call_groq(api_key: str, model: str, system: str, user: str, temperature: float, max_tokens: int = 3500) -> str:
    from groq import Groq
    client = Groq(api_key=api_key)
    r = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=0.95,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ]
    )
    return r.choices[0].message.content.strip()


def call_gemini(api_key: str, model: str, system: str, user: str, temperature: float, max_tokens: int = 3500) -> str:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    gmodel = genai.GenerativeModel(
        model_name=model,
        system_instruction=system,
        generation_config=genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
    )
    response = gmodel.generate_content(user)
    return response.text.strip()


def call_api(provider: str, api_key: str, model: str, system: str, user: str,
             temperature: float, max_tokens: int = 3500) -> str:
    if provider == "openrouter":
        return call_openrouter(api_key, model, system, user, temperature, max_tokens)
    elif provider == "groq":
        return call_groq(api_key, model, system, user, temperature, max_tokens)
    elif provider == "gemini":
        return call_gemini(api_key, model, system, user, temperature, max_tokens)
    raise ValueError(f"Unknown provider: {provider}")


# ─────────────────────────────────────────────────────────────────────────────
#  HUMANIZE — MAIN FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

FORBIDDEN_WORDS = (
    "FORBIDDEN — never use these words or phrases: delve, utilize, leverage, paramount, landscape, realm, "
    "testament, moreover, furthermore, in conclusion, cutting-edge, game-changer, groundbreaking, pivotal, "
    "robust, seamlessly, foster, comprehensive, transformative, synergy, ecosystem, paradigm, multifaceted, "
    "it is important to note, needless to say, as we can see, it goes without saying, in order to, "
    "it is worth noting, showcase (prefer: show/highlight)."
)

GENERAL_BEST_MODEL = {
    "openrouter": "qwen/qwen3-235b-a22b:free",   # Best free model for creative writing
    "groq":       "llama-3.3-70b-versatile",
    "gemini":     "gemini-2.0-flash",
}


def humanize(text, content_type, tone, provider, api_key, model_id,
             stealth, gpt, ori, tur, zer, qui, progress_callback=None):

    ct = CONTENT_TYPES[content_type]
    pipeline = ct["pipeline"]
    ct_sys = ct["system"]

    det_rules = detector_instructions(gpt, ori, tur, zer, qui)

    def call(sys, usr, temp, max_tok=3000):
        return call_api(provider, api_key, model_id, sys, usr, temp, max_tok)

    def call_best(sys, usr, temp, max_tok=3500):
        """For general pipeline, always use the best model for the provider."""
        best_model = GENERAL_BEST_MODEL.get(provider, model_id)
        return call_api(provider, api_key, best_model, sys, usr, temp, max_tok)

    try:
        # ─── FORMAL PIPELINE (1 pass) ──────────────────────────────────
        if pipeline == "formal":
            if progress_callback:
                progress_callback(0.4, "Rewriting…")
            result = call(ct_sys, f"Edit this text:\n\n{text}", 0.7)
            if progress_callback:
                progress_callback(0.85, "Post-processing…")
            result = clean_text(result)
            if stealth:
                result = remove_cliches(result)
            if progress_callback:
                progress_callback(1.0, "Done")
            return result

        # ─── GENERAL PIPELINE (4 passes) ───────────────────────────────
        # Build the base humanization system prompt
        if ct_sys:
            base_sys = ct_sys
        else:
            base_sys = (
                f"You are rewriting this text. {TONE_PROMPTS.get(tone, TONE_PROMPTS['Conversational'])}"
            )

        full_sys = base_sys + det_rules + f"\n\n{FORBIDDEN_WORDS}\n\nOutput ONLY the rewritten text. No preamble."

        # PASS 1 — Structural deconstruction
        # Goal: break AI's predictable paragraph layout before humanizing
        if progress_callback:
            progress_callback(0.15, "Pass 1 — Restructuring…")
        p1 = call_best(
            (
                "You are a structural editor. Break this text's predictable AI structure.\n\n"
                "Rules:\n"
                "- Reorder arguments or ideas within paragraphs (but keep ALL facts intact)\n"
                "- Make paragraph lengths unequal — some very short (1-2 sentences), some longer\n"
                "- Start at least two paragraphs mid-thought rather than with a clear topic sentence\n"
                "- Do NOT add new information. Do NOT use AI buzzwords.\n"
                "- Vary sentence lengths dramatically within each paragraph\n"
                "- Output ONLY the restructured text. No preamble."
            ),
            text,
            1.25,
        )
        p1 = clean_text(p1)

        # PASS 2 — Voice and tone humanization
        if progress_callback:
            progress_callback(0.40, "Pass 2 — Humanizing voice…")
        p2 = call_best(
            full_sys,
            f"Apply your full humanization approach to this text. Make it sound undeniably like a human wrote it:\n\n{p1}",
            1.15,
        )
        p2 = clean_text(p2)

        # PASS 3 — Burstiness and rhythm
        if progress_callback:
            progress_callback(0.65, "Pass 3 — Rhythm & burstiness…")
        p3 = call_best(
            (
                "You are a sentence rhythm specialist. Make this text's rhythm feel undeniably human.\n\n"
                "Rules:\n"
                "- After any sentence over 22 words, the next sentence should be under 10 words\n"
                "- Replace every formal transition (However, Furthermore, Moreover, Additionally, "
                "Consequently, Nevertheless) with a casual equivalent (But, Also, So, Plus, That said, Even so)\n"
                "- The first sentence of at least two paragraphs should be unusually short — under 8 words\n"
                "- At least one paragraph should have no clear 'topic sentence'\n"
                "- If three consecutive sentences are similar in length, break the pattern\n"
                "- Do NOT add new facts. Do NOT use AI buzzwords.\n"
                "- Output ONLY the result. No preamble."
            ),
            p2,
            1.0,
        )
        p3 = clean_text(p3)

        # PASS 4 — Coherence and final polish
        if progress_callback:
            progress_callback(0.85, "Pass 4 — Final polish…")
        p4 = call_best(
            (
                "Final quality pass. Make this text flow naturally while preserving all human-like qualities.\n\n"
                "Rules:\n"
                "- Fix any genuinely confusing or awkward phrasing\n"
                "- Ensure the overall meaning and argument are still clear and intact\n"
                "- If any AI buzzwords slipped in (delve, utilize, leverage, paramount, groundbreaking, "
                "pivotal, robust, seamlessly), replace them with plain alternatives\n"
                "- Do NOT add new content. Do NOT re-introduce AI sentence patterns.\n"
                "- Output ONLY the final text. No preamble."
            ),
            p3,
            0.85,
        )
        result = clean_text(p4)

        if stealth:
            result = remove_cliches(result)

        if progress_callback:
            progress_callback(1.0, "Done")

        return result

    except Exception as e:
        return f"Error: {str(e)}"


# ─────────────────────────────────────────────────────────────────────────────
#  CACHE
# ─────────────────────────────────────────────────────────────────────────────

def make_cache_key(*args, do_random: bool) -> str:
    seed = str(random.random()) if do_random else "fixed"
    raw = "|".join(str(a) for a in args) + seed
    return hashlib.md5(raw.encode()).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ✍️ Authentica v6")
    st.markdown("<div style='color:#4a4a6a;font-size:12px;margin-bottom:16px'>AI Text Humanizer</div>", unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("**Provider**")
    provider_label = st.radio(
        "Provider",
        list(PROVIDER_LABELS.keys()),
        label_visibility="collapsed",
    )
    provider = PROVIDER_LABELS[provider_label]

    hint_label, hint_placeholder, hint_url = PROVIDER_KEY_HINTS[provider]
    api_key = st.text_input(
        hint_label, type="password", placeholder=hint_placeholder,
        label_visibility="visible"
    )
    st.markdown(f"<div style='color:#3a3a5a;font-size:11px;margin-bottom:4px'>🔗 {hint_url}</div>", unsafe_allow_html=True)

    # Model selector — only shown when Groq or Gemini (OpenRouter model selected separately)
    if provider == "openrouter":
        st.markdown("**Model (OpenRouter free)**")
        or_model_label = st.selectbox("OR Model", list(OPENROUTER_MODELS.keys()), label_visibility="collapsed")
        selected_model = OPENROUTER_MODELS[or_model_label]
    elif provider == "groq":
        st.markdown("**Model (Groq)**")
        gr_model_label = st.selectbox("Groq Model", list(GROQ_MODELS.keys()), label_visibility="collapsed")
        selected_model = GROQ_MODELS[gr_model_label]
    else:
        st.markdown("**Model (Gemini)**")
        ge_model_label = st.selectbox("Gemini Model", list(GEMINI_MODELS.keys()), label_visibility="collapsed")
        selected_model = GEMINI_MODELS[ge_model_label]

    st.markdown("---")

    st.markdown("**Target Detectors**")
    ca, cb = st.columns(2)
    with ca:
        t_gpt = st.checkbox("GPTZero",      value=True)
        t_tur = st.checkbox("Turnitin",     value=True)
        t_qui = st.checkbox("Quillbot",     value=True)
    with cb:
        t_ori = st.checkbox("Originality",  value=True)
        t_zer = st.checkbox("ZeroGPT",      value=True)

    st.markdown("---")

    st.markdown("**Options**")
    stealth   = st.checkbox("Stealth Post-Processing", value=True,
                             help="Applies cliché removal after all LLM passes")
    randomize = st.checkbox("Randomize Each Run",      value=True,
                             help="Generates a fresh version every run")

    st.markdown("---")
    st.markdown("""<div style='font-size:11px;color:#2e2e4e;line-height:1.8'>
<b style='color:#3a3a5a'>Free API limits:</b><br>
OpenRouter — rate limited but free<br>
Groq — 14,400 req/day free<br>
Gemini — 1,000 req/day free
</div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div style="
  background: linear-gradient(135deg, #0f0f1a 0%, #12121f 50%, #0a0a15 100%);
  border: 1px solid #1e1e30;
  border-radius: 16px;
  padding: 28px 36px;
  margin-bottom: 24px;
">
  <h1 style="
    font-family: 'Fraunces', serif !important;
    font-size: 30px;
    color: #e8e8f8;
    margin: 0 0 6px 0;
    letter-spacing: -0.5px;
  ">✍️ Authentica <span style="color:#6366f1">v6</span></h1>
  <p style="color:#3a3a5a;font-size:13px;margin:0;letter-spacing:0.05em;text-transform:uppercase">
    Structural AI Humanizer &nbsp;·&nbsp; 5 Detector Targets &nbsp;·&nbsp; 20 Content Types &nbsp;·&nbsp; 3 Free Providers
  </p>
</div>
""", unsafe_allow_html=True)

# Detector badges
def badge(label, active):
    if active:
        return f'<span style="background:rgba(99,102,241,0.15);color:#818cf8;border:1px solid rgba(99,102,241,0.35);border-radius:20px;padding:3px 11px;font-size:11px;font-weight:600;margin:2px;display:inline-block;letter-spacing:0.04em">{label}</span>'
    return f'<span style="background:rgba(255,255,255,0.03);color:#2e2e4e;border:1px solid rgba(255,255,255,0.06);border-radius:20px;padding:3px 11px;font-size:11px;font-weight:600;margin:2px;display:inline-block;letter-spacing:0.04em">{label}</span>'

badges_html = "".join(badge(l, a) for l, a in [
    ("GPTZero", t_gpt), ("Originality.ai", t_ori), ("Turnitin", t_tur), ("ZeroGPT", t_zer), ("Quillbot", t_qui)
])
st.markdown(f'<div style="margin-bottom:20px">{badges_html}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  CONTENT TYPE SELECTOR
# ─────────────────────────────────────────────────────────────────────────────

st.markdown('<div style="color:#3a3a5a;font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:10px">Content Type</div>', unsafe_allow_html=True)

group_col, type_col, info_col = st.columns([1.1, 2, 1.2])
with group_col:
    selected_group = st.radio("Group", list(CONTENT_GROUPS.keys()), label_visibility="collapsed")
with type_col:
    content_type = st.selectbox(f"Type ({selected_group})", CONTENT_GROUPS[selected_group], label_visibility="collapsed")
with info_col:
    ct_info = CONTENT_TYPES[content_type]
    pl = "🚀 4-Pass" if ct_info["pipeline"] == "general" else "🎯 1-Pass"
    tl = ct_info.get("tone_locked") or "User-selected"
    st.markdown(f"""
<div style="background:#0f0f18;border:1px solid #1a1a2a;border-radius:10px;padding:12px 14px;height:100%">
  <div style="color:#4f46e5;font-size:12px;font-weight:700">{pl}</div>
  <div style="color:#3a3a5a;font-size:11px;margin-top:4px">Tone: <span style="color:#5a5a8a">{tl}</span></div>
  <div style="color:#3a3a5a;font-size:11px;margin-top:3px">Provider: <span style="color:#5a5a8a">{provider.capitalize()}</span></div>
</div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  TONE SELECTOR  (Blog/Article only)
# ─────────────────────────────────────────────────────────────────────────────

tone = "Conversational"
if ct_info.get("tone_locked") is None:
    st.markdown('<div style="color:#3a3a5a;font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;margin:16px 0 10px">Tone</div>', unsafe_allow_html=True)
    tone_names = list(TONE_PROMPTS.keys())
    tcols = st.columns(len(tone_names))
    for i, t_name in enumerate(tone_names):
        with tcols[i]:
            is_active = st.session_state.get("tone", "Conversational") == t_name
            if st.button(t_name, key=f"tone_{i}", use_container_width=True,
                         type="primary" if is_active else "secondary"):
                st.session_state["tone"] = t_name
    tone = st.session_state.get("tone", "Conversational")
    st.markdown(
        f'<div style="background:#0f0f18;border-left:3px solid #4f46e5;border-radius:0 8px 8px 0;'
        f'padding:9px 14px;font-size:12px;color:#5a5a8a;margin:8px 0 0">'
        f'<b style="color:#6366f1">{tone}</b> — {TONE_PROMPTS[tone][:90]}…</div>',
        unsafe_allow_html=True
    )


st.markdown('<div style="margin:20px 0 0;border-top:1px solid #131320"></div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  INPUT / OUTPUT COLUMNS
# ─────────────────────────────────────────────────────────────────────────────

col1, col2 = st.columns(2, gap="medium")

with col1:
    st.markdown('<div style="color:#3a3a5a;font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:8px">Input</div>', unsafe_allow_html=True)
    input_text = st.text_area(
        "Input",
        height=440,
        placeholder=(
            "Paste your AI-generated text here…\n\n"
            "Works with: essays, emails, SOPs, blog posts, cover letters,\n"
            "creative writing, marketing copy, reports, and more."
        ),
        label_visibility="collapsed",
    )
    wc_in = len(input_text.split()) if input_text.strip() else 0
    st.markdown(
        f'<div style="color:#2e2e4e;font-size:12px;margin-top:6px">{wc_in} words</div>',
        unsafe_allow_html=True
    )
    run_btn = st.button("✦ Humanize Now", type="primary", use_container_width=True)


with col2:
    st.markdown('<div style="color:#3a3a5a;font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:8px">Output</div>', unsafe_allow_html=True)

    out_area   = st.empty()
    prog_slot  = st.empty()
    wc_slot    = st.empty()
    copy_slot  = st.empty()
    status_slot = st.empty()
    stats_slot = st.empty()

    if run_btn:
        # ── Validation ──────────────────────────────────────────────────
        ok = True
        if not api_key:
            status_slot.error(f"⚠️ Add your {provider.capitalize()} API key in the sidebar.")
            ok = False
        if not input_text.strip():
            status_slot.warning("Paste some text to humanize.")
            ok = False
        elif wc_in < 15:
            status_slot.warning("Text is too short. Provide at least 15 words for best results.")
            ok = False
        if not any([t_gpt, t_ori, t_tur, t_zer, t_qui]):
            status_slot.warning("Select at least one target detector in the sidebar.")
            ok = False

        if ok:
            if "cache" not in st.session_state:
                st.session_state.cache = {}

            ck = make_cache_key(
                input_text, content_type, tone, provider, selected_model,
                stealth, t_gpt, t_ori, t_tur, t_zer, t_qui,
                do_random=randomize
            )

            # Progress bar
            pbar = prog_slot.progress(0, text="Starting…")
            def update_progress(val, msg):
                pbar.progress(val, text=msg)

            if ck in st.session_state.cache and not randomize:
                result = st.session_state.cache[ck]
                update_progress(1.0, "Loaded from cache")
            else:
                result = humanize(
                    text=input_text,
                    content_type=content_type,
                    tone=tone,
                    provider=provider,
                    api_key=api_key,
                    model_id=selected_model,
                    stealth=stealth,
                    gpt=t_gpt, ori=t_ori, tur=t_tur, zer=t_zer, qui=t_qui,
                    progress_callback=update_progress,
                )
                if not result.startswith("Error:"):
                    st.session_state.cache[ck] = result

            prog_slot.empty()

            if result.startswith("Error:"):
                status_slot.error(result)
            else:
                # Output text area
                out_area.text_area(
                    "Output",
                    value=result,
                    height=440,
                    label_visibility="collapsed",
                    key="output_text_area",
                )

                wc_out = len(result.split())
                wc_slot.markdown(
                    f'<div style="color:#2e2e4e;font-size:12px;margin-top:6px">{wc_out} words</div>',
                    unsafe_allow_html=True
                )

                # ── Working clipboard button ─────────────────────────────
                with copy_slot:
                    clipboard_button(result, "📋 Copy to Clipboard")

                status_slot.success(
                    f"✓ Done — {'4-pass' if ct_info['pipeline'] == 'general' else '1-pass'} pipeline complete."
                )

                # Stats
                passes   = 4 if ct_info["pipeline"] == "general" else 1
                det_count = sum([t_gpt, t_ori, t_tur, t_zer, t_qui])
                with stats_slot:
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Passes",    passes)
                    m2.metric("Detectors", det_count)
                    m3.metric("Words Out", wc_out)
                    m4.metric("Stealth",   "On" if stealth else "Off")


# ─────────────────────────────────────────────────────────────────────────────
#  TIPS & REFERENCE
# ─────────────────────────────────────────────────────────────────────────────

st.markdown('<div style="margin-top:32px;border-top:1px solid #131320;padding-top:20px"></div>', unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    st.markdown('<div style="color:#3a3a5a;font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:10px">Manual refinement tips</div>', unsafe_allow_html=True)
    tips = [
        "Add one real specific detail — a year, a number, a named example",
        'Turn one statement into a question: "Why does this matter? Because..."',
        "Break one symmetrical long paragraph in half",
        "Add one self-correction or parenthetical aside (like this one)",
        "Read it aloud — anything that sounds robotic is a detector signal",
        "Vary where the key claim sits: sometimes lead, sometimes build to it",
    ]
    for tip in tips:
        st.markdown(
            f'<div style="background:#0f0f18;border-left:3px solid #1e1e35;border-radius:0 7px 7px 0;'
            f'padding:8px 13px;font-size:12px;color:#4a4a6a;margin:5px 0">{tip}</div>',
            unsafe_allow_html=True
        )

with c2:
    st.markdown('<div style="color:#3a3a5a;font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:10px">Why v6 gets lower scores</div>', unsafe_allow_html=True)
    reasons = [
        ("No contraction injection", "Detectors now flag forced I'm/I'd/I've chains as a humanizer artifact"),
        ("Structural Pass 1", "Breaks AI's predictable topic-sentence→support→conclusion layout before humanizing"),
        ("Syntax restructuring", "Sentences change grammatical form, not just vocabulary — defeats Quillbot detection"),
        ("Rhythm Pass 3", "Explicitly targets burstiness (sentence length variation) — the #1 GPTZero signal"),
        ("Preamble stripping", 'Removes "Here is the rewritten text:" and <think> blocks from reasoning models'),
    ]
    for title, desc in reasons:
        st.markdown(
            f'<div style="background:#0f0f18;border-left:3px solid #1e1e35;border-radius:0 7px 7px 0;'
            f'padding:8px 13px;font-size:12px;color:#4a4a6a;margin:5px 0">'
            f'<b style="color:#3a3a5a">{title}</b> — {desc}</div>',
            unsafe_allow_html=True
        )

with st.expander("📖 Full reference — models, pipelines, detector signals"):
    st.markdown("""
### Free Model Guide

| Provider | Model | Best for | Free limit |
|---|---|---|---|
| OpenRouter | **Qwen3-235B-A22B** | Best overall quality, creative writing | Rate limited |
| OpenRouter | **Llama 4 Maverick** | Long context, agentic tasks | Rate limited |
| OpenRouter | **DeepSeek V3** | Reasoning, technical content | Rate limited |
| OpenRouter | **Mistral Large 3** | EU-hosted, reliable, formal writing | Rate limited |
| Groq | **Llama 3.3 70B** | Fastest inference, general content | 14,400 req/day |
| Gemini | **Gemini 2.0 Flash** | Multimodal, fast, good instruction-following | 1,000 req/day |

**Setup:** OpenRouter at openrouter.ai/keys · Groq at console.groq.com · Gemini at aistudio.google.com/apikey

---

### Pipeline Summary

| Type | Passes | What each pass does |
|---|---|---|
| **General (Blog, LinkedIn, Marketing, etc.)** | 4 | 1: Structural deconstruction → 2: Voice humanization → 3: Burstiness/rhythm → 4: Coherence polish |
| **Formal (SOP, Email, Cover Letter, etc.)** | 1 | Single carefully-prompted pass with document-specific rules |

---

### Detector Signal Map

| Detector | Primary signal measured | v6 counter-strategy |
|---|---|---|
| **GPTZero 3.15b** | Token perplexity + sentence burstiness | Pass 1 breaks structure; Pass 3 forces dramatic length variation; high temperature raises perplexity |
| **Originality.ai** | Semantic fingerprinting vs known LLM probability chains | Reorders idea sequence, injects idioms, adds concrete specifics, avoids predictable paragraph structure |
| **Turnitin** | Stylometric ML — structural patterns, paragraph symmetry, absent personal voice | Breaks paragraph symmetry, injects subjective observations, eliminates parallel list structures |
| **ZeroGPT** | Formal transition detection + uniform clause lengths | All formal transitions replaced in Pass 3; clause lengths varied explicitly |
| **Quillbot** | Paraphrase pattern — detects synonym-replacement chains as distinct fingerprint | Rewrites at syntax level (grammatical form, perspective, structure) not vocabulary level |

---

### Common reasons detection remains high (after using this tool)

1. **Text is very short** (<100 words) — detectors are more confident on short texts
2. **Highly technical content** — domain jargon creates low-perplexity sequences that read as AI
3. **Original was heavily formulaic** — even 4 passes can't fully mask extreme structural AI patterns
4. **Post-edit drift** — running the output through another tool (Quillbot, etc.) can re-introduce AI patterns
5. **Model rate limits** — free models at capacity may return lower-quality rewrites
""")

st.markdown(
    '<div style="text-align:center;color:#1e1e2e;font-size:11px;margin-top:32px;padding:16px">'
    'Authentica v6 · Structural AI Humanizer · Powered by OpenRouter / Groq / Gemini · For legitimate content work only'
    '</div>',
    unsafe_allow_html=True
)
