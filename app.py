"""
app.py — Streamlit UI for the Multi-Source Research Agent.

Run with:
    .venv/Scripts/streamlit.exe run app.py
"""

# ── Standard library ─────────────────────────────────────────────────────────
import io
import sys
import threading
import time
from queue import Empty, Queue

# ── Third-party ──────────────────────────────────────────────────────────────
import streamlit as st

# ── Page config — must be the very first Streamlit call ──────────────────────
st.set_page_config(
    page_title="Research Agent",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =============================================================================
#  GLOBAL CSS & DARK THEME
# =============================================================================
st.markdown("""
<style>
/* ── Color Palette & Tokens ─────────────────────────────────────────────── */
:root {
    --bg:          #0a0c10;
    --card:        #10131d;
    --input-bg:    #151926;
    --accent:      #7c6eff;
    --accent-glow: rgba(124, 110, 255, 0.16);
    --teal:        #3ecfcf;
    --google:      #4285f4;
    --bing:        #00b4d8;
    --reddit:      #ff6b35;
    --green:       #22c55e;
    --amber:       #f59e0b;
    --red:         #ef4444;
    --t1:          #f0f2f8;
    --t2:          #8e93ad;
    --t3:          #424766;
    --border:      #1c2035;
    --border-lite: #272c48;
}

/* ── Base resets ────────────────────────────────────────────────────────── */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stSidebar"] {
    background: var(--bg) !important;
    color: var(--t1) !important;
}

#MainMenu, footer, header { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }
.block-container {
    padding-top: 1.8rem !important;
    padding-bottom: 3rem !important;
    max-width: 900px !important;
}

/* ── Micro-animations ──────────────────────────────────────────────────── */
@keyframes spin {
    to { transform: rotate(360deg); }
}
@keyframes pulse-ring {
    0%, 100% { box-shadow: 0 0 0 0 rgba(124, 110, 255, 0.45); }
    50%      { box-shadow: 0 0 0 7px rgba(124, 110, 255, 0); }
}
@keyframes dot-blink {
    0%, 80%, 100% { opacity: .2; transform: scale(.8); }
    40%           { opacity: 1;  transform: scale(1); }
}

/* ── Hero header ───────────────────────────────────────────────────────── */
.hero { text-align: center; padding: 1.2rem 1rem 0.4rem; }
.hero h1 {
    font-size: 2.6rem;
    font-weight: 800;
    background: linear-gradient(135deg, var(--accent) 0%, var(--teal) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 0 .35rem;
    letter-spacing: -.6px;
}
.hero .sub {
    color: var(--t2);
    font-size: 0.98rem;
    margin: 0;
}

/* ── Source badges ─────────────────────────────────────────────────────── */
.badges {
    display: flex;
    justify-content: center;
    gap: .65rem;
    flex-wrap: wrap;
    margin: .85rem 0 1.6rem;
}
.badge {
    display: inline-flex;
    align-items: center;
    gap: .4rem;
    padding: .28rem .85rem;
    border-radius: 999px;
    font-size: .74rem;
    font-weight: 700;
    letter-spacing: .4px;
}
.bg { background: rgba(66,133,244,.12); border: 1px solid rgba(66,133,244,.35); color: #6ea8fe; }
.bb { background: rgba(0,180,216,.12);  border: 1px solid rgba(0,180,216,.35);  color: #5dcfec; }
.br { background: rgba(255,107,53,.12); border: 1px solid rgba(255,107,53,.35); color: #ff9063; }

/* ── Search Input & Form ───────────────────────────────────────────────── */
[data-testid="stForm"] {
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
}
[data-testid="stTextInput"] input {
    background: var(--input-bg) !important;
    border: 1.5px solid var(--border-lite) !important;
    border-radius: 14px !important;
    color: var(--t1) !important;
    font-size: 1.02rem !important;
    padding: .85rem 1.15rem !important;
    transition: border-color .2s, box-shadow .2s;
}
[data-testid="stTextInput"] input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-glow) !important;
}
[data-testid="stTextInput"] input::placeholder { color: var(--t3) !important; }

/* ── Primary Submit Button ─────────────────────────────────────────────── */
[data-testid="stFormSubmitButton"] > button {
    width: 100%;
    background: linear-gradient(135deg, var(--accent), #5648d8) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 14px !important;
    font-size: .95rem !important;
    font-weight: 700 !important;
    padding: .85rem 1.4rem !important;
    letter-spacing: .3px;
    transition: opacity .2s, transform .12s;
}
[data-testid="stFormSubmitButton"] > button:hover {
    opacity: .9;
    transform: translateY(-1px);
}
[data-testid="stFormSubmitButton"] > button:active {
    transform: translateY(0);
}
[data-testid="stFormSubmitButton"] > button:disabled {
    opacity: .4 !important;
}

/* ── Secondary Buttons & Suggested Question Pills ──────────────────────── */
.stButton > button[kind="secondary"],
.stButton > button[data-testid="baseButton-secondary"] {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    color: var(--t2) !important;
    border-radius: 12px !important;
    font-size: .84rem !important;
    font-weight: 500 !important;
    padding: .65rem 1rem !important;
    text-align: left !important;
    line-height: 1.4 !important;
    transition: all .2s !important;
}
.stButton > button[kind="secondary"]:hover,
.stButton > button[data-testid="baseButton-secondary"]:hover {
    border-color: var(--accent) !important;
    color: var(--t1) !important;
    background: var(--input-bg) !important;
    transform: translateY(-1px);
}

/* ── Pipeline Stepper Card (Rock-solid, zero flicker) ──────────────────── */
.pipe-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 1.5rem 1.8rem;
    margin: .5rem 0 1.2rem;
}
.pipe-hdr {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.1rem;
}
.pipe-title {
    font-size: .7rem;
    font-weight: 800;
    letter-spacing: 1.4px;
    text-transform: uppercase;
    color: var(--t2);
}
.elapsed-badge {
    display: inline-flex;
    align-items: center;
    gap: .4rem;
    background: var(--accent-glow);
    border: 1px solid rgba(124, 110, 255, 0.3);
    border-radius: 999px;
    padding: .24rem .75rem;
    font-size: .78rem;
    font-weight: 700;
    color: var(--accent);
}
.prog-wrap {
    background: var(--border);
    border-radius: 999px;
    height: 4px;
    width: 100%;
    margin: .4rem 0 1.4rem;
    overflow: hidden;
}
.prog-fill {
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, var(--accent), var(--teal));
    transition: width .6s ease;
}
.prog-fill-err {
    background: linear-gradient(90deg, var(--amber), var(--red)) !important;
}

/* ── Stepper row layout ────────────────────────────────────────────────── */
.step-row {
    display: flex;
    align-items: flex-start;
    position: relative;
}
.step-row:not(:last-child)::after {
    content: '';
    position: absolute;
    left: 17px;
    top: 38px;
    height: calc(100% - 40px);
    width: 2px;
    background: var(--border-lite);
    z-index: 1;
}
.step-dot {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    font-size: .86rem;
    font-weight: 700;
    margin: 0 14px 0 0;
    position: relative;
    z-index: 2;
    background: #10131d;
}
.dot-idle   { background: #131622; border: 2px solid var(--border-lite); color: var(--t3); }
.dot-active {
    background: #151829;
    border: 2px solid var(--accent);
    color: var(--accent);
    animation: pulse-ring 1.6s ease infinite;
}
.dot-done   { background: #0c1c16; border: 2px solid var(--green); color: var(--green); }
.dot-err    { background: #221115; border: 2px solid var(--red);   color: var(--red); }

.step-body  { flex: 1; padding-bottom: 1.35rem; }
.step-label { font-weight: 700; font-size: .92rem; }
.step-desc  { font-size: .76rem; color: var(--t2); margin-top: .15rem; }

.spinner {
    width: 15px;
    height: 15px;
    border: 2px solid rgba(124, 110, 255, 0.25);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin .75s linear infinite;
    display: inline-block;
}
.blink-dots { margin-top: .4rem; }
.blink-dots span {
    display: inline-block;
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: var(--accent);
    margin: 0 2px;
    animation: dot-blink 1.4s infinite;
}
.blink-dots span:nth-child(2) { animation-delay: .22s; }
.blink-dots span:nth-child(3) { animation-delay: .44s; }

/* ── Log Console ───────────────────────────────────────────────────────── */
.log-box {
    background: #07090f;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: .9rem 1.1rem;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: .76rem;
    line-height: 1.8;
    max-height: 220px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-word;
}
.l-ok   { color: var(--green); }
.l-info { color: #9b8fff; }
.l-warn { color: var(--amber); }
.l-dim  { color: var(--t2); }
.l-txt  { color: #c0c4d8; }

/* ── Container Cards & Badges ──────────────────────────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 18px !important;
    padding: 1.5rem 1.8rem !important;
    margin-bottom: 1rem !important;
}

.p-lbl {
    font-size: .68rem;
    font-weight: 800;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    padding: .25rem .7rem;
    border-radius: 999px;
    display: inline-block;
    margin-bottom: .8rem;
}
.lbl-fin  { background: var(--accent-glow); color: var(--accent); border: 1px solid rgba(124, 110, 255, 0.3); }
.lbl-g    { background: rgba(66, 133, 244, 0.16); color: #6ea8fe; border: 1px solid rgba(66, 133, 244, 0.3); }
.lbl-b    { background: rgba(0, 180, 216, 0.16);  color: #5dcfec; border: 1px solid rgba(0, 180, 216, 0.3); }
.lbl-r    { background: rgba(255, 107, 53, 0.16); color: #ff9063; border: 1px solid rgba(255, 107, 53, 0.3); }

/* ── Typography Polish (Dark Mode High Contrast) ───────────────────────── */
h2, h3 {
    color: #ffffff !important;
    font-weight: 700 !important;
    letter-spacing: -0.3px !important;
    margin-top: 1.2rem !important;
    margin-bottom: 0.6rem !important;
}
p, li {
    color: #d1d5e5 !important;
    line-height: 1.68 !important;
    font-size: 0.96rem !important;
}
strong {
    color: #ffffff !important;
    font-weight: 700 !important;
}
code {
    background: #181d2c !important;
    color: #3ecfcf !important;
    border-radius: 6px !important;
    padding: 2px 6px !important;
}
blockquote {
    border-left: 3px solid var(--accent) !important;
    background: rgba(124, 110, 255, 0.08) !important;
    padding: 0.6rem 1rem !important;
    border-radius: 0 8px 8px 0 !important;
    color: var(--t2) !important;
}

/* ── Tabs & Expanders ──────────────────────────────────────────────────── */
[data-testid="stTabs"] button[role="tab"] {
    color: var(--t2) !important;
    font-weight: 600 !important;
    padding: .65rem 1.2rem !important;
    border-radius: 8px 8px 0 0 !important;
    transition: color .2s !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
    background: var(--accent-glow) !important;
}
[data-testid="stExpander"] {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
}
[data-testid="stExpander"] summary {
    color: var(--t1) !important;
    font-weight: 600;
    font-size: .88rem;
}

/* ── Empty State ───────────────────────────────────────────────────────── */
.empty {
    text-align: center;
    padding: 2.8rem 1rem 1.5rem;
}
.empty-icon { font-size: 3rem; opacity: .25; margin-bottom: .8rem; }
.empty-h    { font-size: 1.12rem; font-weight: 700; color: #a4a9c6; }
.empty-p    { font-size: .88rem; color: var(--t3); margin-top: .35rem; }

hr { border-color: var(--border) !important; margin: 1.4rem 0 !important; }
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-lite); border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# =============================================================================
#  SESSION STATE INITIALIZATION
# =============================================================================

def _init_state() -> None:
    defaults = {
        "running":              False,
        "log_lines":            [],
        "google_analysis":      None,
        "bing_analysis":        None,
        "reddit_analysis":      None,
        "selected_reddit_urls": None,
        "final_answer":         None,
        "elapsed":              0.0,
        "search_count":         0,
        "error":                None,
        "last_query":           "",
        "active_query":         "",
        "input_key":            0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()


# =============================================================================
#  PIPELINE STAGE DEFINITION & STATUS LOGIC
# =============================================================================

_STAGES = [
    ("search",      "1", "Parallel Web Search",     "Querying Google, Bing &amp; Reddit simultaneously"),
    ("reddit_deep", "2", "Reddit Deep-Dive",         "Extracting high-signal threads &amp; community comments"),
    ("analyze",     "3", "Multi-Source Analysis",    "Extracting facts, consensus &amp; expert viewpoints"),
    ("synthesize",  "4", "Synthesized Intelligence", "Combining all intelligence into a structured answer"),
]


def _stage_statuses(logs: list[str], final_done: bool, has_error: bool = False) -> dict[str, str]:
    joined = "\n".join(logs)

    def has(*patterns):
        return any(p in joined for p in patterns)

    s = {k: "idle" for k, *_ in _STAGES}

    # Stage 1: Search — count completion across all engines (either results or 0 found)
    n_search_done = sum(1 for p in ["Google:", "Bing:", "Reddit:"] if p in joined)
    if has("Searching Google", "Searching Bing", "Searching Reddit", "🚀 Pipeline started"):
        s["search"] = "active"
    if n_search_done >= 2 or has("Selected URLs", "Skipping Reddit URL selection", "No Reddit URLs", "Fetching comments"):
        s["search"] = "done"

    # Stage 2: Reddit deep-dive
    if has("Selected URLs", "📥 Fetching", "Reddit post retrieval"):
        s["reddit_deep"] = "active"
    if has("✅ Reddit posts:", "No Reddit URLs", "Skipping Reddit URL selection", "returned no data", "No Reddit URLs to retrieve"):
        s["reddit_deep"] = "done"

    # Stage 3: Source analysis
    if has("🔍 Analyzing"):
        s["analyze"] = "active"
    if has("🧠 Synthesizing"):
        s["analyze"] = "done"

    # Stage 4: Synthesis
    if has("🧠 Synthesizing"):
        s["synthesize"] = "active"
    if final_done:
        s["synthesize"] = "done"

    # Fallback cascade: once downstream stages start, all prior stages are done
    if has("🔍 Analyzing", "🧠 Synthesizing") or final_done:
        s["search"] = "done"
        s["reddit_deep"] = "done"

    if has("🧠 Synthesizing") or final_done:
        s["analyze"] = "done"

    if final_done:
        s["synthesize"] = "done"

    # If halted by error, turn any currently active stage into error indicator
    if has_error:
        for k in s:
            if s[k] == "active":
                s[k] = "error"

    return s


def _pipeline_html(logs: list[str], elapsed: float, final_done: bool, has_error: bool = False) -> str:
    statuses = _stage_statuses(logs, final_done, has_error)

    vals = {"idle": 0, "active": 0.5, "done": 1, "error": 0.5}
    pct = int(sum(vals[statuses[k]] for k, *_ in _STAGES) / len(_STAGES) * 100)

    rows_html = ""
    for key, step_num, label, desc in _STAGES:
        st_val = statuses[key]

        if st_val == "active":
            dot = '<div class="step-dot dot-active"><span class="spinner"></span></div>'
            nc = "var(--t1)"
            extra = '<div class="blink-dots"><span></span><span></span><span></span></div>'
        elif st_val == "done":
            dot = '<div class="step-dot dot-done">&#10003;</div>'
            nc = "var(--green)"
            extra = ""
        elif st_val == "error":
            dot = '<div class="step-dot dot-err">&#10007;</div>'
            nc = "var(--red)"
            extra = ""
        else:
            dot = f'<div class="step-dot dot-idle">{step_num}</div>'
            nc = "var(--t3)"
            extra = ""

        rows_html += (
            f'<div class="step-row">'
            f'{dot}'
            f'<div class="step-body">'
            f'<div class="step-label" style="color:{nc}">{label}</div>'
            f'<div class="step-desc">{desc}</div>'
            f'{extra}'
            f'</div>'
            f'</div>'
        )

    if has_error:
        title = "Research interrupted &#9888;"
        prog_class = "prog-fill prog-fill-err"
    elif final_done:
        title = "Research complete &#10024;"
        prog_class = "prog-fill"
    else:
        title = "Agent is researching&hellip;"
        prog_class = "prog-fill"

    return (
        f'<div class="pipe-card">'
        f'<div class="pipe-hdr">'
        f'<span class="pipe-title">{title}</span>'
        f'<span class="elapsed-badge">&#9201; {elapsed:.1f}s</span>'
        f'</div>'
        f'<div class="prog-wrap"><div class="{prog_class}" style="width:{pct}%"></div></div>'
        f'<div>{rows_html}</div>'
        f'</div>'
    )


def _log_console_html(lines: list[str]) -> str:
    def classify(line: str) -> str:
        if any(c in line for c in ["✅", "🎉"]):             return "l-ok"
        if any(c in line for c in ["🚀", "🔍", "🧠", "📥"]): return "l-info"
        if any(c in line for c in ["⚠️", "❌", "❓"]):       return "l-warn"
        if any(c in line for c in ["⏳", "🔄", "ℹ️"]):       return "l-dim"
        return "l-txt"

    def safe(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    inner = "".join(
        f'<div class="{classify(str(l))}">{safe(str(l))}</div>'
        for l in lines
    ) or '<span style="color:var(--t3)">Waiting for agent output&hellip;</span>'

    return f'<div class="log-box">{inner}</div>'


# =============================================================================
#  BACKGROUND WORKER THREAD
# =============================================================================

def _run_research(question: str, log_q: Queue, result_q: Queue) -> None:
    old = sys.stdout
    worker_thread_id = threading.get_ident()

    class _Capture(io.StringIO):
        def write(self, s: str) -> int:
            if threading.get_ident() == worker_thread_id:
                if s and s.strip():
                    # Split multiline blocks so each line renders distinctly in console
                    for line in s.splitlines():
                        trimmed = line.strip()
                        if trimmed:
                            log_q.put(trimmed)
            try:
                old.write(s)
                old.flush()
            except Exception:
                pass
            return len(s) if s else 0

    sys.stdout = _Capture()
    try:
        from agent import graph

        state = {
            "messages":             [{"role": "user", "content": question}],
            "user_question":        question,
            "google_results":       None,
            "bing_results":         None,
            "reddit_results":       None,
            "selected_reddit_urls": None,
            "reddit_post_data":     None,
            "google_analysis":      None,
            "bing_analysis":        None,
            "reddit_analysis":      None,
            "final_answer":         None,
        }
        log_q.put("🚀 Pipeline started — launching parallel searches…")
        final = graph.invoke(state)
        result_q.put({"ok": True, "state": final})
    except Exception as exc:  # noqa: BLE001
        result_q.put({"ok": False, "error": str(exc)})
    finally:
        sys.stdout = old


# =============================================================================
#  LAUNCH RESEARCH HELPER
# =============================================================================

def _launch_research(query_text: str) -> None:
    st.session_state.active_query = query_text
    st.session_state.input_key += 1
    st.session_state.update({
        "running":              True,
        "log_lines":            [],
        "google_analysis":      None,
        "bing_analysis":        None,
        "reddit_analysis":      None,
        "selected_reddit_urls": None,
        "final_answer":         None,
        "elapsed":              0.0,
        "error":                None,
        "last_query":           query_text,
    })
    st.session_state.search_count += 1

    log_q: Queue = Queue()
    result_q: Queue = Queue()
    st.session_state["_log_q"] = log_q
    st.session_state["_result_q"] = result_q
    st.session_state["_start_time"] = time.time()

    threading.Thread(
        target=_run_research,
        args=(query_text, log_q, result_q),
        daemon=True,
    ).start()

    st.rerun()


# =============================================================================
#  ISOLATED FRAGMENT FOR LIVE UPDATES  (Zero page blink)
# =============================================================================

@st.fragment(run_every=1.0)
def _live_tracker_fragment():
    """Reruns independently every 1.0s without touching the rest of the page."""
    log_q = st.session_state.get("_log_q")
    result_q = st.session_state.get("_result_q")
    start = st.session_state.get("_start_time", time.time())

    # Drain log queue
    if log_q:
        while True:
            try:
                st.session_state.log_lines.append(log_q.get_nowait())
            except Empty:
                break

    # Check for result
    done = False
    if result_q:
        try:
            res = result_q.get_nowait()
            done = True
            if res.get("ok"):
                fs = res["state"]
                st.session_state.google_analysis      = fs.get("google_analysis")
                st.session_state.bing_analysis        = fs.get("bing_analysis")
                st.session_state.reddit_analysis      = fs.get("reddit_analysis")
                st.session_state.selected_reddit_urls = fs.get("selected_reddit_urls")
                st.session_state.final_answer         = fs.get("final_answer")
            else:
                st.session_state.error = res.get("error", "Unknown error")
        except Empty:
            pass

    st.session_state.elapsed = time.time() - start

    if done:
        st.session_state.running = False
        st.rerun(scope="app")
        return

    # Render active progress in-place
    st.html(_pipeline_html(st.session_state.log_lines, st.session_state.elapsed, False))

    with st.expander("&#128225; Raw Agent Logs", expanded=False):
        st.html(_log_console_html(st.session_state.log_lines))

    # Stop button during active research
    col_stop, _ = st.columns([1, 4])
    with col_stop:
        if st.button("⏹ Stop Research", type="secondary", use_container_width=True):
            st.session_state.running = False
            st.session_state.error = "Research was cancelled by the user."
            st.rerun(scope="app")


# =============================================================================
#  MAIN PAGE RENDERING
# =============================================================================

# ── Hero ──────────────────────────────────────────────────────────────────────
st.html(
    '<div class="hero">'
    '<h1>&#128300; Research Agent</h1>'
    '<p class="sub">Parallel multi-source intelligence &middot; Google &middot; Bing &middot; Reddit &middot; AI synthesis</p>'
    '</div>'
    '<div class="badges">'
    '<span class="badge bg">&#128309; Google Search</span>'
    '<span class="badge bb">&#128311; Bing Search</span>'
    '<span class="badge br">&#128992; Reddit Discussions</span>'
    '</div>'
)

# ── Search Form (Enter key automatically submits!) ────────────────────────────
with st.form("search_form", border=False):
    col_q, col_btn = st.columns([5, 1], gap="small")
    with col_q:
        query = st.text_input(
            label="query",
            label_visibility="collapsed",
            key=f"query_input_{st.session_state.input_key}",
            value=st.session_state.get("active_query", ""),
            placeholder="Ask anything… e.g. 'Will AI agents replace software developers?'",
            disabled=st.session_state.running,
        )
    with col_btn:
        search_clicked = st.form_submit_button(
            "Search" if not st.session_state.running else "Searching…",
            disabled=st.session_state.running,
            use_container_width=True,
        )

# ── Launch research logic on Form Submit ──────────────────────────────────────
if search_clicked:
    if query and query.strip():
        _launch_research(query.strip())
    else:
        st.warning("Please enter a research question first.")


# =============================================================================
#  BODY STATE: RUNNING vs COMPLETED vs EMPTY
# =============================================================================

if st.session_state.running:
    # Live fragment updates independently — zero full-page reload
    _live_tracker_fragment()

elif st.session_state.final_answer or st.session_state.log_lines or st.session_state.error:
    # ── Completed or Halted View ───────────────────────────────────────────────

    # Header bar with query recap & new search button
    q_col, btn_col = st.columns([5, 1])
    with q_col:
        if st.session_state.last_query:
            st.markdown(f"**Research query:** `{st.session_state.last_query}`")
    with btn_col:
        if st.button("➕ New Query", type="secondary", use_container_width=True):
            st.session_state.active_query = ""
            st.session_state.input_key += 1
            st.session_state.update({
                "final_answer":         None,
                "log_lines":            [],
                "google_analysis":      None,
                "bing_analysis":        None,
                "reddit_analysis":      None,
                "selected_reddit_urls": None,
                "error":                None,
                "last_query":           "",
            })
            st.rerun()

    # Completed or error stepper
    has_err = bool(st.session_state.error)
    is_done = bool(st.session_state.final_answer)
    st.html(_pipeline_html(st.session_state.log_lines, st.session_state.elapsed, is_done, has_err))

    with st.expander("&#128225; Raw Agent Logs", expanded=False):
        st.html(_log_console_html(st.session_state.log_lines))

    st.markdown("<hr>", unsafe_allow_html=True)

    if st.session_state.error:
        st.error(f"❌  {st.session_state.error}")

    if st.session_state.final_answer:
        # Synthesized Answer Card
        with st.container(border=True):
            st.html('<div class="p-lbl lbl-fin">&#10024; Synthesized Research Report</div>')
            st.markdown(st.session_state.final_answer)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### &#128202; Source Evidence &amp; Analyses")

        tab_g, tab_b, tab_r = st.tabs(["&#128309; Google Search", "&#128311; Bing Search", "&#128992; Reddit Community"])

        with tab_g:
            with st.container(border=True):
                st.html('<div class="p-lbl lbl-g">&#128309; Google Search Analysis</div>')
                st.markdown(st.session_state.google_analysis or "_No Google analysis available._")

        with tab_b:
            with st.container(border=True):
                st.html('<div class="p-lbl lbl-b">&#128311; Bing Search Analysis</div>')
                st.markdown(st.session_state.bing_analysis or "_No Bing analysis available._")

        with tab_r:
            with st.container(border=True):
                st.html('<div class="p-lbl lbl-r">&#128992; Reddit Community Perspectives</div>')
                st.markdown(st.session_state.reddit_analysis or "_No Reddit community analysis available._")

                if st.session_state.get("selected_reddit_urls"):
                    st.markdown("---")
                    st.markdown("**📌 Key Reddit Threads Deep-Dived:**")
                    for u in st.session_state.selected_reddit_urls:
                        if isinstance(u, str) and u.strip():
                            full_u = u.strip() if u.strip().startswith("http") else f"https://www.reddit.com{u.strip()}" if u.strip().startswith("/") else f"https://www.reddit.com/{u.strip()}"
                            st.markdown(f"- [{full_u}]({full_u})")

else:
    # ── Empty Initial State with Sample Query Pills ───────────────────────────
    st.html(
        '<div class="empty">'
        '<div class="empty-icon">&#128269;</div>'
        '<div class="empty-h">Ask anything to begin multi-source research</div>'
        '<div class="empty-p">The agent concurrently queries Google, Bing &amp; Reddit,<br>'
        'deep-dives into top community discussions, and synthesises an authoritative report.</div>'
        '</div>'
    )

    st.markdown("<div style='text-align:center; margin-bottom:.8rem; font-size:.82rem; font-weight:700; color:var(--t3); text-transform:uppercase; letter-spacing:1px;'>💡 Suggested Research Questions</div>", unsafe_allow_html=True)

    samples = [
        "🤖 Will AI agents replace software developers in the next 5 years?",
        "⚡ DeepSeek-R1 vs OpenAI o3-mini: technical strengths & differences",
        "📈 Latest breakthroughs in quantum computing hardware in 2025",
        "🔐 Best self-hosted open-source password managers compared",
    ]

    s_col1, s_col2 = st.columns(2)
    for idx, prompt_text in enumerate(samples):
        target_col = s_col1 if idx % 2 == 0 else s_col2
        with target_col:
            if st.button(prompt_text, key=f"sample_{idx}", type="secondary", use_container_width=True):
                # Click immediately launches research for this query
                _launch_research(prompt_text)
