import streamlit as st
from groq import Groq
import hashlib
import re
import random

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Authentica v4 | AI Humanizer",
    page_icon="🖊️",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Serif+Display&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}
h1, h2, h3 {
    font-family: 'DM Serif Display', serif;
}

.main { background: #f8f7f4; }

.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.03em;
    margin: 2px;
}
.badge-active   { background: #1a1a2e; color: #fff; }
.badge-inactive { background: #e8e8e8; color: #888; }

.pipeline-card {
    background: #fff;
    border: 1px solid #e5e5e5;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 12px;
}
.pipeline-title {
    font-weight: 600;
    font-size: 14px;
    color: #1a1a2e;
    margin-bottom: 4px;
}
.pipeline-desc {
    font-size: 12px;
    color: #888;
}

.stButton > button {
    background: #1a1a2e !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-family: 'DM Sans', sans-serif !important;
    letter-spacing: 0.02em !important;
}
.stButton > button:hover {
    background: #2d2d50 !important;
}

div[data-testid="stTextArea"] textarea {
    border-radius: 10px;
    border: 1.5px solid #e0e0e0;
    font-family: 'DM Sans', sans-serif;
    font-size: 14px;
}
div[data-testid="stTextArea"] textarea:focus {
    border-color: #1a1a2e;
    box-shadow: 0 0 0 2px rgba(26,26,46,0.1);
}

.tip-card {
    background: #eef2ff;
    border-left: 4px solid #1a1a2e;
    border-radius: 6px;
    padding: 12px 16px;
    font-size: 13px;
    color: #333;
    margin: 10px 0;
}

.stat-row {
    display: flex;
    gap: 12px;
    margin-top: 8px;
}
.stat-box {
    flex: 1;
    background: #f0f0f5;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: center;
}
.stat-value { font-size: 20px; font-weight: 700; color: #1a1a2e; }
.stat-label { font-size: 11px; color: #888; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  CONTENT TYPE DEFINITIONS
# ─────────────────────────────────────────────

CONTENT_TYPES = {
    # ── Academic ──────────────────────────────
    "📄 Statement of Purpose (SOP)": {
        "group": "Academic",
        "pipeline": "formal",
        "desc": "Graduate school / university admission",
        "tone_locked": "Reflective & Personal",
        "system_prompt": """You are an expert SOP editor. Your job is to make this Statement of Purpose sound authentically human — like a real applicant wrote it after deep reflection.

STRICT RULES — follow every one:
1. Keep ALL facts, credentials, GPA, research projects, internships, and career goals exactly as stated. NEVER fabricate anything.
2. Write in warm first-person voice. Use "I" naturally throughout.
3. Add genuine-sounding personal motivation — but ONLY if it can be inferred from existing content. Never invent experiences.
4. Replace stiff, templated openers ("I am writing to express my strong interest") with direct, human ones ("What drew me to X was…").
5. Vary sentence length: some short punchy ones, some longer reflective ones.
6. Add one concrete detail or analogy to make an abstract goal feel real.
7. Use contractions sparingly where natural (I'm, I've, I'd).
8. Remove ALL AI buzzwords: passionate, delve, leverage, cutting-edge, robust, seamlessly, pivotal, groundbreaking.
9. Do NOT add casual phrases like "Look," "Here's the thing," "Honestly" — this is a formal document.
10. Preserve paragraph structure and logical flow.
11. Output ONLY the rewritten SOP."""
    },

    "📝 College Application Essay": {
        "group": "Academic",
        "pipeline": "formal",
        "desc": "Personal statements for undergrad admission",
        "tone_locked": "Authentic & Narrative",
        "system_prompt": """You are an expert college essay editor helping students sound genuinely themselves.

STRICT RULES:
1. Keep ALL factual content — events, names, experiences — exactly as written. Never invent or embellish.
2. Write in a vivid, authentic first-person voice appropriate for a 17-18 year old.
3. Make the narrative arc feel personal: show, don't tell.
4. Vary sentence lengths dramatically — mix 3-word punchy sentences with longer flowing ones.
5. Avoid adult corporate-speak. This should sound like a smart student, not a consultant.
6. Replace generic reflections ("This experience taught me…") with specific, personal ones when possible.
7. Contractions are natural and expected here.
8. Avoid: delve, utilize, leverage, paramount, testament, multifaceted, in conclusion.
9. Do NOT add experiences or emotions not implied by the original.
10. Output ONLY the rewritten essay."""
    },

    "🔬 Research Paper / Academic Essay": {
        "group": "Academic",
        "pipeline": "formal",
        "desc": "Journal articles, dissertations, academic writing",
        "tone_locked": "Scholarly & Precise",
        "system_prompt": """You are an academic editor refining this research text to sound naturally human-written while preserving full scholarly integrity.

STRICT RULES:
1. Preserve ALL citations, data, statistics, methodology, and technical terminology exactly.
2. Academic transitions (however, therefore, furthermore) are APPROPRIATE here — keep them.
3. Fix only: overly passive constructions, bloated sentence structures, repetitive phrasing.
4. Do NOT add contractions, casual language, or personal opinions.
5. Replace only the most glaring AI phrases: "it is important to note," "delve into," "in the realm of," "as we can see."
6. Preserve the argument structure, paragraph order, and section flow.
7. Do NOT add new claims or analysis.
8. Output ONLY the revised text."""
    },

    "📚 High School / College Essay": {
        "group": "Academic",
        "pipeline": "general",
        "desc": "Academic essays, argumentative papers",
        "tone_locked": "Clear & Analytical",
        "system_prompt": """You are editing an academic essay to sound like a smart student wrote it — not an AI.

RULES:
1. Maintain academic tone: formal enough for a classroom, but not robotic.
2. Keep the argument structure and all factual claims intact.
3. Vary sentence length — mix short direct claims with longer analytical sentences.
4. Replace formal AI transitions (moreover, furthermore, consequently) with cleaner equivalents (also, this means, as a result, but).
5. Add one concrete example or analogy to support the argument where it's thin.
6. Avoid contractions in formal arguments but allow them in topic sentences.
7. Remove AI buzzwords: delve, pivotal, groundbreaking, multifaceted, testament.
8. Output ONLY the rewritten essay."""
    },

    # ── Professional ──────────────────────────
    "📧 Professional Email": {
        "group": "Professional",
        "pipeline": "formal",
        "desc": "Work emails, client communication",
        "tone_locked": "Professional & Direct",
        "system_prompt": """You are a professional editor lightly editing this email to sound naturally human-written.

STRICT RULES:
1. Keep the formal greeting and sign-off exactly (Dear / Best regards / Sincerely). Do NOT change to "Hey".
2. Keep ALL factual claims, names, dates, and project details exactly as stated. NEVER invent anything.
3. Make ONLY these changes:
   - Replace stiff phrases ("I am writing to inform you") with direct equivalents ("I wanted to share")
   - Add contractions where natural (I am → I'm, I would → I'd, I have → I've)
   - Break up overly long run-on sentences into two clear ones
   - Remove throat-clearing filler ("I hope this email finds you well")
   - Make the ask or closing feel genuine rather than templated
4. Do NOT add casual phrases, humor, or informality not appropriate for professional email.
5. Do NOT start sentences with And/But/So.
6. Preserve bullet point structure if present.
7. Output ONLY the rewritten email."""
    },

    "💼 Cover Letter": {
        "group": "Professional",
        "pipeline": "formal",
        "desc": "Job applications, internships",
        "tone_locked": "Confident & Genuine",
        "system_prompt": """You are a professional editor refining this cover letter to sound authentically human.

STRICT RULES:
1. Keep ALL factual claims: job titles, companies, skills, achievements, years of experience. NEVER fabricate.
2. Replace the templated opener ("I am writing to express my strong interest") with a direct, confident one ("I'm excited about this role because…").
3. Make the motivation feel genuine — but only from what's already in the text.
4. Add contractions where appropriate (I'm, I've, I'd).
5. Vary sentence length slightly — avoid uniform paragraph sizes.
6. Replace AI buzzwords: leverage, pivotal, passionate, driven, dynamic, synergy, robust.
7. Make the closing line feel specific and real, not boilerplate.
8. Preserve bullet points if present.
9. Do NOT add new achievements, stories, or qualifications.
10. Output ONLY the rewritten letter."""
    },

    "🔗 LinkedIn Post / Bio": {
        "group": "Professional",
        "pipeline": "general",
        "desc": "LinkedIn content, professional bios",
        "tone_locked": "Authentic & Professional",
        "system_prompt": """You are a LinkedIn content expert. Rewrite this to sound like a real professional wrote it — not a corporate AI.

RULES:
1. Keep all facts, role titles, achievements, and companies exactly as stated.
2. LinkedIn tone: professional but human. Confident but not boastful.
3. First-person voice. Natural use of "I".
4. Short punchy sentences mixed with medium-length ones. No walls of text.
5. Replace LinkedIn clichés: "passionate," "excited to share," "thrilled to announce," "game-changer," "leverage," "synergy."
6. Add one specific, concrete detail to make a vague claim feel real.
7. Remove hashtag overuse. If hashtags exist, keep max 3 and make them relevant.
8. Output ONLY the rewritten content."""
    },

    "📊 Business Report / Executive Summary": {
        "group": "Professional",
        "pipeline": "formal",
        "desc": "Reports, summaries, proposals",
        "tone_locked": "Clear & Executive",
        "system_prompt": """You are a senior business writer editing this report for clarity and human readability.

STRICT RULES:
1. Preserve all data, findings, recommendations, and factual claims exactly.
2. Replace overly complex passive constructions with clear active voice.
3. Remove redundant qualifiers ("it is important to note that," "it should be noted").
4. Replace AI buzzwords: leverage, synergy, paradigm, robust, seamlessly, ecosystem, innovative.
5. Keep formal structure: headers, bullet points, and numbered lists stay intact.
6. Do NOT add contractions — this is a formal business document.
7. Sentences should be clear and direct. Prefer shorter over longer.
8. Output ONLY the revised text."""
    },

    # ── Creative / Content ─────────────────────
    "✍️ Blog Post / Article": {
        "group": "Creative & Content",
        "pipeline": "general",
        "desc": "Blogs, articles, opinion pieces",
        "tone_locked": None,  # Tone selector enabled
        "system_prompt": None,  # Built dynamically
    },

    "📱 Social Media Content": {
        "group": "Creative & Content",
        "pipeline": "general",
        "desc": "Instagram, Twitter/X, Facebook captions",
        "tone_locked": "Casual & Engaging",
        "system_prompt": """You are a social media writer. Rewrite this to sound like a real person, not an AI content generator.

RULES:
1. Keep all factual claims and key messages intact.
2. Casual, energetic tone. Short sentences. Real human voice.
3. Remove all corporate-speak and AI buzzwords.
4. Vary rhythm — some very short sentences, some punchy medium ones.
5. Contractions everywhere (it's, you're, we're, don't, can't).
6. One rhetorical question or conversational hook.
7. If hashtags exist, keep max 3-5 relevant ones.
8. Output ONLY the rewritten content."""
    },

    "🎯 Marketing Copy / Ad": {
        "group": "Creative & Content",
        "pipeline": "general",
        "desc": "Product descriptions, ad copy, landing pages",
        "tone_locked": "Persuasive & Human",
        "system_prompt": """You are a conversion copywriter. Rewrite this marketing copy to sound like it was written by a sharp, human marketer.

RULES:
1. Keep all product claims, features, and CTAs exactly as stated. Never fabricate benefits.
2. Lead with the benefit, not the feature.
3. Short punchy sentences. Power words that feel earned, not hollow.
4. Remove: cutting-edge, revolutionary, game-changing, innovative, robust, seamlessly, leverage.
5. Active voice only. Remove all passive constructions.
6. Add one specific, concrete detail if the copy is vague.
7. Contractions are natural here (you're, it's, don't, we've).
8. Output ONLY the rewritten copy."""
    },

    "📖 Creative / Fictional Writing": {
        "group": "Creative & Content",
        "pipeline": "general",
        "desc": "Stories, narratives, creative nonfiction",
        "tone_locked": "Vivid & Narrative",
        "system_prompt": """You are a literary editor helping this piece of creative writing sound authentically human.

RULES:
1. Preserve the story, characters, plot, and all invented details exactly.
2. Make the prose feel alive: sensory details, rhythm, tension.
3. Vary sentence length dramatically. Mix fragments with long flowing sentences.
4. Remove generic descriptors ("beautiful," "amazing," "incredible") and replace with specific, evocative ones.
5. Remove AI tells: "it is worth noting," "as we can see," "needless to say."
6. Natural dialogue if present should sound like real people talk — incomplete sentences, interruptions.
7. Add one small unexpected detail that makes a scene feel real.
8. Output ONLY the revised text."""
    },

    # ── Personal ──────────────────────────────
    "💬 Personal Message / Text": {
        "group": "Personal",
        "pipeline": "general",
        "desc": "Texts, DMs, personal notes",
        "tone_locked": "Casual & Personal",
        "system_prompt": """You are rewriting this to sound like a real person texting or writing a personal note.

RULES:
1. Keep all factual content and intent intact.
2. Very casual, warm tone. Like texting a friend.
3. Contractions everywhere. Short sentences.
4. One small personal touch or conversational aside.
5. Remove ALL formal language, corporate phrasing, and AI buzzwords.
6. It's OK to start sentences with And, But, So.
7. Output ONLY the rewritten message."""
    },
}

# Group them for the UI
CONTENT_GROUPS = {}
for key, val in CONTENT_TYPES.items():
    g = val["group"]
    if g not in CONTENT_GROUPS:
        CONTENT_GROUPS[g] = []
    CONTENT_GROUPS[g].append(key)

# Tone options (only for Blog Post / Article)
TONE_OPTIONS = {
    "Conversational & Raw": "Like texting a smart friend. Casual, direct, uses contractions and short sentences.",
    "Professional but Natural": "Confident senior voice. Clear, no fluff. Like a sharp colleague explaining something.",
    "Storyteller": "Narrative flow. Em dashes, vivid details, cause and effect.",
    "Opinionated Blog": "First-person. Bold opinions. Rhetorical questions. Slightly impatient with fluff.",
    "Witty & Engaging": "Smart humor, clever observations, light sarcasm where appropriate.",
    "Neutral & Journalistic": "Objective, factual, AP-style clarity. No opinions.",
}

TONE_SYSTEM_PROMPTS = {
    "Conversational & Raw": """You are rewriting this in a genuine, casual human voice — like explaining something to a smart friend.
RULES: Contractions everywhere. Short mixed with longer sentences. And/But/So sentence starters OK. Simple concrete words. One small parenthetical aside. No jargon. Output ONLY the rewritten text.""",

    "Professional but Natural": """You are a senior editor rewriting this in a confident, direct professional voice — like a sharp colleague, not a consultant.
RULES: Direct and clear. No fluff. Contractions where natural. Active voice only. Vary sentence length — some punchy short ones, some longer explanatory ones. Output ONLY the rewritten text.""",

    "Storyteller": """You are a narrative writer giving this content story-like flow.
RULES: Make abstract concepts concrete and visual. Use em dashes — like this — for rhythm. Vary sentence length dramatically. Show cause and effect through narrative progression. One concrete scene-setting detail or analogy. Output ONLY the rewritten text.""",

    "Opinionated Blog": """You are a blogger with a distinct, confident voice.
RULES: First person. "I" used naturally. Direct and opinionated. Rhetorical questions: "Why does this matter? Because…". Start some sentences with "Look," or "Here's the thing:". Contractions everywhere. Output ONLY the rewritten text.""",

    "Witty & Engaging": """You are a witty writer — sharp, engaging, occasionally irreverent.
RULES: Clever observations. Light humor where natural. One well-placed subversion of expectation. Contractions and casual phrasing. Never try-hard or cringe. Output ONLY the rewritten text.""",

    "Neutral & Journalistic": """You are a journalist rewriting this in clear, neutral, AP-style prose.
RULES: Objective. No opinions or editorial asides. Active voice. Short clear sentences. No jargon. No AI buzzwords. No contractions unless in a quote. Output ONLY the rewritten text.""",
}


# ─────────────────────────────────────────────
#  DETECTOR INSTRUCTIONS
# ─────────────────────────────────────────────

def get_detector_instructions(gptzero, originality, turnitin, zerogpt) -> str:
    parts = []
    if gptzero:
        parts.append("""GPTZero Countermeasures (perplexity + burstiness):
- Mix sentence lengths aggressively. Some: 4 words. Others: longer with embedded clauses.
- Use one unexpected but correct word choice to raise perplexity.
- Add one rhetorical question somewhere.""")
    if originality:
        parts.append("""Originality.ai Countermeasures (semantic fingerprinting):
- Restructure the logical ORDER of ideas, not just words.
- Use idiomatic expressions: "easier said than done," "at the end of the day."
- Introduce one concrete specific detail (a number, a scenario).
- Avoid clean topic-sentence → support → conclusion paragraph structure.""")
    if turnitin:
        parts.append("""Turnitin Countermeasures (structural patterns + personal voice):
- Break paragraph symmetry. Not all 3–4 sentences. Some: 1. Some: 6.
- Include one mild opinion or judgment: "which, honestly, is the smarter approach."
- Avoid perfectly parallel list structures.""")
    if zerogpt:
        parts.append("""ZeroGPT Countermeasures (formal transitions + uniform clause length):
- Replace ALL formal transitions (However, Furthermore, Moreover, Additionally) with casual ones: But, Also, So, Plus.
- Vary clause length inside sentences.
- Start at least 2 sentences with conjunctions: And, But, So.
- Use a contraction in every paragraph.""")
    return "\n\n".join(parts)


# ─────────────────────────────────────────────
#  AI CLICHE REMOVAL (SAFE — no regex artifacts)
# ─────────────────────────────────────────────

AI_CLICHE_MAP = {
    "delve into": ["dig into", "explore", "look at", "get into"],
    "delves into": ["digs into", "explores", "gets into"],
    "delving into": ["digging into", "exploring", "getting into"],
    "unlock": ["open up", "access", "tap into"],
    "unleash": ["release", "bring out", "use"],
    "utilize": ["use", "apply", "work with"],
    "utilizes": ["uses", "applies"],
    "leverage": ["use", "tap into", "draw on"],
    "leverages": ["uses", "draws on"],
    "foster": ["build", "grow", "encourage"],
    "facilitate": ["help", "enable", "support"],
    "navigate": ["handle", "deal with", "manage"],
    "ensure": ["make sure", "confirm"],
    "underscore": ["highlight", "show", "stress"],
    "showcase": ["show", "highlight", "demonstrate"],
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
    "notably": ["interestingly", "importantly"],
    "moreover": ["also", "on top of that", "and"],
    "furthermore": ["beyond that", "also", "and"],
    "consequently": ["so", "as a result", "this means"],
    "nevertheless": ["still", "even so", "but"],
    "in conclusion": ["to wrap up", "so", "bottom line"],
    "in summary": ["in short", "briefly", "bottom line"],
    "it is important to note that": ["worth noting,", "keep in mind that", "note that"],
    "it's important to note that": ["worth noting,", "keep in mind that", "note that"],
    "it is worth noting that": ["worth mentioning,", "note that"],
    "it's worth noting that": ["worth mentioning,", "note that"],
    "in order to": ["to"],
    "due to the fact that": ["because", "since"],
    "at this point in time": ["now", "currently"],
    "game-changer": ["big shift", "major change", "real difference-maker"],
    "game changer": ["big shift", "major change"],
    "one must": ["you need to", "you have to"],
}

def clean_cliches(text: str) -> str:
    """Safe cliché replacement using whole-word matching, no regex artifacts."""
    for phrase, options in sorted(AI_CLICHE_MAP.items(), key=lambda x: -len(x[0])):
        pattern = r'(?<!\w)' + re.escape(phrase) + r'(?!\w)'
        if re.search(pattern, text, flags=re.IGNORECASE):
            replacement = random.choice(options)
            text = re.sub(pattern, replacement, text, count=1, flags=re.IGNORECASE)
    return text


# ─────────────────────────────────────────────
#  SAFE POST-PROCESSING (no dot artifacts)
# ─────────────────────────────────────────────

def safe_split_sentences(text: str):
    """Split on sentence boundaries without breaking abbreviations."""
    # Use a simple split that avoids splitting on "Mr. Smith" etc.
    return re.split(r'(?<=[.!?])(?=\s+[A-Z])', text.strip())


def safe_vary_burstiness(text: str) -> str:
    """
    Vary sentence length by splitting long sentences at natural conjunction points.
    Critically: avoids adding extra periods or creating dot artifacts.
    """
    sentences = safe_split_sentences(text)
    result = []

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue

        words = sent.split()
        wc = len(words)

        # Only try to split sentences > 25 words, 60% of the time
        if wc > 25 and random.random() < 0.6:
            split_done = False
            # Look for a natural split point (conjunction) in the middle third
            search_start = max(8, wc // 3)
            search_end = min(len(sent) - 8, (len(sent) * 2) // 3)

            for conj in [' and ', ' but ', ' because ', ' while ', ' although ', ' which ', ' so ']:
                idx = sent.lower().find(conj, search_start)
                # Make sure we're actually in the middle portion
                if idx != -1 and idx < search_end:
                    part1 = sent[:idx].rstrip(' ,').strip()
                    rest = sent[idx + len(conj):].strip()
                    if part1 and rest and len(part1.split()) > 4 and len(rest.split()) > 4:
                        # Ensure part1 ends with exactly one period
                        if part1[-1] not in '.!?':
                            part1 = part1 + '.'
                        # Capitalize start of part2
                        part2 = rest[0].upper() + rest[1:]
                        result.append(part1)
                        result.append(part2)
                        split_done = True
                        break
            if not split_done:
                result.append(sent)
        else:
            result.append(sent)

    return ' '.join(result)


def safe_replace_transitions(text: str, aggressive: bool = False) -> str:
    """Replace formal transitions safely. No regex that introduces artifacts."""
    replacements = {
        r'\bHowever,': random.choice(["But", "Still,", "That said,"]),
        r'\bTherefore,': random.choice(["So,", "That means", "As a result,"]),
        r'\bFurthermore,': random.choice(["Plus,", "Also,", "And"]),
        r'\bMoreover,': random.choice(["Plus,", "On top of that,", "Also,"]),
        r'\bIn addition,': random.choice(["Also,", "Plus,", "And"]),
        r'\bConsequently,': random.choice(["So,", "Because of that,", "That's why,"]),
        r'\bNevertheless,': random.choice(["Still,", "Even so,", "But"]),
        r'\bAdditionally,': random.choice(["Also,", "On top of that,", "Plus,"]),
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, count=1)
    return text


def add_human_specificity(text: str) -> str:
    """Add a human-sounding aside to one sentence (Originality.ai counter)."""
    asides = [
        " — and I've seen this firsthand",
        " — which, in practice, makes a real difference",
        ", and that's not a small thing",
        " — something most people overlook",
        " — simple, but it works",
        ", which is exactly the point",
    ]
    sentences = safe_split_sentences(text)
    if len(sentences) < 4:
        return text

    target_idx = random.randint(1, len(sentences) // 2)
    s = sentences[target_idx].strip()

    # Only add to sentences ending with a period (not already modified)
    if len(s.split()) > 10 and s.endswith('.'):
        aside = random.choice(asides)
        sentences[target_idx] = s[:-1] + aside + '.'

    return ' '.join(sentences)


def add_casual_starter(text: str) -> str:
    """Insert one casual sentence starter (for general/blog content only)."""
    starters = [
        "Honestly, ", "Look, ", "Here's the thing: ",
        "And honestly, ", "To be fair, ", "The thing is, ",
    ]
    sentences = safe_split_sentences(text)
    if len(sentences) < 4:
        return text

    # Pick a sentence in the middle, not the first or last
    idx = random.randint(1, len(sentences) - 2)
    s = sentences[idx].strip()

    # Don't double-apply — skip if sentence already starts with a starter word
    first_word = s.split()[0].lower() if s.split() else ""
    if first_word in {"honestly,", "look,", "here's", "and", "but", "so", "to", "the"}:
        return text

    starter = random.choice(starters)
    sentences[idx] = starter + s[0].lower() + s[1:]
    return ' '.join(sentences)


def add_contractions(text: str) -> str:
    """Expand contraction opportunities (safe, no artifacts)."""
    contractions = [
        (r'\bit is\b', "it's"),
        (r'\bthat is\b', "that's"),
        (r'\bthere is\b', "there's"),
        (r'\bthey are\b', "they're"),
        (r'\bwe are\b', "we're"),
        (r'\byou are\b', "you're"),
        (r'\bdo not\b', "don't"),
        (r'\bdoes not\b', "doesn't"),
        (r'\bis not\b', "isn't"),
        (r'\bare not\b', "aren't"),
        (r'\bhave not\b', "haven't"),
        (r'\bcan not\b', "can't"),
        (r'\bcannot\b', "can't"),
        (r'\bwill not\b', "won't"),
        (r'\bwould not\b', "wouldn't"),
        (r'\bshould not\b', "shouldn't"),
        (r'\bcould not\b', "couldn't"),
        (r'\bdid not\b', "didn't"),
        (r'\bwas not\b', "wasn't"),
        (r'\bI am\b', "I'm"),
        (r'\bI have\b', "I've"),
        (r'\bI would\b', "I'd"),
        (r'\bI will\b', "I'll"),
    ]
    # Apply each contraction with 70% probability
    for pattern, replacement in contractions:
        if random.random() < 0.7:
            text = re.sub(pattern, replacement, text, count=1, flags=re.IGNORECASE)
    return text


def post_process_general(text: str, gptzero, originality, turnitin, zerogpt) -> str:
    """Full post-processing pipeline for general/blog content."""
    text = clean_cliches(text)
    text = safe_vary_burstiness(text)
    text = safe_replace_transitions(text, aggressive=True)
    text = add_contractions(text)
    if originality:
        text = add_human_specificity(text)
    text = add_casual_starter(text)
    # Clean up any double spaces that might have crept in
    text = re.sub(r'  +', ' ', text)
    # Clean up space before punctuation
    text = re.sub(r' ([,.!?;:])', r'\1', text)
    return text.strip()


def post_process_formal(text: str) -> str:
    """Minimal post-processing for formal documents."""
    text = clean_cliches(text)
    text = add_contractions(text)
    text = re.sub(r'  +', ' ', text)
    text = re.sub(r' ([,.!?;:])', r'\1', text)
    return text.strip()


# ─────────────────────────────────────────────
#  MAIN HUMANIZE FUNCTION
# ─────────────────────────────────────────────

MODEL_OPTIONS = {
    "Llama 3.3 70B — Best Quality (Recommended)": "llama-3.3-70b-versatile",
    "Llama 3.1 8B — Fast & Light": "llama-3.1-8b-instant",
    "Mixtral 8x7B — Alternative": "mixtral-8x7b-32768",
}

GENERAL_MODEL = "llama-3.3-70b-versatile"  # Always use best for general pipeline


def build_general_system_prompt(tone: str, gptzero, originality, turnitin, zerogpt) -> str:
    base = TONE_SYSTEM_PROMPTS.get(tone, TONE_SYSTEM_PROMPTS["Conversational & Raw"])
    targets = get_detector_instructions(gptzero, originality, turnitin, zerogpt)
    forbidden = "FORBIDDEN WORDS (never use): delve, utilize, leverage, paramount, landscape, realm, testament, moreover, furthermore, in conclusion, cutting-edge, game-changer, groundbreaking, pivotal, robust, seamlessly, foster, comprehensive, transformative, synergy, ecosystem, paradigm, multifaceted, it is important to note, needless to say."
    combined = base
    if targets:
        combined += f"\n\nANTI-DETECTION RULES:\n{targets}"
    combined += f"\n\n{forbidden}\n\nOutput ONLY the rewritten text. No preamble, no commentary."
    return combined


def humanize(
    text: str,
    content_type: str,
    tone: str,
    client,
    model_id: str,
    stealth: bool,
    gptzero: bool,
    originality: bool,
    turnitin: bool,
    zerogpt: bool,
) -> str:
    ct = CONTENT_TYPES[content_type]
    pipeline = ct["pipeline"]

    try:
        # ── FORMAL PIPELINE (single-pass, restrained) ──────────────────
        if pipeline == "formal":
            system_prompt = ct["system_prompt"]
            r = client.chat.completions.create(
                model=model_id,
                temperature=0.6,
                max_tokens=2800,
                top_p=0.88,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Please edit this:\n\n{text}"},
                ]
            )
            result = r.choices[0].message.content.strip()
            if stealth:
                result = post_process_formal(result)
            return result

        # ── GENERAL PIPELINE (4-pass, aggressive) ─────────────────────
        # Use best model for general pipeline always
        gmodel = GENERAL_MODEL

        # Check if this type has a fixed system prompt or dynamic (Blog only)
        if ct["system_prompt"] is not None:
            # Content type has its own fixed system prompt
            pass1_system = ct["system_prompt"]
            final_system = ct["system_prompt"]
        else:
            # Blog/Article — use tone-based prompt
            pass1_system = TONE_SYSTEM_PROMPTS.get(tone, TONE_SYSTEM_PROMPTS["Conversational & Raw"])
            final_system = build_general_system_prompt(tone, gptzero, originality, turnitin, zerogpt)

        # PASS 1: Expand with creativity (high temp)
        r1 = client.chat.completions.create(
            model=gmodel,
            temperature=1.4,
            max_tokens=4000,
            top_p=0.97,
            messages=[
                {"role": "system", "content": (
                    "You are a creative human writer. Expand this text by about 35% — add a personal angle, "
                    "a concrete example or analogy, and one opinion. Use casual, varied language. "
                    "Vary sentence lengths dramatically. Do NOT use AI buzzwords. "
                    "Output ONLY the expanded text. No preamble."
                )},
                {"role": "user", "content": text},
            ]
        )
        expanded = r1.choices[0].message.content.strip()

        # PASS 2: Humanize with detector-specific rules
        detector_additions = get_detector_instructions(gptzero, originality, turnitin, zerogpt)
        pass2_system = pass1_system
        if detector_additions:
            pass2_system += f"\n\nANTI-DETECTION RULES:\n{detector_additions}"
        pass2_system += "\nOutput ONLY the rewritten text. Condense to roughly the original length."

        r2 = client.chat.completions.create(
            model=gmodel,
            temperature=1.2,
            max_tokens=3200,
            top_p=0.95,
            messages=[
                {"role": "system", "content": pass2_system},
                {"role": "user", "content": f"Rewrite this to sound like a smart human wrote it:\n\n{expanded}"},
            ]
        )
        current = r2.choices[0].message.content.strip()

        # PASS 3: Rhythm & structure pass
        r3 = client.chat.completions.create(
            model=gmodel,
            temperature=1.1,
            max_tokens=3200,
            top_p=0.93,
            messages=[
                {"role": "system", "content": (
                    "You are a sentence rhythm expert. Make this text sound undeniably human:\n"
                    "- Ensure NO two consecutive sentences are the same length\n"
                    "- Replace any formal transitions (However, Furthermore, Moreover, Additionally, Consequently) "
                    "with casual equivalents (But, Also, So, Plus, That said)\n"
                    "- Add 1-2 natural casual phrases where appropriate (e.g. 'honestly', 'here's the thing', "
                    "'to be fair') — but ONLY if it fits the document type and tone\n"
                    "- Break any overly parallel paragraph structures\n"
                    "- Do NOT add new facts or fabricate anything\n"
                    "Output ONLY the result. No preamble."
                )},
                {"role": "user", "content": current},
            ]
        )
        current = r3.choices[0].message.content.strip()

        # PASS 4: Final anti-detection polish
        r4 = client.chat.completions.create(
            model=gmodel,
            temperature=0.9,
            max_tokens=3200,
            top_p=0.92,
            messages=[
                {"role": "system", "content": (
                    "Final polish for maximum human authenticity:\n"
                    "- Remove any remaining AI buzzwords or templated phrases\n"
                    "- Ensure contractions are used naturally throughout\n"
                    "- Vary sentence rhythm one last time — no two adjacent sentences should feel the same length\n"
                    "- If there is a perfectly structured paragraph, slightly break its symmetry\n"
                    "- Do NOT change factual content\n"
                    "Output ONLY the final text. No preamble."
                )},
                {"role": "user", "content": current},
            ]
        )
        current = r4.choices[0].message.content.strip()

        # POST-PROCESSING
        if stealth:
            current = post_process_general(current, gptzero, originality, turnitin, zerogpt)

        return current

    except Exception as e:
        return f"Error: {str(e)}"


# ─────────────────────────────────────────────
#  CACHE KEY
# ─────────────────────────────────────────────

def make_cache_key(text, content_type, tone, model, stealth, gpt, ori, tur, zer, randomize):
    seed = str(random.random()) if randomize else "static"
    raw = f"{text}|{content_type}|{tone}|{model}|{stealth}|{gpt}|{ori}|{tur}|{zer}|{seed}"
    return hashlib.md5(raw.encode()).hexdigest()


# ─────────────────────────────────────────────
#  UI
# ─────────────────────────────────────────────

# SIDEBAR
with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    api_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...", help="Get yours at console.groq.com")

    st.markdown("---")
    st.markdown("**🎯 Target Detectors**")
    col_a, col_b = st.columns(2)
    with col_a:
        target_gptzero     = st.checkbox("GPTZero",    value=True)
        target_turnitin    = st.checkbox("Turnitin",   value=True)
    with col_b:
        target_originality = st.checkbox("Originality.ai", value=True)
        target_zerogpt     = st.checkbox("ZeroGPT",   value=True)

    st.markdown("---")
    st.markdown("**🤖 Model**")
    selected_model_name = st.selectbox("", list(MODEL_OPTIONS.keys()), label_visibility="collapsed")
    selected_model_id = MODEL_OPTIONS[selected_model_name]

    st.markdown("---")
    st.markdown("**⚙️ Options**")
    stealth   = st.checkbox("Stealth Post-Processing", value=True,
                            help="Applies a secondary layer of cliché removal, rhythm variation, and human-sounding touches after the LLM pass.")
    randomize = st.checkbox("Randomize Each Run", value=True,
                            help="Disables result caching so every run generates a fresh version.")

    st.markdown("---")
    st.markdown("""
<div style="font-size:12px;color:#888;line-height:1.6">
<b>Tips for best results:</b><br>
• Use all 4 detectors for maximum stealth<br>
• General content uses a 4-pass pipeline<br>
• Formal docs use a 1-pass restrained pipeline<br>
• Always verify output before submitting
</div>
""", unsafe_allow_html=True)


# MAIN CONTENT
st.markdown("## 🖊️ Authentica v4")
st.markdown("AI content humanizer with **document-aware pipelines** and **multi-detector targeting**.")

# Active detector badges
badges_html = ""
for label, active in [
    ("GPTZero", target_gptzero),
    ("Originality.ai", target_originality),
    ("Turnitin", target_turnitin),
    ("ZeroGPT", target_zerogpt),
]:
    cls = "badge-active" if active else "badge-inactive"
    badges_html += f'<span class="badge {cls}">{label}</span> '

st.markdown(f"**Targeting:** {badges_html}", unsafe_allow_html=True)
st.markdown("---")

# CONTENT TYPE SELECTOR — grouped
st.markdown("#### 📂 Select Content Type")
group_labels = list(CONTENT_GROUPS.keys())
selected_group = st.radio("Category", group_labels, horizontal=True, label_visibility="collapsed")
content_type_options = CONTENT_GROUPS[selected_group]

col_ct1, col_ct2 = st.columns([3, 2])
with col_ct1:
    content_type = st.selectbox(
        f"{selected_group} types:",
        content_type_options,
        label_visibility="visible",
    )

ct_info = CONTENT_TYPES[content_type]
with col_ct2:
    pipeline_label = "🚀 4-Pass Aggressive" if ct_info["pipeline"] == "general" else "🎯 1-Pass Restrained"
    tone_label = ct_info.get("tone_locked") or "User-selected"
    st.markdown(f"""
<div class="pipeline-card">
<div class="pipeline-title">{pipeline_label}</div>
<div class="pipeline-desc">{ct_info['desc']}</div>
<div class="pipeline-desc" style="margin-top:6px">Tone: <b>{tone_label}</b></div>
</div>
""", unsafe_allow_html=True)

# TONE SELECTOR — only for Blog Post / Article
tone = "Conversational & Raw"  # default
if ct_info.get("tone_locked") is None:  # Blog/Article only
    st.markdown("#### 🎨 Tone")
    tone_cols = st.columns(len(TONE_OPTIONS))
    selected_tone = None
    for i, (t_name, t_desc) in enumerate(TONE_OPTIONS.items()):
        with tone_cols[i]:
            if st.button(t_name.split(" & ")[0], key=f"tone_{i}", use_container_width=True):
                st.session_state["selected_tone"] = t_name
    tone = st.session_state.get("selected_tone", "Conversational & Raw")

    # Show active tone description
    st.markdown(f"""
<div class="tip-card">
<b>{tone}</b> — {TONE_OPTIONS[tone]}
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# INPUT / OUTPUT
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 📥 Input")
    input_text = st.text_area(
        "Paste your text here",
        height=400,
        placeholder="Paste your AI-generated text here...\n\nSupports any length — essays, emails, SOPs, blog posts, cover letters, and more.",
        label_visibility="collapsed",
    )
    wc_in = len(input_text.split()) if input_text.strip() else 0
    st.caption(f"Word count: **{wc_in}**")

with col2:
    st.markdown("#### 📤 Output")
    output_placeholder = st.empty()
    status_placeholder = st.empty()

    run_btn = st.button("🚀 Humanize Now", type="primary", use_container_width=True)

    if run_btn:
        if not api_key:
            st.error("⚠️ Please add your Groq API key in the sidebar.")
        elif not input_text.strip():
            st.warning("Please paste some text to humanize.")
        elif wc_in < 20:
            st.warning("Text is too short. Please provide at least 20 words for best results.")
        elif not any([target_gptzero, target_originality, target_turnitin, target_zerogpt]):
            st.warning("Select at least one target detector in the sidebar.")
        else:
            client = Groq(api_key=api_key)
            pipeline_name = "4-pass aggressive" if ct_info["pipeline"] == "general" else "1-pass restrained"

            if "cache" not in st.session_state:
                st.session_state.cache = {}

            ck = make_cache_key(
                input_text, content_type, tone, selected_model_id,
                stealth, target_gptzero, target_originality, target_turnitin, target_zerogpt,
                randomize
            )

            with st.spinner(f"Running {pipeline_name} pipeline for **{content_type}**..."):
                if ck in st.session_state.cache and not randomize:
                    result = st.session_state.cache[ck]
                else:
                    result = humanize(
                        input_text,
                        content_type,
                        tone,
                        client,
                        selected_model_id,
                        stealth,
                        target_gptzero,
                        target_originality,
                        target_turnitin,
                        target_zerogpt,
                    )
                    if not result.startswith("Error:"):
                        st.session_state.cache[ck] = result

            if result.startswith("Error:"):
                st.error(result)
            else:
                output_placeholder.text_area(
                    "Humanized output",
                    value=result,
                    height=400,
                    label_visibility="collapsed",
                )
                wc_out = len(result.split())
                st.caption(f"Word count: **{wc_out}**")
                st.success(f"✅ Done! {pipeline_name.capitalize()} pipeline complete.")

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Pipeline", "Aggressive" if ct_info["pipeline"] == "general" else "Restrained")
                m2.metric("Passes", 4 if ct_info["pipeline"] == "general" else 1)
                m3.metric("Detectors", sum([target_gptzero, target_originality, target_turnitin, target_zerogpt]))
                m4.metric("Post-Proc", "On" if stealth else "Off")

# EXPLAINER
st.markdown("---")
with st.expander("📖 How Authentica v4 works"):
    st.markdown("""
    ### Two pipelines, zero tone pollution

    | Content Type | Pipeline | Passes | Temperature | Post-Processing |
    |---|---|---|---|---|
    | Blog / Article | General | 4 | 0.9 – 1.4 | Full: burstiness, transitions, specificity |
    | SOP / Personal Statement | Formal | 1 | 0.6 | Minimal: clichés + contractions only |
    | Cover Letter | Formal | 1 | 0.6 | Minimal |
    | Professional Email | Formal | 1 | 0.6 | Minimal |
    | Academic / Research | Formal | 1 | 0.6 | Minimal |
    | College App Essay | Formal | 1 | 0.6 | Minimal |
    | LinkedIn / Social | General | 4 | 0.9 – 1.4 | Full |
    | Marketing Copy | General | 4 | 0.9 – 1.4 | Full |

    ### Detector-specific targeting

    | Detector | Primary Signal | Fix Applied |
    |---|---|---|
    | **GPTZero** | Low perplexity + low burstiness | High temp, mixed sentence lengths, unexpected word choices |
    | **Originality.ai** | Semantic fingerprinting | Idea reordering, concrete specifics injected, idioms |
    | **Turnitin** | Structural patterns + absent personal voice | Paragraph asymmetry, opinion statements |
    | **ZeroGPT** | Formal transitions + uniform clauses | All formal transitions replaced, contractions everywhere |

    ### What was fixed in v4
    - ✅ Rogue dot artifacts eliminated — sentence splitting now validates both parts before creating new sentences
    - ✅ 12 content types with document-specific system prompts
    - ✅ Tone selector only appears for Blog/Article (not SOPs or emails where it causes problems)
    - ✅ Formal docs never receive casual injections ("Look,", "Honestly,") that sound wrong in professional context
    - ✅ Post-processing cleans double spaces and space-before-punctuation artifacts
    - ✅ Cache key logic fixed so randomization actually works correctly
    - ✅ Fragment injection removed (was creating single-word sentences mid-paragraph)
    - ✅ Comma splice injection removed (was creating unnatural grammar errors)
    """)

st.markdown("---")
st.markdown("<div style='text-align:center;color:#bbb;font-size:12px'>Authentica v4 · Powered by Groq Cloud · For legitimate content work only</div>", unsafe_allow_html=True)
