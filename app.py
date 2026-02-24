import streamlit as st
from groq import Groq
import time
import hashlib
import re
import random

# --- Page Config ---
st.set_page_config(page_title="Authentica v3 | Multi-Detector", page_icon="🕵️", layout="wide")

st.markdown("""
    <style>
    body { font-family: 'Segoe UI', sans-serif; }
    .stTextArea label { font-weight: bold; }
    .detector-badge {
        display: inline-block; padding: 4px 10px; border-radius: 12px;
        font-size: 12px; font-weight: bold; margin: 2px;
    }
    .badge-green { background: #d4edda; color: #155724; }
    .badge-yellow { background: #fff3cd; color: #856404; }
    .badge-red { background: #f8d7da; color: #721c24; }
    .tip-box { padding: 12px; background: #f0f4ff; border-left: 4px solid #4a6cf7; border-radius: 4px; margin: 8px 0; }
    </style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Groq API Key", type="password", help="console.groq.com")

    st.markdown("---")
    st.subheader("🎯 Target Detectors")
    target_gptzero      = st.checkbox("GPTZero",        value=True)
    target_originality  = st.checkbox("Originality.ai", value=True)
    target_turnitin     = st.checkbox("Turnitin",       value=True)
    target_zerogpt      = st.checkbox("ZeroGPT",        value=True)

    st.markdown("---")
    st.subheader("Model")
    model_options = {
        "Llama 3.3 70B — Most Intelligent (Recommended for General Content)": "llama-3.3-70b-versatile",
        "Llama 3.1 8B — Faster but Less Powerful":       "llama-3.1-8b-instant",
        "Mixtral 8x7B — Alternative":                    "mixtral-8x7b-32768",
    }
    selected_model_name = st.selectbox("Model", list(model_options.keys()))
    selected_model_id   = model_options[selected_model_name]

    st.markdown("---")
    st.subheader("Document Type")
    doc_type = st.selectbox("What are you humanizing?", [
        "General Content (Blog / Article / Essay)",
        "Professional Email",
        "Academic / Research Writing",
        "Cover Letter / Application",
    ])
    st.caption({
        "General Content (Blog / Article / Essay)":    "✅ Full stealth pipeline — aggressive humanization (4 passes, high temp, heavy post‑proc)",
        "Professional Email":                          "⚠️ Restrained pipeline — keeps formal tone, fixes AI tells only",
        "Academic / Research Writing":                 "⚠️ Conservative pipeline — preserves structure and citations",
        "Cover Letter / Application":                  "⚠️ Restrained pipeline — professional voice, no fabrications",
    }[doc_type])

    st.markdown("---")
    st.subheader("Style")

    # Tone selector is only meaningful for general content
    tone_disabled = doc_type != "General Content (Blog / Article / Essay)"
    tone = st.selectbox("Tone (General Content only)", [
        "Conversational & Raw",
        "Professional but Natural",
        "Storyteller",
        "Opinionated Blog",
    ], disabled=tone_disabled)
    if tone_disabled:
        st.caption("🔒 Tone is fixed for this document type.")

    st.markdown("---")
    st.subheader("Pipeline")
    num_passes  = st.slider("Rewrite Passes", 1, 3, 3,
                             help="For General Content, 4 passes are always used regardless of this setting.")
    stealth     = st.checkbox("Stealth Post-Processing", value=True)
    randomize   = st.checkbox("Randomize on Each Run",   value=True,
                               help="Disables cache so each run is unique")

    st.markdown("---")
    st.info("🏆 Best combo for General Content: **4 passes + Stealth**, all detectors checked.")
    st.warning("⚠️ For legitimate content work only.")


# ─────────────────────────────────────────────
#  AI CLICHE / BUZZWORD REMOVAL
# ─────────────────────────────────────────────

AI_CLICHE_MAP = {
    # Verbs
    "delve": ["dig into", "get into", "look at", "explore"],
    "delves": ["digs into", "gets into", "explores"],
    "delving": ["digging into", "getting into", "exploring"],
    "unlock": ["open up", "access", "tap into", "find"],
    "unleash": ["release", "let out", "bring out", "use"],
    "utilize": ["use", "apply", "work with"],
    "utilizes": ["uses", "applies", "works with"],
    "leverage": ["use", "tap into", "rely on", "draw on"],
    "leverages": ["uses", "taps into", "draws on"],
    "foster": ["build", "grow", "encourage", "support"],
    "facilitate": ["help", "enable", "support", "make easier"],
    "navigate": ["handle", "deal with", "work through", "manage"],
    "ensure": ["make sure", "confirm", "see that"],
    "underscore": ["highlight", "show", "point out", "stress"],
    "showcase": ["show", "display", "highlight", "demonstrate"],
    "harness": ["use", "apply", "tap into", "channel"],

    # Nouns
    "realm": ["area", "space", "world", "domain", "field"],
    "landscape": ["field", "scene", "environment", "picture", "world"],
    "testament": ["proof", "sign", "evidence", "indicator"],
    "paradigm": ["model", "approach", "way of thinking", "framework"],
    "synergy": ["teamwork", "collaboration", "combined effort"],
    "ecosystem": ["system", "network", "environment", "setup"],

    # Adjectives
    "paramount": ["key", "critical", "essential", "top-priority", "vital"],
    "pivotal": ["key", "crucial", "central", "critical", "important"],
    "groundbreaking": ["new", "innovative", "fresh", "original", "novel"],
    "cutting-edge": ["new", "modern", "latest", "up-to-date", "advanced"],
    "cutting edge": ["new", "modern", "latest", "up-to-date"],
    "robust": ["strong", "solid", "reliable", "well-built", "solid"],
    "comprehensive": ["complete", "full", "thorough", "detailed", "wide-ranging"],
    "innovative": ["new", "creative", "fresh", "original", "inventive"],
    "transformative": ["significant", "major", "powerful", "game-changing"],
    "multifaceted": ["complex", "layered", "varied", "nuanced"],

    # Adverbs & filler phrases
    "seamlessly": ["smoothly", "easily", "without friction", "naturally"],
    "notably": ["interestingly", "worth mentioning", "importantly"],

    # Transition words / phrases that scream AI
    "moreover":             ["also", "on top of that", "plus", "and"],
    "furthermore":          ["beyond that", "also", "what's more", "and"],
    "consequently":         ["so", "as a result", "because of that", "this means"],
    "nevertheless":         ["still", "even so", "that said", "but"],
    "in conclusion":        ["to wrap up", "at the end of the day", "so", "bottom line"],
    "in summary":           ["in short", "to put it simply", "bottom line", "briefly"],
    "it is important to note":  ["worth noting", "keep in mind", "note that"],
    "it's important to note":   ["worth noting", "keep in mind", "note that"],
    "it is worth noting":       ["worth mentioning", "note that", "keep in mind"],
    "it's worth noting":        ["worth mentioning", "note that"],
    "in the world of":          ["in", "within", "across", "inside"],
    "in today's":               ["today,", "these days,", "right now,", "nowadays,"],
    "game-changer":             ["big shift", "real difference-maker", "major change"],
    "game changer":             ["big shift", "real difference-maker", "major change"],
    "one must":                 ["you need to", "you have to", "it helps to"],
    "in order to":              ["to"],
    "due to the fact that":     ["because", "since"],
    "at this point in time":    ["now", "currently", "at this point"],
    "as we can see":            ["clearly", "as shown", "it's clear that", "you can see"],
}

TRANSITION_SWAPS = {
    "However,": ["But", "Still,", "That said,", "Even so,", "Yet,"],
    "Nevertheless,": ["Still,", "Even so,", "But", "That said,"],
    "Therefore,": ["So,", "This means", "Because of that,", "As a result,"],
    "Additionally,": ["Also,", "On top of that,", "And", "Plus,"],
    "In addition,": ["Also,", "Plus,", "And", "On top of that,"],
    "Notably,": ["Interestingly,", "Here's the thing —", "Worth noting:"],
    "Importantly,": ["Here's the key part:", "What matters is", "Crucially,"],
    "Consequently,": ["So,", "As a result,", "Because of this,"],
    "Furthermore,": ["And", "Plus,", "What's more,", "Also,"],
    "Moreover,": ["Also,", "And", "On top of that,", "Beyond that,"],
}


def clean_cliches(text: str) -> str:
    cleaned = text
    for phrase, options in sorted(AI_CLICHE_MAP.items(), key=lambda x: -len(x[0])):
        pattern = r'\b' + re.escape(phrase) + r'\b'
        if re.search(pattern, cleaned, flags=re.IGNORECASE):
            replacement = random.choice(options)
            cleaned = re.sub(pattern, replacement, cleaned, count=1, flags=re.IGNORECASE)
    for phrase, options in TRANSITION_SWAPS.items():
        cleaned = cleaned.replace(phrase, random.choice(options))
    return cleaned


# ─────────────────────────────────────────────
#  DETECTOR-SPECIFIC WEAKNESSES
# ─────────────────────────────────────────────

def get_detector_instructions(gptzero, originality, turnitin, zerogpt) -> str:
    """
    Each detector has a known weakness. Build targeted instructions.
    GPTZero    → perplexity + burstiness
    Originality → semantic fingerprinting, looks for consistent high-probability sequences
    Turnitin   → structural patterns, paragraph symmetry, absence of personal voice
    ZeroGPT    → very sensitive to formal transitions and uniform clause length
    """
    parts = []

    if gptzero:
        parts.append("""
GPTZero Countermeasures (perplexity + burstiness):
- Mix sentence lengths AGGRESSIVELY. Some sentences: 4 words. Others can run long with embedded clauses, details, and qualifications that a real person might ramble through.
- Use unexpected word choices occasionally — a slightly unusual but correct word raises perplexity.
- Add one rhetorical question somewhere.
""")
    if originality:
        parts.append("""
Originality.ai Countermeasures (semantic fingerprinting):
- Restructure the logical ORDER of ideas, not just the words. Don't just paraphrase — rearrange.
- Use idiomatic expressions: "easier said than done", "at the end of the day", "the elephant in the room".
- Introduce at least one concrete, specific example (a number, a name, a real scenario).
- Avoid writing in clean topic-sentence → support → conclusion paragraph structure.
""")
    if turnitin:
        parts.append("""
Turnitin Countermeasures (structural patterns + personal voice):
- Break paragraph symmetry. Paragraphs should NOT all be 3–4 sentences. Some: 1 sentence. Some: 6.
- Use first-person voice ("I think", "in my experience", "what I've seen") where natural.
- Include an opinion or mild judgment — "which, honestly, is the smarter approach".
- Avoid perfectly parallel list structures (e.g., "First... Second... Third...").
""")
    if zerogpt:
        parts.append("""
ZeroGPT Countermeasures (formal transitions + uniform clause length):
- Replace ALL formal transitions (However, Furthermore, Moreover, Additionally, Consequently) with casual ones: But, Also, So, Plus, And.
- Vary clause length inside sentences — don't write consistently balanced clauses.
- Start at least 2 sentences with conjunctions: "And", "But", "So".
- Use a contraction in every paragraph.
""")

    return "\n".join(parts) if parts else ""


# ─────────────────────────────────────────────
#  FORMAL DOCUMENT PROMPTS (restrained pipeline)
# ─────────────────────────────────────────────

FORMAL_PROMPTS = {
    "Professional Email": """
You are a professional editor lightly editing this email to sound naturally human-written.

STRICT RULES:
- Keep the formal greeting and sign-off (Dear / Best regards / Sincerely). Do NOT change to "Hey".
- Keep ALL factual claims exactly as stated. NEVER invent experiences, events, or personal stories.
- Keep all specific technical terms, project names, tools, and credentials exactly as written.
- ONLY make these kinds of changes:
    • Replace stiff formal phrases with natural but still professional equivalents
    • Add contractions where natural (I am → I'm, I have → I've, I would → I'd)
    • Break up any overly long, run-on sentences
    • Remove filler phrases like "I am writing to" or "I would like to take this opportunity"
    • Make the motivation/closing line feel genuine rather than templated
- Do NOT add casual phrases like "honestly", "look,", "here's the thing", "to be fair"
- Do NOT start sentences with And/But/So in a formal email
- Do NOT rearrange the structure or reorder bullet points
- Output ONLY the rewritten email.
""",
    "Academic / Research Writing": """
You are an academic editor lightly revising this text to sound naturally human-written while preserving scholarly tone.

STRICT RULES:
- Preserve all citations, data points, technical terms, and factual claims exactly.
- Keep formal academic transitions (however, therefore, furthermore) — these are APPROPRIATE here.
- Only change: overly passive constructions, unnecessarily complex sentence structures, and AI buzzwords.
- Do NOT inject casual language, contractions, or personal asides.
- Do NOT reorder arguments or restructure paragraphs.
- Replace only the most obvious AI phrases: "it is important to note", "delve into", "in the realm of".
- Output ONLY the revised text.
""",
    "Cover Letter / Application": """
You are a professional editor lightly editing this cover letter to sound naturally human-written.

STRICT RULES:
- Keep ALL factual claims, credentials, project names, and experiences exactly as stated.
- NEVER fabricate personal anecdotes, events, or emotional stories not present in the original.
- Keep professional tone throughout — no slang, no casual openers like "Hey".
- Make these changes ONLY:
    • Add natural contractions (I am → I'm, I have → I've)
    • Replace templated opener phrases ("I am writing to express my strong interest" → "I'm interested in")
    • Make the closing line feel genuine rather than boilerplate
    • Vary sentence length slightly where the original is very uniform
    • Replace obvious AI buzzwords with plain equivalents
- Preserve bullet point structure if present — do NOT convert to prose
- Do NOT add new claims, stories, or motivations
- Output ONLY the rewritten letter.
""",
}


def is_formal_doc(doc_type: str) -> bool:
    return doc_type != "General Content (Blog / Article / Essay)"


TONE_PROMPTS = {
    "Conversational & Raw": """
You are rewriting this in a genuine, casual human voice. Like texting a smart friend.

RULES:
- Contractions everywhere: it's, don't, can't, won't, they're, we're.
- Short sentences mixed with longer ones. No pattern.
- OK to start sentences with And, But, So.
- Use simple, concrete words. Zero corporate jargon.
- Add one small parenthetical aside (like this).
- Output ONLY the rewritten text.
""",
    "Professional but Natural": """
You are a senior editor rewriting this in a confident, direct professional voice — like a smart colleague explaining something, not a consultant writing a report.

RULES:
- Direct and clear. No fluff. No hedging unless necessary.
- Contractions where natural. No stiff language.
- Active voice only. Cut all passive constructions.
- Replace jargon with plain English equivalents.
- Vary sentence length — some punchy short ones, some longer explanatory ones.
- Output ONLY the rewritten text.
""",
    "Storyteller": """
You are a narrative writer giving this content a story-like flow.

RULES:
- Make abstract concepts feel concrete and visual.
- Use em dashes — like this — to add rhythm and emphasis.
- Vary sentence length dramatically.
- Show cause and effect through narrative progression.
- One concrete scene-setting detail or analogy.
- Output ONLY the rewritten text.
""",
    "Opinionated Blog": """
You are a blogger with a distinct, confident voice.

RULES:
- Write in first person. Use 'I' naturally.
- Be direct and opinionated. State things plainly.
- Use rhetorical questions: "Why does this matter? Because..."
- Start some sentences with "Look,", "Here's the thing:", "And honestly,".
- Contractions everywhere. Sound human, slightly impatient with fluff.
- Output ONLY the rewritten text.
""",
}


# ─────────────────────────────────────────────
#  ORIGINAL POST-PROCESSING (kept for compatibility)
# ─────────────────────────────────────────────

def inject_quirks(text: str, tone: str) -> str:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if len(sentences) < 3:
        return text

    contractions = {
        "it is ": "it's ", "that is ": "that's ", "there is ": "there's ",
        "they are ": "they're ", "we are ": "we're ", "you are ": "you're ",
        "do not ": "don't ", "does not ": "doesn't ", "is not ": "isn't ",
        "are not ": "aren't ", "have not ": "haven't ", "can not ": "can't ",
        "will not ": "won't ", "would not ": "wouldn't ", "should not ": "shouldn't ",
        "could not ": "couldn't ", "did not ": "didn't ", "was not ": "wasn't ",
    }

    modified = []
    for i, sent in enumerate(sentences):
        s = sent.strip()
        if tone in ("Conversational & Raw", "Opinionated Blog", "Storyteller"):
            for long, short in contractions.items():
                if long in s:
                    s = s.replace(long, short, 1)

        if i > 0 and random.random() < 0.18:
            if not re.match(r'^(And |But |So |Yet |Or |Look,|Plus,)', s):
                prefix = random.choice(["And ", "But ", "So "])
                s = prefix + s[0].lower() + s[1:]

        modified.append(s)

    return " ".join(modified)


def vary_burstiness(text: str) -> str:
    """Split long sentences and merge short ones to vary burstiness."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    result = []
    i = 0
    while i < len(sentences):
        s = sentences[i]
        wc = len(s.split())

        if wc > 28 and random.random() < 0.65:
            split_done = False
            for splitter in [' and ', ' which ', ' because ', ' but ', ' while ', ' although ']:
                idx = s.lower().find(splitter, max(15, len(s) // 3))
                if idx != -1:
                    part1 = s[:idx].strip().rstrip(',') + '.'
                    rest  = s[idx + len(splitter):].strip()
                    part2 = rest[0].upper() + rest[1:] if rest else rest
                    result.extend([part1, part2])
                    split_done = True
                    break
            if not split_done:
                result.append(s)

        elif wc < 7 and i + 1 < len(sentences) and len(sentences[i+1].split()) < 7 and random.random() < 0.45:
            next_s = sentences[i+1]
            merged = s.rstrip('.!?') + ', ' + next_s[0].lower() + next_s[1:]
            result.append(merged)
            i += 2
            continue

        else:
            result.append(s)
        i += 1

    return ' '.join(result)


def add_human_specificity(text: str) -> str:
    """
    Originality.ai specifically looks for generic AI writing.
    Injecting a plausible-sounding specific detail raises the human score.
    """
    specifics = [
        " — and I've seen this firsthand",
        " — which, in practice, makes a real difference",
        ", and that's not a small thing",
        " — something most people overlook",
        ", which is exactly the point",
        " — simple, but it works",
    ]
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if len(sentences) < 4:
        return text
    target_idx = random.randint(1, max(1, len(sentences) // 2))
    s = sentences[target_idx]
    if len(s.split()) > 10 and s.endswith('.'):
        aside = random.choice(specifics)
        sentences[target_idx] = s[:-1] + aside + '.'
    return ' '.join(sentences)


# ===== NEW AGGRESSIVE POST‑PROCESSING FOR GENERAL CONTENT =====

def aggressive_burstiness(text: str) -> str:
    """Much more aggressive sentence splitting/merging + occasional fragments."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if len(sentences) < 3:
        return text

    new_sents = []
    i = 0
    while i < len(sentences):
        s = sentences[i].strip()
        wc = len(s.split())

        # Split ANY sentence > 18 words at a conjunction or comma (80% chance)
        if wc > 18 and random.random() < 0.8:
            split_at = None
            for conj in [' and ', ' but ', ' because ', ' so ', ' however,', ' although ', ' while ']:
                pos = s.lower().find(conj)
                if pos != -1 and pos > 8 and pos < len(s) - 8:
                    split_at = pos + len(conj.rstrip(','))
                    break
            if split_at is None:
                comma_pos = s.find(',')
                if comma_pos != -1 and comma_pos > 8:
                    split_at = comma_pos + 1
            if split_at:
                part1 = s[:split_at].rstrip(',').strip() + '.'
                part2 = s[split_at:].strip()
                if part2:
                    part2 = part2[0].upper() + part2[1:]
                    new_sents.extend([part1, part2])
                    i += 1
                    continue

        # Merge very short sentences (< 6 words) with next if possible
        if wc < 6 and i + 1 < len(sentences):
            next_s = sentences[i+1].strip()
            if len(next_s.split()) < 10:
                merged = s.rstrip('.!?') + ', ' + next_s[0].lower() + next_s[1:]
                new_sents.append(merged)
                i += 2
                continue

        new_sents.append(s)
        i += 1

    # 25% chance to insert a sentence fragment
    if random.random() < 0.25:
        idx = random.randint(0, len(new_sents)-1)
        frag = random.choice(["Exactly.", "Right.", "True.", "I know.", "Fair enough.", "No question."])
        new_sents.insert(idx, frag)

    return ' '.join(new_sents)


def inject_colloquialisms(text: str) -> str:
    """Replace formal transitions and add casual sentence starters."""
    # Hard replacements for common formal transitions
    text = re.sub(r'\bHowever,?\b', random.choice(["But", "Still,", "That said,"]), text, flags=re.IGNORECASE)
    text = re.sub(r'\bTherefore,?\b', random.choice(["So", "That means", "As a result"]), text, flags=re.IGNORECASE)
    text = re.sub(r'\bFurthermore,?\b', random.choice(["Plus,", "Also,", "And"]), text, flags=re.IGNORECASE)
    text = re.sub(r'\bMoreover,?\b', random.choice(["Plus,", "On top of that,", "Also,"]), text, flags=re.IGNORECASE)
    text = re.sub(r'\bIn addition,?\b', random.choice(["Also,", "Plus,", "And"]), text, flags=re.IGNORECASE)
    text = re.sub(r'\bConsequently,?\b', random.choice(["So,", "Because of that,", "That's why"]), text, flags=re.IGNORECASE)
    text = re.sub(r'\bNevertheless,?\b', random.choice(["Still,", "Even so,", "But"]), text, flags=re.IGNORECASE)

    # Insert casual starters in the middle of the text
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) > 3:
        idx = random.randint(1, len(sentences)-2)
        starter = random.choice(["Honestly, ", "Look, ", "I mean, ", "You know, ", "Actually, ", "Here's the thing: "])
        sentences[idx] = starter + sentences[idx][0].lower() + sentences[idx][1:]
    return ' '.join(sentences)


# Small thesaurus for common AI words
SYNONYM_MAP = {
    'important': ['key', 'crucial', 'vital', 'essential', 'big'],
    'significant': ['major', 'substantial', 'considerable', 'notable'],
    'demonstrate': ['show', 'prove', 'illustrate', 'highlight'],
    'provide': ['give', 'offer', 'supply', 'deliver'],
    'develop': ['build', 'create', 'form', 'put together'],
    'utilize': ['use', 'employ', 'apply'],
    'implement': ['put in place', 'roll out', 'carry out'],
    'facilitate': ['help', 'enable', 'make easier'],
    'numerous': ['many', 'countless', 'several', 'a lot of'],
    'prior to': ['before'],
    'subsequent': ['later', 'following'],
    'commence': ['start', 'begin'],
    'terminate': ['end', 'stop'],
}

def synonym_replacement(text: str) -> str:
    """Replace overused words with synonyms (40% chance per occurrence)."""
    words = text.split()
    new_words = []
    for w in words:
        lower = w.lower().strip('.,!?;:')
        if lower in SYNONYM_MAP and random.random() < 0.4:
            replacement = random.choice(SYNONYM_MAP[lower])
            # Preserve case
            if w[0].isupper():
                replacement = replacement.capitalize()
            # Reattach punctuation
            punct = ''
            if w[-1] in '.,!?;:':
                punct = w[-1]
            new_words.append(replacement + punct)
        else:
            new_words.append(w)
    return ' '.join(new_words)


def add_minor_imperfections(text: str) -> str:
    """Introduce tiny grammar/punctuation 'errors' that humans make."""
    # 20% chance to replace a period with a comma (creating a comma splice)
    if random.random() < 0.2:
        text = re.sub(r'\.\s+([A-Z])', r', \1', text, count=1)
    # 15% chance to remove an Oxford comma
    if random.random() < 0.15:
        text = re.sub(r', and', ' and', text, count=1)
    # 10% chance to add a random comma inside a sentence
    if random.random() < 0.1:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) > 1:
            idx = random.randint(0, len(sentences)-1)
            words = sentences[idx].split()
            if len(words) > 5:
                pos = random.randint(2, len(words)-2)
                words.insert(pos, ',')
                sentences[idx] = ' '.join(words)
        text = ' '.join(sentences)
    return text


# ─────────────────────────────────────────────
#  MAIN PIPELINE
# ─────────────────────────────────────────────

def build_system_prompt(tone, gptzero, originality, turnitin, zerogpt) -> str:
    base    = TONE_PROMPTS.get(tone, TONE_PROMPTS["Conversational & Raw"])
    targets = get_detector_instructions(gptzero, originality, turnitin, zerogpt)
    combined = base
    if targets:
        combined += f"\n\nADDITIONAL ANTI-DETECTION RULES:\n{targets}"
    combined += "\n\nFORBIDDEN WORDS (never use these): delve, utilize, leverage, paramount, landscape, realm, testament, moreover, furthermore, in conclusion, cutting-edge, game-changer, groundbreaking, pivotal, robust, seamlessly, foster, facilitate, comprehensive, innovative, transformative, synergy, ecosystem, paradigm.\n\nOutput ONLY the rewritten text."
    return combined


def humanize(text, tone, doc_type, client, model_id, num_passes, stealth, gptzero, originality, turnitin, zerogpt):

    # ── Formal document path: single-pass, restrained, no post-processing quirks ──
    if is_formal_doc(doc_type):
        formal_prompt = FORMAL_PROMPTS[doc_type]
        try:
            r = client.chat.completions.create(
                model=model_id,
                temperature=0.55,   # Low temp — we want controlled, not creative
                max_tokens=2500,
                top_p=0.85,
                messages=[
                    {"role": "system", "content": formal_prompt},
                    {"role": "user",   "content": f"Edit this:\n\n{text}"},
                ]
            )
            result = r.choices[0].message.content.strip()
            # Only run cliché removal for formal docs — no quirks, no burstiness scrambling
            if stealth:
                result = clean_cliches(result)
            return result
        except Exception as e:
            return f"Error: {e}"

    # ── General content path: full aggressive pipeline (4 passes, forced 70B) ──
    system_prompt = build_system_prompt(tone, gptzero, originality, turnitin, zerogpt)

    # Force the best model for general content
    general_model = "llama-3.3-70b-versatile"

    try:
        current_text = text

        # --- PASS 1: Wild expansion (high temp, add noise) ---
        r1 = client.chat.completions.create(
            model=general_model,
            temperature=1.5,
            max_tokens=3500,
            top_p=0.98,
            messages=[
                {"role": "system", "content": (
                    "You are a wildly creative human writer. Expand this text by about 40%. "
                    "Add a personal story, a vivid analogy, an opinion, and a rhetorical question. "
                    "Use very casual, conversational language. Vary sentence lengths like crazy. "
                    "Do NOT use any AI buzzwords. Output ONLY the expanded text."
                )},
                {"role": "user", "content": current_text},
            ]
        )
        expanded = r1.choices[0].message.content

        # --- PASS 2: Humanize with detector-specific instructions ---
        r2 = client.chat.completions.create(
            model=general_model,
            temperature=1.4,
            max_tokens=3000,
            top_p=0.96,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Rewrite and condense this to roughly the original length. Make it sound like a smart human wrote it casually:\n\n{expanded}"},
            ]
        )
        current_text = r2.choices[0].message.content

        # --- PASS 3: Rhythm & structure scrambler ---
        r3 = client.chat.completions.create(
            model=general_model,
            temperature=1.3,
            max_tokens=3000,
            top_p=0.94,
            messages=[
                {"role": "system", "content": (
                    "You are a sentence rhythm expert. Your task: make this text sound undeniably human.\n"
                    "- Rearrange sentence order within paragraphs if it feels natural.\n"
                    "- Ensure NO two consecutive sentences are the same length.\n"
                    "- Add 2-3 casual phrases: 'honestly', 'look', 'here's the thing', 'to be fair', 'I mean'.\n"
                    "- Replace any remaining formal transitions with casual ones (But, So, Plus, etc.).\n"
                    "- Break any parallel structure patterns.\n"
                    "- If a sentence feels too perfect, add a tiny imperfection (e.g., a comma splice or a slight run-on).\n"
                    "Do NOT add new facts. Output ONLY the result."
                )},
                {"role": "user", "content": current_text},
            ]
        )
        current_text = r3.choices[0].message.content

        # --- PASS 4: Final anti-detection polish (lower temp for coherence) ---
        r4 = client.chat.completions.create(
            model=general_model,
            temperature=1.0,
            max_tokens=3000,
            top_p=0.92,
            messages=[
                {"role": "system", "content": (
                    "You are an expert at evading AI detectors. Final polish:\n"
                    "- Eliminate any remaining overused transition words.\n"
                    "- Vary sentence length even more.\n"
                    "- Insert one tangential thought or a slight self-correction.\n"
                    "- Replace one or two common words with unexpected synonyms.\n"
                    "- Ensure contractions are used naturally.\n"
                    "Output ONLY the final version."
                )},
                {"role": "user", "content": current_text},
            ]
        )
        current_text = r4.choices[0].message.content

        # --- STEALTH POST-PROCESSING (only for general content) ---
        if stealth:
            current_text = clean_cliches(current_text)               # remove buzzwords
            current_text = aggressive_burstiness(current_text)       # extreme sentence variation
            current_text = inject_colloquialisms(current_text)       # casual tone
            current_text = synonym_replacement(current_text)         # shuffle vocabulary
            if originality:
                current_text = add_human_specificity(current_text)   # concrete details
            current_text = add_minor_imperfections(current_text)     # human‑like errors

        return current_text.strip()

    except Exception as e:
        return f"Error: {e}"


def cache_key(text, tone, doc_type, model, passes, stealth, gpt, ori, tur, zer, rand):
    seed = str(random.random()) if rand else ""
    return hashlib.md5(f"{text}{tone}{doc_type}{model}{passes}{stealth}{gpt}{ori}{tur}{zer}{seed}".encode()).hexdigest()


# ─────────────────────────────────────────────
#  UI
# ─────────────────────────────────────────────

st.title("🕵️ Authentica v3 — Multi-Detector Humanizer")
st.markdown(
    "Engineered to lower scores on **GPTZero**, **Originality.ai**, **Turnitin**, and **ZeroGPT**. "
    "Uses **document-type-aware** pipelines — formal docs get a restrained edit; general content gets the full stealth treatment (4 passes, high temp, heavy post‑proc)."
)

# Show active detector badges
badges = []
if target_gptzero:     badges.append('<span class="detector-badge badge-red">GPTZero</span>')
if target_originality: badges.append('<span class="detector-badge badge-red">Originality.ai</span>')
if target_turnitin:    badges.append('<span class="detector-badge badge-red">Turnitin</span>')
if target_zerogpt:     badges.append('<span class="detector-badge badge-red">ZeroGPT</span>')
st.markdown("**Targeting:** " + " ".join(badges), unsafe_allow_html=True)

st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.subheader("📥 Input")
    input_text = st.text_area(
        "Paste AI-generated text",
        height=380,
        placeholder="Paste your AI-written content here...",
    )
    word_count = len(input_text.split()) if input_text else 0
    st.caption(f"Word count: {word_count}")

with col2:
    st.subheader("📤 Output")
    output_area = st.empty()
    status_area = st.empty()

    if st.button("🚀 Run Humanizer", type="primary", use_container_width=True):
        if not api_key:
            st.error("Add your Groq API key in the sidebar.")
        elif not input_text.strip():
            st.warning("Paste some text to rewrite.")
        elif not any([target_gptzero, target_originality, target_turnitin, target_zerogpt]):
            st.warning("Select at least one target detector in the sidebar.")
        else:
            client = Groq(api_key=api_key)

            pass_label = "1-pass (restrained)" if is_formal_doc(doc_type) else "4-pass (aggressive)"
            with st.spinner(f"Running {pass_label} pipeline — {doc_type}..."):

                if 'cache' not in st.session_state:
                    st.session_state.cache = {}

                ck = cache_key(
                    input_text, tone, doc_type, selected_model_id, num_passes, stealth,
                    target_gptzero, target_originality, target_turnitin, target_zerogpt,
                    randomize
                )

                if ck in st.session_state.cache and not randomize:
                    result = st.session_state.cache[ck]
                else:
                    result = humanize(
                        input_text, tone, doc_type, client, selected_model_id,
                        num_passes, stealth,
                        target_gptzero, target_originality, target_turnitin, target_zerogpt
                    )
                    st.session_state.cache[ck] = result

            if result.startswith("Error:"):
                st.error(result)
            else:
                output_area.text_area("Result", value=result, height=380)
                out_wc = len(result.split())
                st.caption(f"Word count: {out_wc}")
                st.success(f"✅ Done! {pass_label} pipeline complete.")

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Pipeline",    "Restrained" if is_formal_doc(doc_type) else "Full Stealth")
                c2.metric("Passes",      1 if is_formal_doc(doc_type) else 4)
                c3.metric("Detectors",   sum([target_gptzero, target_originality, target_turnitin, target_zerogpt]))
                c4.metric("Post-proc",   "On" if stealth else "Off")

st.markdown("---")
with st.expander("📖 How it works — two pipelines explained"):
    st.markdown("""
    ### Document-Type-Aware Pipelines

    | Document Type | Pipeline | Temperature | Post-processing |
    |---|---|---|---|
    | **General Content** (Blog/Article/Essay) | Full 4-pass stealth | 1.0–1.5 | Aggressive burstiness + colloquialisms + synonyms + minor errors |
    | **Professional Email** | Single-pass restrained | 0.55 | Clichés only |
    | **Academic Writing** | Single-pass restrained | 0.55 | Clichés only |
    | **Cover Letter** | Single-pass restrained | 0.55 | Clichés only |

    **Why formal docs need a different pipeline:**
    Aggressive humanization (high temperature, sentence scrambling, casual injections) actively *hurts* formal writing.
    A professor or hiring manager will notice "Hey Dr. X" or fabricated personal stories immediately.
    The restrained pipeline only fixes actual AI tells — stiff phrasing, missing contractions, buzzwords — without touching structure or adding anything new.

    ### How each detector is beaten (General Content)

    | Detector | Primary Signal | This Tool's Fix |
    |---|---|---|
    | **GPTZero** | Low perplexity + low burstiness | High temp (1.5), extreme sentence length mixing, fragments |
    | **Originality.ai** | Semantic fingerprinting | Idea reordering, concrete specifics injected, idioms, synonym replacement |
    | **Turnitin** | Structural patterns + no personal voice | Paragraph asymmetry, opinion statements, colloquialisms |
    | **ZeroGPT** | Formal transitions + uniform clause lengths | All formal transitions replaced, contractions, minor errors |

    ### 4 manual tweaks that close the last gap

    1. **Add one real specific detail** — a number, date, or named example
    2. **Break paragraph symmetry** — split one long paragraph or combine two short ones
    3. **Turn one statement into a question** — "Why does this matter?" or "Sound familiar?"
    4. **Add one natural self-correction** — "or rather, what I mean is…" or a parenthetical aside
    """)

st.markdown("*Powered by Groq Cloud | Authentica v3 | Multi-Detector Engine*")
