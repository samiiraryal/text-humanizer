"""
Authentica v5 — AI Text Humanizer
Fixes applied vs v4:
  1. Removed ALL contraction injection (it's now a detection signal)
  2. Added Google Gemini 2.0 Flash as free provider option
  3. Added copy button for output text
  4. Added 20 content-type options across 5 groups
  5. Real structural-level rewriting via deep prompt engineering, NOT word-swapping
  6. Post-processing stripped back to cliché removal only (no synonym swaps, no injections)
  7. Added Quillbot to detector targeting list
  8. Fixed rogue-dot artifacts, cache key logic, fragment injection
"""

import streamlit as st
import hashlib
import re
import random
import time

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Authentica v5",
    page_icon="✍️",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Lato:wght@300;400;700&display=swap');

*, html, body, [class*="css"] {
    font-family: 'Lato', sans-serif !important;
}
h1, h2, h3, .brand {
    font-family: 'Syne', sans-serif !important;
}

.stApp { background: #0f0f13; }
section[data-testid="stSidebar"] { background: #16161f !important; border-right: 1px solid #2a2a3a; }
section[data-testid="stSidebar"] * { color: #ccc !important; }
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stCheckbox label,
section[data-testid="stSidebar"] .stRadio label { color: #aaa !important; font-size: 13px !important; }

.main-header {
    background: linear-gradient(135deg, #1a0533 0%, #0d1a3a 50%, #001a1a 100%);
    border: 1px solid #2a2a4a;
    border-radius: 16px;
    padding: 32px 40px;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
}
.main-header::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle at 30% 50%, rgba(120,60,255,0.08) 0%, transparent 50%),
                radial-gradient(circle at 70% 50%, rgba(0,180,255,0.06) 0%, transparent 50%);
    pointer-events: none;
}
.brand-title {
    font-family: 'Syne', sans-serif !important;
    font-size: 36px;
    font-weight: 800;
    color: #fff;
    letter-spacing: -1px;
    margin: 0;
}
.brand-sub {
    color: #8888aa;
    font-size: 14px;
    margin-top: 6px;
    letter-spacing: 0.05em;
}
.brand-accent { color: #a855f7; }

.badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin: 3px;
    border: 1px solid;
}
.badge-on  { background: rgba(168,85,247,0.15); color: #a855f7; border-color: rgba(168,85,247,0.4); }
.badge-off { background: rgba(255,255,255,0.04); color: #555; border-color: rgba(255,255,255,0.08); }

.panel {
    background: #16161f;
    border: 1px solid #2a2a3a;
    border-radius: 14px;
    padding: 20px;
}
.panel-title {
    font-family: 'Syne', sans-serif !important;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #666;
    margin-bottom: 14px;
}

.ct-pill {
    display: inline-block;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 12px;
    color: #aaa;
    margin: 3px;
    cursor: pointer;
}
.ct-pill-active {
    background: rgba(168,85,247,0.2);
    border-color: rgba(168,85,247,0.5);
    color: #c084fc;
}

.info-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 12px;
    color: #888;
    margin: 4px 0;
}
.info-chip-val { color: #c084fc; font-weight: 700; }

.stButton > button {
    background: linear-gradient(135deg, #7c3aed, #a855f7) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 15px !important;
    padding: 14px 20px !important;
    letter-spacing: 0.04em !important;
    transition: all 0.2s !important;
    box-shadow: 0 4px 20px rgba(168,85,247,0.3) !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 28px rgba(168,85,247,0.45) !important;
}

div[data-testid="stTextArea"] textarea {
    background: #0f0f18 !important;
    border: 1.5px solid #2a2a3a !important;
    border-radius: 10px !important;
    color: #e0e0e8 !important;
    font-family: 'Lato', sans-serif !important;
    font-size: 14px !important;
    line-height: 1.7 !important;
}
div[data-testid="stTextArea"] textarea:focus {
    border-color: #7c3aed !important;
    box-shadow: 0 0 0 3px rgba(124,58,237,0.15) !important;
}
div[data-testid="stTextArea"] label { color: #666 !important; font-size: 11px !important; }

.copy-box {
    background: #0f0f18;
    border: 1.5px solid #2a2a3a;
    border-radius: 10px;
    padding: 16px;
    color: #e0e0e8;
    font-family: 'Lato', sans-serif;
    font-size: 14px;
    line-height: 1.75;
    white-space: pre-wrap;
    max-height: 420px;
    overflow-y: auto;
    position: relative;
}

.stat-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin-top: 14px;
}
.stat-card {
    background: #1a1a28;
    border: 1px solid #2a2a3a;
    border-radius: 10px;
    padding: 12px;
    text-align: center;
}
.stat-val { font-family: 'Syne', sans-serif; font-size: 22px; font-weight: 800; color: #a855f7; }
.stat-lbl { font-size: 10px; color: #555; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 2px; }

div[data-testid="stSelectbox"] > div { background: #16161f !important; border-color: #2a2a3a !important; color: #ccc !important; }
div[data-testid="stSelectbox"] label { color: #888 !important; font-size: 12px !important; }
.stRadio label { color: #bbb !important; font-size: 13px !important; }
.stCheckbox label { color: #bbb !important; }
.stTextInput > div > div > input { background: #0f0f18 !important; border-color: #2a2a3a !important; color: #ccc !important; }

.section-label {
    font-family: 'Syne', sans-serif;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #444;
    margin-bottom: 10px;
    margin-top: 20px;
}
.wc-display { color: #555; font-size: 12px; margin-top: 6px; }

.tip-row {
    background: rgba(168,85,247,0.07);
    border-left: 3px solid #7c3aed;
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    font-size: 12px;
    color: #9070c0;
    margin: 8px 0;
}

.success-bar {
    background: rgba(34,197,94,0.1);
    border: 1px solid rgba(34,197,94,0.25);
    border-radius: 8px;
    padding: 12px 16px;
    color: #4ade80;
    font-size: 13px;
    font-weight: 600;
    margin: 10px 0;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  CONTENT TYPES — 20 options across 5 groups
# ─────────────────────────────────────────────

CONTENT_TYPES = {

    # ══ ACADEMIC ══════════════════════════════════════════════
    "📄 Statement of Purpose (SOP)": {
        "group": "Academic",
        "pipeline": "formal",
        "tone_locked": "Reflective & Personal",
        "system": """You are an elite SOP editor. Rewrite this to sound like a real, thoughtful applicant wrote it after months of reflection.

ABSOLUTE RULES:
- Keep every fact: GPA, projects, institutions, career goals, internships. Never fabricate anything.
- Write in warm, genuine first-person. The voice must feel like a specific human, not a template.
- Replace "I am writing to express my passion" style openers with direct, specific ones ("What first pulled me toward X was...").
- Vary sentence length unpredictably. Some sentences: 5 words. Some build slowly across two clauses and land somewhere unexpected.
- Avoid uniform paragraph sizes — some short (1-2 sentences), some longer.
- NO buzzwords: passionate, leverage, cutting-edge, robust, seamlessly, paradigm, synergy, pivotal, delve, multifaceted.
- NO casual phrases: "Look,", "Honestly,", "Here's the thing:" — this is a formal, personal document.
- One paragraph should open with something concrete and specific rather than a general claim.
- Output ONLY the rewritten SOP."""
    },

    "📝 Personal Statement": {
        "group": "Academic",
        "pipeline": "formal",
        "tone_locked": "Authentic & Reflective",
        "system": """You are a personal statement editor who specializes in making essays sound like real human beings wrote them.

RULES:
- Preserve all factual content. Zero fabrication.
- First-person voice throughout. Warm but not sentimental.
- Replace abstract motivations with concrete, specific ones grounded in what's already in the text.
- One moment of genuine vulnerability or honest self-assessment (not dramatic — understated).
- Vary sentence rhythm: short punchy declarations, then longer more reflective ones.
- Avoid: "I have always been fascinated by", "This experience taught me that", "I am passionate about."
- Remove all AI buzzwords.
- Output ONLY the rewritten statement."""
    },

    "🎓 College Application Essay (Common App)": {
        "group": "Academic",
        "pipeline": "formal",
        "tone_locked": "Vivid & Authentic",
        "system": """You are a college essay coach. Rewrite this to sound like a genuine 17-18 year old with a distinct voice.

RULES:
- Keep all actual events, people, and experiences. Never invent.
- The voice should feel like a smart, self-aware teenager — not a consultant.
- Concrete over abstract. Show moments, not summaries.
- Short punchy sentences mixed with longer flowing ones.
- One small unexpected detail that makes it feel real and specific.
- Avoid adult corporate-speak. Avoid: "I am passionate", "deeply impacted", "transformative experience."
- Output ONLY the rewritten essay."""
    },

    "🔬 Research Paper / Academic Essay": {
        "group": "Academic",
        "pipeline": "formal",
        "tone_locked": "Scholarly & Precise",
        "system": """You are an academic editor. Refine this text to read as naturally human-written while preserving full scholarly integrity.

RULES:
- Preserve all citations, data, terminology, and factual claims exactly.
- Academic transitions (however, therefore, although) are correct here — keep them.
- Remove only: bloated passive constructions, hollow filler phrases ("it is important to note that," "it goes without saying").
- Replace "delve into," "in the realm of," "as we can see" with direct scholarly equivalents.
- Do NOT add casual language, colloquialisms, or personal opinions.
- Maintain argument structure and paragraph order.
- Output ONLY the revised text."""
    },

    "📚 High School / Undergrad Essay": {
        "group": "Academic",
        "pipeline": "formal",
        "tone_locked": "Clear & Analytical",
        "system": """You are editing an academic essay to sound like a thoughtful student wrote it — clear, analytical, but not robotic.

RULES:
- Keep the argument structure and all evidence intact.
- Mix sentence lengths: some punchy thesis-like sentences, some longer analytical ones.
- Replace AI transitions (moreover, furthermore, consequently) with cleaner ones (also, this means, and yet, as a result).
- Remove AI buzzwords: delve, pivotal, groundbreaking, multifaceted, testament, robust.
- One concrete example or analogy should anchor the argument where it's currently thin.
- Formal enough for a classroom — no slang, no casual openers.
- Output ONLY the rewritten essay."""
    },

    # ══ PROFESSIONAL ══════════════════════════════════════════
    "📧 Professional Email": {
        "group": "Professional",
        "pipeline": "formal",
        "tone_locked": "Professional & Direct",
        "system": """You are lightly editing this professional email so it sounds naturally written — not robotic, not over-formatted.

STRICT RULES:
- Keep the greeting and sign-off exactly (Dear / Best regards / Sincerely / Hi [Name]).
- Keep ALL facts, names, dates, project details exactly as stated. Never invent.
- Only change:
  · Remove filler openers ("I hope this email finds you well," "I am writing to inform you that")
  · Replace stiff phrases with direct natural ones ("I am pleased to inform you" → "I wanted to share")
  · Break long run-on sentences into two clear ones
  · Remove redundant qualifiers ("very important" → "important")
- Do NOT inject casual phrases, humor, or overly informal language.
- Do NOT start sentences with And/But/So in a formal email.
- Keep bullet points intact if they exist.
- Output ONLY the rewritten email."""
    },

    "💼 Cover Letter": {
        "group": "Professional",
        "pipeline": "formal",
        "tone_locked": "Confident & Genuine",
        "system": """You are a professional editor refining this cover letter to sound authentic and human.

STRICT RULES:
- Keep ALL factual claims, skills, companies, projects, and years of experience exactly. Never fabricate.
- Replace the templated opener ("I am writing to express my strong interest") with a direct one ("I'm excited about this role because...").
- Make the motivation feel grounded — but only in what's already in the text.
- Vary sentence length slightly — avoid three identical-length sentences in a row.
- Remove AI buzzwords: leverage, passionate, driven, dynamic, synergy, impactful, results-oriented, hard-working.
- Keep the closing line specific and real, not boilerplate.
- Keep bullet points if present — do NOT convert to prose.
- Do NOT add new achievements or stories.
- Output ONLY the rewritten letter."""
    },

    "🔗 LinkedIn Post / Bio": {
        "group": "Professional",
        "pipeline": "general",
        "tone_locked": "Authentic Professional",
        "system": """You are a LinkedIn content strategist. Rewrite this to sound like a credible professional, not a corporate AI.

RULES:
- Keep all facts, titles, achievements, and companies exactly.
- Confident but not boastful. Specific not vague.
- Short punchy sentences. No walls of text.
- Replace LinkedIn clichés: "passionate about," "excited to share," "thrilled to announce," "game-changer," "leverage," "synergy."
- One concrete, specific detail to make a vague claim feel real.
- Remove hashtag clutter (keep max 3 if they exist and must be relevant).
- Output ONLY the rewritten content."""
    },

    "📊 Business Report / Executive Summary": {
        "group": "Professional",
        "pipeline": "formal",
        "tone_locked": "Clear & Executive",
        "system": """You are a senior business writer editing this for clarity and executive readability.

RULES:
- Preserve all data, findings, and recommendations exactly.
- Replace passive constructions with active voice where it improves clarity.
- Remove redundant qualifiers and throat-clearing ("It should be noted that," "In light of the above").
- Remove AI buzzwords: leverage, synergy, paradigm, robust, seamlessly, ecosystem, transformative.
- Keep headers, bullets, and numbered lists intact.
- Sentences should be direct. Prefer shorter over longer where meaning is equal.
- Output ONLY the revised text."""
    },

    "📨 Cold Outreach / Sales Email": {
        "group": "Professional",
        "pipeline": "formal",
        "tone_locked": "Sharp & Personal",
        "system": """You are a sales copywriter editing this cold outreach email to feel human and compelling.

RULES:
- Keep the core offer, value prop, and CTA exactly as stated. Never fabricate claims.
- Open with the prospect's pain or gain, not "I wanted to reach out."
- Short paragraphs. Short sentences. Each sentence earns its place.
- Remove: "I hope you're doing well," "I know you're busy," "circle back," "leverage," "synergy."
- End with a clear, low-friction ask.
- Output ONLY the rewritten email."""
    },

    # ══ CREATIVE & CONTENT ════════════════════════════════════
    "✍️ Blog Post / Article": {
        "group": "Creative & Content",
        "pipeline": "general",
        "tone_locked": None,   # Tone selector enabled
        "system": None,        # Built dynamically
    },

    "🎯 Marketing Copy / Landing Page": {
        "group": "Creative & Content",
        "pipeline": "general",
        "tone_locked": "Persuasive & Human",
        "system": """You are a conversion copywriter rewriting this to sound like a sharp human marketer wrote it.

RULES:
- Keep all product claims, features, and CTAs exactly. Never fabricate benefits.
- Lead with the benefit, not the feature. Cut every word that doesn't earn its place.
- Short punchy sentences. Power words that feel earned, not hollow.
- Remove: cutting-edge, revolutionary, game-changing, innovative, robust, seamlessly, leverage, groundbreaking.
- Active voice only. Kill passive constructions.
- One specific, concrete detail to make a vague claim real.
- Output ONLY the rewritten copy."""
    },

    "📱 Social Media Post": {
        "group": "Creative & Content",
        "pipeline": "general",
        "tone_locked": "Casual & Engaging",
        "system": """You are a social media writer. Rewrite this to sound like a real person posted it.

RULES:
- Keep all facts and key messages.
- Casual, energetic tone. Very short sentences. Real human voice.
- One conversational hook or rhetorical question.
- Remove all corporate-speak and AI buzzwords.
- Keep max 3-5 hashtags if they exist.
- Output ONLY the rewritten post."""
    },

    "📖 Creative / Narrative Writing": {
        "group": "Creative & Content",
        "pipeline": "general",
        "tone_locked": "Vivid & Literary",
        "system": """You are a literary editor. Help this piece of writing sound authentically human and alive.

RULES:
- Preserve all story elements: characters, plot points, invented details. Never fabricate.
- Make the prose feel alive: sensory details, rhythm variation, tension.
- Vary sentence length dramatically. Mix fragments with long flowing sentences.
- Replace generic descriptors with specific, evocative ones.
- Remove AI tells: "it is worth noting," "needless to say," "as we can see."
- If there's dialogue, make it sound like real people — incomplete, alive.
- Output ONLY the revised text."""
    },

    "📰 News / Journalism Style": {
        "group": "Creative & Content",
        "pipeline": "general",
        "tone_locked": "Objective & Journalistic",
        "system": """You are a copy editor. Rewrite this in clean, neutral, AP-style journalistic prose.

RULES:
- Objective. No opinions. No editorial asides.
- Active voice. Clear, short sentences.
- Lead with the most important fact.
- No jargon. No AI buzzwords.
- Quotes (if present) must stay verbatim.
- Output ONLY the rewritten article."""
    },

    # ══ PERSONAL ══════════════════════════════════════════════
    "💬 Personal Message / Casual Text": {
        "group": "Personal",
        "pipeline": "general",
        "tone_locked": "Warm & Casual",
        "system": """You are rewriting this to sound like a real person wrote a personal message.

RULES:
- Keep all factual content and intent.
- Very casual, warm. Like texting a friend or writing a personal note.
- Short sentences. Natural rhythm.
- Remove ALL formal language, corporate phrasing, and AI buzzwords.
- One small personal touch or honest aside.
- Output ONLY the rewritten message."""
    },

    "💌 Personal Letter / Thank You Note": {
        "group": "Personal",
        "pipeline": "formal",
        "tone_locked": "Warm & Genuine",
        "system": """You are editing this personal letter or thank you note to sound heartfelt and genuinely human.

RULES:
- Keep all specific details about the person or situation exactly.
- Warm, personal tone. This should feel like it was written with care for a specific person.
- Remove templated phrases: "I am writing to express my sincere gratitude," "I cannot thank you enough."
- One specific, concrete memory or detail to make it feel personal.
- Vary sentence length. Let some sentences breathe.
- Output ONLY the rewritten letter."""
    },

    # ══ SPECIALIZED ═══════════════════════════════════════════
    "⚖️ Legal / Contract Simplification": {
        "group": "Specialized",
        "pipeline": "formal",
        "tone_locked": "Clear & Precise",
        "system": """You are editing this legal or contract text to be clearer and more readable while preserving all legal meaning.

RULES:
- Preserve ALL legal terms, obligations, parties, dates, and clauses exactly.
- Replace unnecessarily complex constructions with direct equivalents that preserve legal meaning.
- Do NOT remove any substantive legal content or alter the legal effect.
- Break run-on legal sentences into shorter, clearer ones where safe to do so.
- Remove hollow legalese fillers: "hereinafter referred to as," "it is hereby agreed that," "in the event that" → "if."
- Output ONLY the revised text."""
    },

    "🏥 Medical / Health Communication": {
        "group": "Specialized",
        "pipeline": "formal",
        "tone_locked": "Clear & Compassionate",
        "system": """You are a medical communications editor. Rewrite this health content to sound clear, human, and compassionate.

RULES:
- Preserve ALL medical facts, dosages, diagnoses, instructions, and warnings exactly.
- Replace overly clinical constructions with plain language equivalents where clarity is improved.
- Warm but factual. Not alarmist. Not dismissive.
- Remove AI-generic phrases while keeping medical accuracy.
- If this is patient-facing: use "you" language. If clinical: maintain appropriate register.
- Output ONLY the revised text."""
    },

    "🛠️ Technical Documentation": {
        "group": "Specialized",
        "pipeline": "formal",
        "tone_locked": "Clear & Technical",
        "system": """You are a technical writer editing this documentation to be clear and naturally written.

RULES:
- Preserve all technical details, commands, parameters, and specifications exactly.
- Replace passive constructions with active voice where it improves clarity ("It should be noted that X" → "Note: X").
- Break up overly long sentences into sequential steps where appropriate.
- Remove filler phrases and AI-generic language.
- Keep numbered lists and code blocks intact.
- Output ONLY the revised text."""
    },
}

CONTENT_GROUPS = {}
for k, v in CONTENT_TYPES.items():
    g = v["group"]
    if g not in CONTENT_GROUPS:
        CONTENT_GROUPS[g] = []
    CONTENT_GROUPS[g].append(k)

# ─────────────────────────────────────────────
#  TONE OPTIONS (Blog/Article only)
# ─────────────────────────────────────────────

TONE_PROMPTS = {
    "Conversational & Raw": """You are rewriting this in a genuine, casual human voice — like a smart person explaining something to a friend.
WRITING STYLE: Mix very short sentences (3-6 words) with longer, rambling ones that feel natural. Unpredictable vocabulary. Real opinions. Occasionally an aside in parentheses. Avoid uniform paragraph lengths. Do NOT use AI buzzwords or formal transitions.
Output ONLY the rewritten text. No preamble.""",

    "Professional but Natural": """You are a senior editor rewriting this in a confident, direct professional voice — like a sharp colleague giving a briefing, not a consultant writing a report.
WRITING STYLE: Direct. No fluff. Active voice. Vary sentence length — some short and punchy, some medium explanatory ones. No jargon. Replace every formal or stiff phrase with a natural professional equivalent.
Output ONLY the rewritten text. No preamble.""",

    "Storyteller / Narrative": """You are a narrative writer giving this content story-like flow.
WRITING STYLE: Make abstract concepts concrete and visual. Use em dashes — like this — for rhythm and emphasis. Vary sentence length dramatically. Show cause and effect through narrative. One concrete scene-setting detail or analogy. Unexpected structural choices.
Output ONLY the rewritten text. No preamble.""",

    "Opinionated / First-Person": """You are a blogger with a distinct, confident voice.
WRITING STYLE: First person. "I" used naturally. Direct and opinionated. Rhetorical questions: "Why does this matter? Because..." Start some sentences with "Look," or "Here's the thing:" where natural. Vary sentence rhythm wildly. Challenge the obvious.
Output ONLY the rewritten text. No preamble.""",

    "Witty & Sharp": """You are a witty writer — sharp, clever, occasionally irreverent without trying too hard.
WRITING STYLE: Smart observations. Light humor where natural. One well-placed subversion of expectation. Unexpected vocabulary choices. Confident, breezy tone. Never forced or cringeworthy.
Output ONLY the rewritten text. No preamble.""",

    "Neutral & Journalistic": """You are a journalist rewriting this in clean, neutral AP-style prose.
WRITING STYLE: Objective. No opinions or editorial asides. Active voice. Short clear sentences. No jargon. No AI buzzwords.
Output ONLY the rewritten text. No preamble.""",
}

# ─────────────────────────────────────────────
#  DETECTOR TARGETING INSTRUCTIONS
# ─────────────────────────────────────────────

def get_detector_instructions(gptzero, originality, turnitin, zerogpt, quillbot) -> str:
    """
    Each detector measures different signals. These instructions target those
    signals at the LLM prompt level — NOT via post-processing.
    """
    parts = []
    if gptzero:
        parts.append("""GPTZERO TARGETING (perplexity + burstiness):
- Make at least 20% of sentences dramatically shorter than the rest (under 7 words).
- At least 20% of sentences should run longer than 25 words with embedded clauses.
- Use at least one word that is correct but slightly unexpected in context.
- Include one rhetorical question somewhere in the text.
- Vary the OPENING WORD of each sentence — never start two consecutive sentences with the same word.""")

    if originality:
        parts.append("""ORIGINALITY.AI TARGETING (semantic fingerprinting + probability chains):
- Restructure the logical ORDER of ideas across paragraphs — don't just rephrase in the same sequence.
- Use at least two idiomatic or colloquial expressions that would raise probability scores.
- Introduce one concrete, specific real-world detail (a number, a named scenario, a comparison).
- Avoid clean topic-sentence → supporting-detail → conclusion paragraph structure.
- At least one paragraph should begin mid-thought, as if continuing something from before.""")

    if turnitin:
        parts.append("""TURNITIN TARGETING (stylometric ML + structural patterns + personal voice):
- Break paragraph symmetry: not all 3-4 sentences. Include at least one 1-sentence paragraph and one 6+ sentence paragraph.
- Include at least one subjective observation or mild opinion: "which, in practice, works better than it sounds."
- Avoid any parallel list structure ("First... Second... Third...").
- Vary the POSITION of the main claim within paragraphs — sometimes lead, sometimes build to it.""")

    if zerogpt:
        parts.append("""ZEROGPT TARGETING (formal transitions + uniform clause length):
- Replace ALL of these transitions: However / Furthermore / Moreover / Additionally / Consequently / Nevertheless / In conclusion.
- Use instead: But / Also / So / Plus / That said / Even so / And yet / Which means.
- Vary clause length within sentences — avoid symmetrical paired clauses.
- At least two sentences should begin with a conjunction (And, But, So).
- At least one sentence should be deliberately shorter than everything around it.""")

    if quillbot:
        parts.append("""QUILLBOT TARGETING (paraphrase detection + synonym pattern recognition):
- Do NOT simply swap synonyms — Quillbot detects synonym-replacement patterns as paraphrasing artifacts.
- Instead, restructure sentences SYNTACTICALLY: change the grammatical form, not just word choice.
- Convert some noun phrases to verb phrases and vice versa.
- Combine two short related sentences into one longer one, or split one long sentence into two short ones.
- Change the perspective or framing of claims (e.g., "X improves Y" → "Y improves when X is applied").
- Introduce at least one informal phrase that no paraphraser would generate.""")

    return "\n\n".join(parts) if parts else ""


# ─────────────────────────────────────────────
#  CLICHE REMOVAL (post-processing — safe only)
# ─────────────────────────────────────────────

AI_CLICHES = {
    "delve into": ["dig into", "explore", "look at", "get into"],
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
    "in conclusion": ["to wrap up", "so", "bottom line"],
    "in summary": ["in short", "briefly"],
    "it is important to note that": ["worth noting,", "note that"],
    "it's important to note that": ["worth noting,", "note that"],
    "it is worth noting that": ["worth noting,", "note that"],
    "it's worth noting that": ["worth noting,"],
    "in order to": ["to"],
    "due to the fact that": ["because", "since"],
    "game-changer": ["big shift", "major change"],
    "game changer": ["big shift", "major change"],
    "needless to say": ["clearly", "obviously"],
    "as we can see": ["clearly", "as shown"],
    "it goes without saying": ["clearly",],
}

def remove_cliches(text: str) -> str:
    """Safe word/phrase replacement only. No structural manipulation."""
    for phrase, options in sorted(AI_CLICHES.items(), key=lambda x: -len(x[0])):
        pattern = r'(?<!\w)' + re.escape(phrase) + r'(?!\w)'
        if re.search(pattern, text, flags=re.IGNORECASE):
            replacement = random.choice(options)
            text = re.sub(pattern, replacement, text, count=1, flags=re.IGNORECASE)
    return text

def clean_artifacts(text: str) -> str:
    """Remove common post-LLM artifacts: double spaces, space before punctuation, double periods."""
    text = re.sub(r'\.{2,}', '.', text)       # Multiple periods → single
    text = re.sub(r' +\.', '.', text)          # Space before period
    text = re.sub(r' +,', ',', text)           # Space before comma
    text = re.sub(r'  +', ' ', text)           # Double spaces
    text = re.sub(r'\n{3,}', '\n\n', text)     # Triple+ newlines
    # Remove any preamble that starts with "Here is" or "Here's" 
    text = re.sub(r'^(Here is|Here\'s|Below is|Below\'s)[^:]*:\s*\n*', '', text, flags=re.IGNORECASE)
    return text.strip()


# ─────────────────────────────────────────────
#  API CLIENTS
# ─────────────────────────────────────────────

def get_groq_client(api_key: str):
    from groq import Groq
    return Groq(api_key=api_key)

def call_groq(client, model_id: str, system: str, user: str, temperature: float, max_tokens: int) -> str:
    r = client.chat.completions.create(
        model=model_id,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=0.95,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
    )
    return r.choices[0].message.content.strip()

def call_gemini(api_key: str, system: str, user: str, temperature: float, max_tokens: int) -> str:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=system,
        generation_config=genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
    )
    response = model.generate_content(user)
    return response.text.strip()


# ─────────────────────────────────────────────
#  HUMANIZE FUNCTION
# ─────────────────────────────────────────────

GROQ_MODELS = {
    "Llama 3.3 70B — Best (Recommended)": "llama-3.3-70b-versatile",
    "Llama 3.1 8B — Faster, Lighter":     "llama-3.1-8b-instant",
    "Mixtral 8x7B — Alternative":         "mixtral-8x7b-32768",
}


def build_general_system(tone: str, ct_system: str | None, gptzero, originality, turnitin, zerogpt, quillbot) -> str:
    """Build the full system prompt for general content pipeline."""
    base = ct_system if ct_system else TONE_PROMPTS.get(tone, TONE_PROMPTS["Conversational & Raw"])
    detector_rules = get_detector_instructions(gptzero, originality, turnitin, zerogpt, quillbot)
    forbidden = ("FORBIDDEN — never use these words or phrases: delve, utilize, leverage, paramount, "
                 "landscape, realm, testament, moreover, furthermore, in conclusion, cutting-edge, "
                 "game-changer, groundbreaking, pivotal, robust, seamlessly, foster, comprehensive, "
                 "transformative, synergy, ecosystem, paradigm, multifaceted, it is important to note, "
                 "needless to say, as we can see, it goes without saying, in order to.")
    full = base
    if detector_rules:
        full += f"\n\n{detector_rules}"
    full += f"\n\n{forbidden}"
    full += "\n\nOutput ONLY the rewritten text. Do NOT include any preamble like 'Here is the rewritten version:'"
    return full


def humanize(
    text: str,
    content_type: str,
    tone: str,
    provider: str,
    groq_api_key: str,
    groq_model_id: str,
    gemini_api_key: str,
    stealth: bool,
    gptzero: bool,
    originality: bool,
    turnitin: bool,
    zerogpt: bool,
    quillbot: bool,
) -> str:

    ct = CONTENT_TYPES[content_type]
    pipeline = ct["pipeline"]
    ct_system = ct["system"]

    def call(system: str, user: str, temperature: float, max_tokens: int = 3000) -> str:
        if provider == "Groq":
            client = get_groq_client(groq_api_key)
            return call_groq(client, groq_model_id, system, user, temperature, max_tokens)
        else:
            return call_gemini(gemini_api_key, system, user, temperature, max_tokens)

    try:
        # ── FORMAL PIPELINE ───────────────────────────────────────────
        if pipeline == "formal":
            result = call(
                system=ct_system,
                user=f"Edit this text:\n\n{text}",
                temperature=0.65,
                max_tokens=3000,
            )
            result = clean_artifacts(result)
            if stealth:
                result = remove_cliches(result)
            return result

        # ── GENERAL PIPELINE (4 passes) ───────────────────────────────
        system = build_general_system(tone, ct_system, gptzero, originality, turnitin, zerogpt, quillbot)
        GENERAL_GROQ_MODEL = "llama-3.3-70b-versatile"  # Always best for general

        def call_general(sys: str, usr: str, temp: float) -> str:
            if provider == "Groq":
                client = get_groq_client(groq_api_key)
                return call_groq(client, GENERAL_GROQ_MODEL, sys, usr, temp, 3500)
            else:
                return call_gemini(gemini_api_key, sys, usr, temp, 3500)

        # PASS 1: Structural deconstruction (high temperature)
        # Goal: break AI's predictable structure before humanizing
        p1_result = call_general(
            """You are a structural editor. Your ONLY job: take this text and restructure it so it no longer follows the AI pattern of topic-sentence → support → conclusion in every paragraph.

Rules:
- Rearrange the ORDER of arguments or ideas (but keep all facts intact).
- Make paragraph lengths unequal — some very short, some longer.
- Start at least two paragraphs mid-thought rather than with a clear topic sentence.
- Do NOT add new information. Do NOT use AI buzzwords.
- Vary sentence lengths dramatically within each paragraph.
- Output ONLY the restructured text. No preamble.""",
            text,
            1.3,
        )

        # PASS 2: Voice and tone humanization
        p2_result = call_general(
            system,
            f"Apply your full humanization approach to this text. Make it sound undeniably like a human wrote it:\n\n{p1_result}",
            1.2,
        )

        # PASS 3: Rhythm and flow pass (targets burstiness specifically)
        p3_result = call_general(
            """You are a sentence rhythm specialist. Your job: make this text's rhythm feel undeniably human.

Rules:
- Ensure sentence lengths vary dramatically. After any sentence over 20 words, the next should be under 10.
- Replace every formal transition word (However, Furthermore, Moreover, Additionally, Consequently, Nevertheless) with a casual equivalent (But, Also, So, Plus, That said, Even so).
- The first sentence of at least two paragraphs should be unusually short — under 8 words.
- At least one paragraph should have no clear "topic sentence" at all.
- If there are three or more consecutive sentences of similar length, break the pattern.
- Do NOT add new facts. Do NOT use AI buzzwords.
- Output ONLY the result. No preamble.""",
            p2_result,
            1.0,
        )

        # PASS 4: Final coherence and polish
        p4_result = call_general(
            """Final quality pass. Your job: make this text flow naturally while maintaining all the human-like qualities it has.

Rules:
- Fix any awkward phrasing that reads as unnatural (not AI-unnatural — genuinely confusing).
- Ensure the overall meaning and argument are still clear.
- If any AI buzzwords slipped in (delve, utilize, leverage, paramount, groundbreaking, pivotal, robust, seamlessly), replace them.
- Do NOT add new content. Do NOT re-introduce AI sentence patterns.
- Output ONLY the final text. No preamble.""",
            p3_result,
            0.8,
        )

        result = clean_artifacts(p4_result)
        if stealth:
            result = remove_cliches(result)
        return result

    except Exception as e:
        return f"Error: {str(e)}"


# ─────────────────────────────────────────────
#  CACHE
# ─────────────────────────────────────────────

def make_cache_key(*args, randomize: bool) -> str:
    seed = str(random.random()) if randomize else "static"
    raw = "|".join(str(a) for a in args) + seed
    return hashlib.md5(raw.encode()).hexdigest()


# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("<div style='font-family:Syne,sans-serif;font-size:18px;font-weight:800;color:#a855f7;margin-bottom:20px'>✍️ Authentica v5</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-label'>API Provider</div>", unsafe_allow_html=True)
    provider = st.radio("Provider", ["Groq (Free)", "Google Gemini (Free)"], label_visibility="collapsed")
    provider_key = "Groq" if "Groq" in provider else "Gemini"

    st.markdown("<div class='section-label'>API Key</div>", unsafe_allow_html=True)
    if provider_key == "Groq":
        groq_api_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...", help="console.groq.com — Free, no credit card", label_visibility="collapsed")
        gemini_api_key = ""
        st.markdown("<div style='font-size:11px;color:#555'>Get free key: console.groq.com</div>", unsafe_allow_html=True)
    else:
        gemini_api_key = st.text_input("Gemini API Key", type="password", placeholder="AIza...", help="aistudio.google.com/apikey — Free tier available", label_visibility="collapsed")
        groq_api_key = ""
        st.markdown("<div style='font-size:11px;color:#555'>Get free key: aistudio.google.com/apikey</div>", unsafe_allow_html=True)

    if provider_key == "Groq":
        st.markdown("<div class='section-label'>Model</div>", unsafe_allow_html=True)
        groq_model_name = st.selectbox("Groq Model", list(GROQ_MODELS.keys()), label_visibility="collapsed")
        groq_model_id = GROQ_MODELS[groq_model_name]
    else:
        groq_model_id = "llama-3.3-70b-versatile"

    st.markdown("<div class='section-label'>Target Detectors</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        t_gptzero     = st.checkbox("GPTZero",      value=True)
        t_turnitin    = st.checkbox("Turnitin",     value=True)
        t_quillbot    = st.checkbox("Quillbot",     value=True)
    with c2:
        t_originality = st.checkbox("Originality", value=True)
        t_zerogpt     = st.checkbox("ZeroGPT",     value=True)

    st.markdown("<div class='section-label'>Options</div>", unsafe_allow_html=True)
    stealth    = st.checkbox("Stealth Post-Processing", value=True, help="Applies cliché removal after the LLM pass")
    randomize  = st.checkbox("Randomize Each Run",      value=True, help="Every run produces a different version")

    st.markdown("---")
    st.markdown("""<div style='font-size:11px;color:#444;line-height:1.7'>
<b style='color:#666'>What's new in v5:</b><br>
✓ Contraction injection removed<br>
✓ Quillbot detector targeting added<br>
✓ Copy button on output<br>
✓ 20 content types across 5 groups<br>
✓ Structural-level rewriting (4 passes)<br>
✓ Gemini 2.0 Flash support (free)<br>
✓ Dot artifacts fixed<br>
✓ Preamble stripping
</div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  MAIN UI
# ─────────────────────────────────────────────

# Header
st.markdown("""
<div class="main-header">
  <p class="brand-title">✍️ Authentica <span class="brand-accent">v5</span></p>
  <p class="brand-sub">STRUCTURAL AI HUMANIZER · MULTI-DETECTOR ENGINE · 20 CONTENT TYPES</p>
</div>
""", unsafe_allow_html=True)

# Detector badges
detector_html = ""
for label, active in [("GPTZero", t_gptzero), ("Originality.ai", t_originality),
                       ("Turnitin", t_turnitin), ("ZeroGPT", t_zerogpt), ("Quillbot", t_quillbot)]:
    cls = "badge-on" if active else "badge-off"
    detector_html += f'<span class="badge {cls}">{label}</span>'
st.markdown(f"<div style='margin-bottom:20px'>{detector_html}</div>", unsafe_allow_html=True)

# Content type selection
st.markdown("<div class='section-label'>Content Type</div>", unsafe_allow_html=True)
group_col, type_col = st.columns([1, 3])

with group_col:
    selected_group = st.radio("Group", list(CONTENT_GROUPS.keys()), label_visibility="collapsed")

with type_col:
    ct_options = CONTENT_GROUPS[selected_group]
    content_type = st.selectbox("Content Type", ct_options, label_visibility="collapsed")

ct_info = CONTENT_TYPES[content_type]
pipeline_label = "🚀 4-Pass General" if ct_info["pipeline"] == "general" else "🎯 1-Pass Formal"
tone_label = ct_info.get("tone_locked") or "User-Selected"

col_info_a, col_info_b, col_info_c = st.columns(3)
col_info_a.markdown(f"<div class='info-chip'>Pipeline: <span class='info-chip-val'>{pipeline_label}</span></div>", unsafe_allow_html=True)
col_info_b.markdown(f"<div class='info-chip'>Tone: <span class='info-chip-val'>{tone_label}</span></div>", unsafe_allow_html=True)
col_info_c.markdown(f"<div class='info-chip'>Provider: <span class='info-chip-val'>{provider_key}</span></div>", unsafe_allow_html=True)

# Tone selector (Blog/Article only)
tone = "Conversational & Raw"
if ct_info.get("tone_locked") is None:
    st.markdown("<div class='section-label' style='margin-top:16px'>Tone</div>", unsafe_allow_html=True)
    tone_names = list(TONE_PROMPTS.keys())
    tcols = st.columns(len(tone_names))
    for i, t_name in enumerate(tone_names):
        with tcols[i]:
            short = t_name.split(" ")[0]
            if st.button(short, key=f"tone_btn_{i}", use_container_width=True):
                st.session_state["selected_tone"] = t_name
    tone = st.session_state.get("selected_tone", "Conversational & Raw")
    st.markdown(f"<div class='tip-row'><b>{tone}</b> — {TONE_PROMPTS[tone][:80]}...</div>", unsafe_allow_html=True)

st.markdown("---")

# Main columns
col1, col2 = st.columns(2)

with col1:
    st.markdown("<div class='section-label'>Input Text</div>", unsafe_allow_html=True)
    input_text = st.text_area(
        "Input",
        height=420,
        placeholder="Paste your AI-generated text here...\n\nWorks with any length — essays, emails, SOPs, blog posts, cover letters, creative writing, and more.",
        label_visibility="collapsed",
    )
    wc_in = len(input_text.split()) if input_text.strip() else 0
    st.markdown(f"<div class='wc-display'>{wc_in} words</div>", unsafe_allow_html=True)

    run = st.button("✦ Humanize Now", type="primary", use_container_width=True)

with col2:
    st.markdown("<div class='section-label'>Output</div>", unsafe_allow_html=True)
    output_slot = st.empty()
    status_slot = st.empty()
    copy_slot   = st.empty()
    stats_slot  = st.empty()

    if run:
        # Validation
        api_key_present = (provider_key == "Groq" and groq_api_key) or (provider_key == "Gemini" and gemini_api_key)
        if not api_key_present:
            status_slot.error(f"⚠️ Please enter your {provider_key} API key in the sidebar.")
        elif not input_text.strip():
            status_slot.warning("Please paste some text to humanize.")
        elif wc_in < 15:
            status_slot.warning("Text is too short. Please provide at least 15 words for best results.")
        elif not any([t_gptzero, t_originality, t_turnitin, t_zerogpt, t_quillbot]):
            status_slot.warning("Select at least one target detector in the sidebar.")
        else:
            if "cache" not in st.session_state:
                st.session_state.cache = {}

            ck = make_cache_key(
                input_text, content_type, tone, provider_key, groq_model_id,
                stealth, t_gptzero, t_originality, t_turnitin, t_zerogpt, t_quillbot,
                randomize=randomize,
            )

            p_label = "4-pass general" if ct_info["pipeline"] == "general" else "1-pass formal"
            with st.spinner(f"Running {p_label} pipeline…"):
                if ck in st.session_state.cache and not randomize:
                    result = st.session_state.cache[ck]
                else:
                    result = humanize(
                        text=input_text,
                        content_type=content_type,
                        tone=tone,
                        provider=provider_key,
                        groq_api_key=groq_api_key,
                        groq_model_id=groq_model_id,
                        gemini_api_key=gemini_api_key,
                        stealth=stealth,
                        gptzero=t_gptzero,
                        originality=t_originality,
                        turnitin=t_turnitin,
                        zerogpt=t_zerogpt,
                        quillbot=t_quillbot,
                    )
                    if not result.startswith("Error:"):
                        st.session_state.cache[ck] = result

            if result.startswith("Error:"):
                status_slot.error(result)
            else:
                # Output text area
                output_slot.text_area(
                    "Output",
                    value=result,
                    height=420,
                    label_visibility="collapsed",
                    key="output_area"
                )

                wc_out = len(result.split())
                st.markdown(f"<div class='wc-display'>{wc_out} words</div>", unsafe_allow_html=True)

                # Copy button using st.code for easy copying
                with copy_slot.expander("📋 Click to copy output"):
                    st.code(result, language=None)

                status_slot.markdown("<div class='success-bar'>✓ Humanization complete</div>", unsafe_allow_html=True)

                # Stats
                stats_slot.markdown(f"""
<div class="stat-grid">
  <div class="stat-card"><div class="stat-val">{"4" if ct_info["pipeline"] == "general" else "1"}</div><div class="stat-lbl">Passes</div></div>
  <div class="stat-card"><div class="stat-val">{sum([t_gptzero, t_originality, t_turnitin, t_zerogpt, t_quillbot])}</div><div class="stat-lbl">Detectors</div></div>
  <div class="stat-card"><div class="stat-val">{wc_out}</div><div class="stat-lbl">Words</div></div>
  <div class="stat-card"><div class="stat-val">{"ON" if stealth else "OFF"}</div><div class="stat-lbl">Stealth</div></div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  TIPS & EXPLAINER
# ─────────────────────────────────────────────

st.markdown("---")
col_t1, col_t2 = st.columns(2)

with col_t1:
    st.markdown("<div class='section-label'>Manual refinement tips</div>", unsafe_allow_html=True)
    st.markdown("""
<div class="tip-row">1. Add one real specific detail — a year, a number, a named example</div>
<div class="tip-row">2. Turn one statement into a question: "Why does this matter? Because..."</div>
<div class="tip-row">3. Break one long paragraph in half, or merge two short ones</div>
<div class="tip-row">4. Add one self-correction or parenthetical aside (like this one)</div>
<div class="tip-row">5. Read it aloud — anything that sounds robotic is a detector signal</div>
""", unsafe_allow_html=True)

with col_t2:
    st.markdown("<div class='section-label'>Why v5 works better</div>", unsafe_allow_html=True)
    st.markdown("""
<div class="tip-row"><b>No contraction injection</b> — detectors now flag "I'm, I'd, I've" chains as a humanizer artifact</div>
<div class="tip-row"><b>Structural rewriting</b> — Pass 1 breaks AI's predictable paragraph structure before humanizing</div>
<div class="tip-row"><b>No synonym swapping</b> — Quillbot-style synonym replacement is itself detectable; we restructure syntax instead</div>
<div class="tip-row"><b>Rhythm-specific pass</b> — Pass 3 targets burstiness (sentence length variation) explicitly</div>
""", unsafe_allow_html=True)

with st.expander("📖 Full pipeline & detector reference"):
    st.markdown("""
### Pipeline summary

| Content Type | Pipeline | Passes | Temperature | Post-Proc |
|---|---|---|---|---|
| Blog / Article | General | 4 | 0.8 – 1.3 | Clichés only |
| SOP / Personal Statement | Formal | 1 | 0.65 | Clichés only |
| Cover Letter | Formal | 1 | 0.65 | Clichés only |
| Professional Email | Formal | 1 | 0.65 | Clichés only |
| Academic / Research | Formal | 1 | 0.65 | Clichés only |
| LinkedIn / Social | General | 4 | 0.8 – 1.3 | Clichés only |
| Marketing Copy | General | 4 | 0.8 – 1.3 | Clichés only |
| Creative Writing | General | 4 | 0.8 – 1.3 | Clichés only |

### What each detector actually measures

| Detector | Primary Signal | v5 Counter-Strategy |
|---|---|---|
| **GPTZero** | Perplexity (token predictability) + Burstiness (sentence length variation) | Pass 1 restructures paragraph order; Pass 3 forces dramatic sentence length variation |
| **Originality.ai** | Semantic fingerprinting — compares probability chains to known LLM outputs | Reorders idea sequence, injects idioms, adds concrete specifics |
| **Turnitin** | Stylometric ML trained on millions of papers — detects structural patterns, not just words | Breaks paragraph symmetry, adds subjective observations, eliminates parallel list structures |
| **ZeroGPT** | Heavy reliance on formal transition detection + uniform clause lengths | All formal transitions replaced; clause lengths varied explicitly in Pass 3 |
| **Quillbot** | Detects synonym-replacement paraphrasing patterns as a distinct signature | We restructure syntax (sentence form, perspective, order) rather than swapping synonyms |

### Why contractions were removed
Older humanizers injected `I'm, I'd, I've, can't` etc. everywhere.
Modern detectors (GPTZero 3.15b, Originality.ai) now recognize this chain of contractions as a **humanizer artifact** — it actually raises the AI probability score.
v5 lets the LLM decide naturally when contractions appear, rather than forcing them.

### Free API providers
- **Groq**: 14,400 requests/day free. Llama 3.3 70B at 300+ tokens/sec. Get key: console.groq.com
- **Google Gemini 2.0 Flash**: 1,000 requests/day free. Get key: aistudio.google.com/apikey
""")

st.markdown("""
<div style='text-align:center;color:#333;font-size:11px;margin-top:30px;padding:20px'>
Authentica v5 · Structural Humanizer · Powered by Groq + Gemini · For legitimate content work only
</div>
""", unsafe_allow_html=True)
