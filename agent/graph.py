"""
agent/graph.py

LangGraph research pipeline.

Runs three parallel web searches (Google, Bing, Reddit), deep-dives into
Reddit discussions, analyses each source concurrently, and synthesises
a single, unified research report.

Public surface:
    graph  — compiled LangGraph StateGraph ready to call with .invoke()
"""

import sys
from typing import Annotated, Any, TypedDict

# Ensure UTF-8 output encoding for emojis on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from agent.prompts import (
    get_bing_analysis_messages,
    get_google_analysis_messages,
    get_reddit_analysis_messages,
    get_reddit_url_analysis_messages,
    get_synthesis_messages,
)
from agent.snapshot_operations import _safe_print
from agent.web_operations import reddit_post_retrieval, reddit_search_api, serp_search

load_dotenv()

# ── Graph state ───────────────────────────────────────────────────────────────

class State(TypedDict):
    messages:             Annotated[list, add_messages]
    user_question:        str | None
    google_results:       dict | str | None
    bing_results:         dict | str | None
    reddit_results:       dict | str | None
    selected_reddit_urls: list[str] | None
    reddit_post_data:     list | dict | None
    google_analysis:      str | None
    bing_analysis:        str | None
    reddit_analysis:      str | None
    final_answer:         str | None


# ── Structured output schema ──────────────────────────────────────────────────

class RedditURLAnalysisInput(BaseModel):
    selected_urls: list[str] = Field(
        default_factory=list,
        description=(
            "List of up to 3 Reddit URLs most relevant to the user's question. "
            "Only include URLs that are directly useful. Return an empty list if none are relevant."
        ),
    )


# ── LLM initialisation ────────────────────────────────────────────────────────
llm = init_chat_model(
    "gemini-3.8-flash",
    model_provider="google_genai",
)

structured_llm = llm.with_structured_output(RedditURLAnalysisInput)


# ── Utilities ─────────────────────────────────────────────────────────────────

def _extract_content(reply: Any) -> str:
    """
    Safely extract plain text from an LLM reply.

    Handles simple string content, message objects, and structured content blocks
    (e.g. ``[{'type': 'text', 'text': '...', ...}]``) returned by some providers.
    """
    content = getattr(reply, "content", reply)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    texts.append(block.get("text", ""))
                elif "text" in block:
                    texts.append(str(block["text"]))
            elif hasattr(block, "text"):
                texts.append(str(getattr(block, "text")))
            elif isinstance(block, str):
                texts.append(block)
        return "\n".join(filter(None, texts))
    return str(content) if content is not None else ""


def _format_serp_for_prompt(results: dict | str | None) -> str:
    """Format SERP results dictionary into clean readable text for the LLM."""
    if not results:
        return "No search results available."
    if not isinstance(results, dict):
        return str(results)

    lines: list[str] = []
    knowledge = results.get("knowledge")
    if knowledge and isinstance(knowledge, dict):
        title = knowledge.get("title") or knowledge.get("heading") or "Knowledge Info"
        desc = knowledge.get("description") or knowledge.get("snippet") or ""
        lines.append(f"**Knowledge Graph:** {title}\n{desc}")

    organic = results.get("organic")
    if organic and isinstance(organic, list):
        lines.append("**Organic Search Results:**")
        for i, item in enumerate(organic[:10], 1):
            if isinstance(item, dict):
                title = item.get("title", "No Title")
                link = item.get("link", "")
                snippet = item.get("description") or item.get("snippet") or ""
                lines.append(f"{i}. [{title}]({link})\n   Snippet: {snippet}")

    return "\n\n".join(lines) if lines else "No search results available."


def _format_reddit_results_for_prompt(reddit_results: dict | str | None) -> str:
    """Format Reddit search results into clean titles and URLs for prompt."""
    if not reddit_results:
        return "No Reddit search results."
    if not isinstance(reddit_results, dict):
        return str(reddit_results)

    parsed = reddit_results.get("parsed_data", [])
    if not parsed:
        return "No Reddit posts found."

    lines: list[str] = []
    for i, item in enumerate(parsed[:15], 1):
        if isinstance(item, dict):
            title = item.get("title", "Untitled")
            url = item.get("url", "")
            lines.append(f"{i}. Title: {title}\n   URL: {url}")
    return "\n".join(lines) if lines else "No Reddit posts found."


def _format_reddit_comments_for_prompt(comments: list | dict | None) -> str:
    """Format retrieved Reddit comments cleanly for analysis."""
    if not comments:
        return "No comment details available."
    if isinstance(comments, dict):
        comments = comments.get("comments", [])
    if not isinstance(comments, list):
        return str(comments)

    lines: list[str] = []
    for i, c in enumerate(comments[:25], 1):
        if isinstance(c, dict):
            content = (c.get("content") or c.get("comment") or "").strip()
            date = c.get("date") or ""
            if content:
                date_str = f" (Posted: {date})" if date else ""
                lines.append(f"Comment {i}{date_str}:\n{content}")
    return "\n\n".join(lines) if lines else "No comment details available."


# ── Graph nodes ───────────────────────────────────────────────────────────────

def google_search(state: State) -> dict:
    user_question = state.get("user_question", "") or ""
    _safe_print(f"Searching Google for: {user_question}")

    google_results = serp_search(user_question, engine="google")

    if google_results and isinstance(google_results, dict):
        count = len(google_results.get("organic", []))
        _safe_print(f"✅ Google: retrieved {count} results")
    else:
        _safe_print("⚠️  Google: no results returned")

    return {"google_results": google_results}


def bing_search(state: State) -> dict:
    user_question = state.get("user_question", "") or ""
    _safe_print(f"Searching Bing for: {user_question}")

    bing_results = serp_search(user_question, engine="bing")

    if bing_results and isinstance(bing_results, dict):
        count = len(bing_results.get("organic", []))
        _safe_print(f"✅ Bing: retrieved {count} results")
    else:
        _safe_print("⚠️  Bing: no results returned")

    return {"bing_results": bing_results}


def reddit_search(state: State) -> dict:
    user_question = state.get("user_question", "") or ""
    _safe_print(f"Searching Reddit for: {user_question}")

    reddit_results = reddit_search_api(user_question)

    if reddit_results and isinstance(reddit_results, dict):
        total = reddit_results.get("total_found", 0)
        _safe_print(f"✅ Reddit: found {total} posts")
    else:
        _safe_print("⚠️  Reddit: no results returned")

    return {"reddit_results": reddit_results}


def analyze_reddit_posts(state: State) -> dict:
    user_question  = state.get("user_question", "") or ""
    reddit_results = state.get("reddit_results")

    if not reddit_results or not isinstance(reddit_results, dict) or not reddit_results.get("parsed_data"):
        _safe_print("⚠️  Skipping Reddit URL selection — no search results")
        return {"selected_reddit_urls": []}

    formatted_reddit = _format_reddit_results_for_prompt(reddit_results)
    messages = get_reddit_url_analysis_messages(user_question, formatted_reddit)

    try:
        analysis = structured_llm.invoke(messages)
        raw_urls = getattr(analysis, "selected_urls", []) if analysis else []

        # Clean and ensure absolute URLs
        selected_urls: list[str] = []
        for raw_u in raw_urls:
            if isinstance(raw_u, str) and raw_u.strip():
                u = raw_u.strip()
                if not u.startswith("http"):
                    u = f"https://www.reddit.com{u}" if u.startswith("/") else f"https://www.reddit.com/{u}"
                if u not in selected_urls:
                    selected_urls.append(u)

        selected_urls = selected_urls[:3]  # hard cap at 3

        if selected_urls:
            _safe_print("Selected URLs:")
            for i, url in enumerate(selected_urls, 1):
                _safe_print(f"    {i}. {url}")
        else:
            _safe_print("ℹ️  No Reddit URLs selected for deep retrieval")

    except Exception as exc:
        _safe_print(f"⚠️  Reddit URL selection failed: {exc}")
        selected_urls = []

    return {"selected_reddit_urls": selected_urls}


def retrieve_reddit_posts(state: State) -> dict:
    selected_urls = state.get("selected_reddit_urls", []) or []

    if not selected_urls:
        _safe_print("ℹ️  No Reddit URLs to retrieve — skipping post fetching")
        return {"reddit_post_data": []}

    _safe_print(f"📥 Fetching comments for {len(selected_urls)} Reddit post(s)…")

    reddit_post_data = reddit_post_retrieval(selected_urls)

    if reddit_post_data and isinstance(reddit_post_data, dict) and reddit_post_data.get("total_found", 0) > 0:
        total = reddit_post_data.get("total_found", 0)
        _safe_print(f"✅ Reddit posts: retrieved {total} comment(s)")
        comments_list = reddit_post_data.get("comments", [])
    else:
        _safe_print("⚠️  Reddit post retrieval returned no data — analysis will use search titles only")
        comments_list = []

    return {"reddit_post_data": comments_list}


def analyze_google_results(state: State) -> dict:
    _safe_print("🔍 Analyzing Google results…")

    user_question = state.get("user_question", "") or ""
    google_results = state.get("google_results")

    if not google_results or not isinstance(google_results, dict) or not (google_results.get("organic") or google_results.get("knowledge")):
        return {"google_analysis": "No Google search results were available for this query."}

    formatted = _format_serp_for_prompt(google_results)
    messages = get_google_analysis_messages(user_question, formatted)

    try:
        reply = llm.invoke(messages)
        return {"google_analysis": _extract_content(reply)}
    except Exception as exc:
        _safe_print(f"⚠️  Google analysis error: {exc}")
        return {"google_analysis": f"Google analysis could not be completed: {exc}"}


def analyze_bing_results(state: State) -> dict:
    _safe_print("🔍 Analyzing Bing results…")

    user_question = state.get("user_question", "") or ""
    bing_results  = state.get("bing_results")

    if not bing_results or not isinstance(bing_results, dict) or not (bing_results.get("organic") or bing_results.get("knowledge")):
        return {"bing_analysis": "No Bing search results were available for this query."}

    formatted = _format_serp_for_prompt(bing_results)
    messages = get_bing_analysis_messages(user_question, formatted)

    try:
        reply = llm.invoke(messages)
        return {"bing_analysis": _extract_content(reply)}
    except Exception as exc:
        _safe_print(f"⚠️  Bing analysis error: {exc}")
        return {"bing_analysis": f"Bing analysis could not be completed: {exc}"}


def analyze_reddit_results(state: State) -> dict:
    _safe_print("🔍 Analyzing Reddit results…")

    user_question   = state.get("user_question", "") or ""
    reddit_results  = state.get("reddit_results")
    reddit_post_data = state.get("reddit_post_data")

    has_results = bool(reddit_results and isinstance(reddit_results, dict) and reddit_results.get("parsed_data"))
    has_posts = bool(reddit_post_data)

    if not has_results and not has_posts:
        return {"reddit_analysis": "No Reddit discussions were available for this query."}

    formatted_results = _format_reddit_results_for_prompt(reddit_results)
    formatted_comments = _format_reddit_comments_for_prompt(reddit_post_data)

    messages = get_reddit_analysis_messages(
        user_question, formatted_results, formatted_comments
    )

    try:
        reply = llm.invoke(messages)
        return {"reddit_analysis": _extract_content(reply)}
    except Exception as exc:
        _safe_print(f"⚠️  Reddit analysis error: {exc}")
        return {"reddit_analysis": f"Reddit analysis could not be completed: {exc}"}


def synthesize_analyses(state: State) -> dict:
    _safe_print("🧠 Synthesizing all results…")

    user_question   = state.get("user_question", "") or ""
    google_analysis = state.get("google_analysis") or "Not available."
    bing_analysis   = state.get("bing_analysis")   or "Not available."
    reddit_analysis = state.get("reddit_analysis") or "Not available."

    messages = get_synthesis_messages(
        user_question, google_analysis, bing_analysis, reddit_analysis
    )

    try:
        reply = llm.invoke(messages)
        final_answer = _extract_content(reply)
    except Exception as exc:
        _safe_print(f"⚠️  Synthesis error: {exc}")
        final_answer = (
            f"## Research Synthesis Summary\n\n"
            f"An error occurred during final synthesis: {exc}\n\n"
            f"### Available Source Insights:\n\n"
            f"**Google Insights:**\n{google_analysis}\n\n"
            f"**Bing Insights:**\n{bing_analysis}\n\n"
            f"**Reddit Insights:**\n{reddit_analysis}"
        )

    return {
        "final_answer": final_answer,
        "messages": [{"role": "assistant", "content": final_answer}],
    }



# ── Graph assembly ────────────────────────────────────────────────────────────

_builder = StateGraph(State)

# Nodes
_builder.add_node("google_search",          google_search)
_builder.add_node("bing_search",            bing_search)
_builder.add_node("reddit_search",          reddit_search)
_builder.add_node("analyze_reddit_posts",   analyze_reddit_posts)
_builder.add_node("retrieve_reddit_posts",  retrieve_reddit_posts)
_builder.add_node("analyze_google_results", analyze_google_results)
_builder.add_node("analyze_bing_results",   analyze_bing_results)
_builder.add_node("analyze_reddit_results", analyze_reddit_results)
_builder.add_node("synthesize_analyses",    synthesize_analyses)

# Parallel search fan-out from START
_builder.add_edge(START, "google_search")
_builder.add_edge(START, "bing_search")
_builder.add_edge(START, "reddit_search")

# Synchronize parallel searches before Reddit deep-dive
_builder.add_edge("google_search", "analyze_reddit_posts")
_builder.add_edge("bing_search",   "analyze_reddit_posts")
_builder.add_edge("reddit_search", "analyze_reddit_posts")

# Reddit deep-dive chain
_builder.add_edge("analyze_reddit_posts",  "retrieve_reddit_posts")

# Fan-out to all 3 analyses in parallel once Reddit fetching is complete
_builder.add_edge("retrieve_reddit_posts", "analyze_google_results")
_builder.add_edge("retrieve_reddit_posts", "analyze_bing_results")
_builder.add_edge("retrieve_reddit_posts", "analyze_reddit_results")

# All 3 analyses fan-in to synthesize_analyses (executes exactly ONCE with all 3 analyses ready)
_builder.add_edge("analyze_google_results", "synthesize_analyses")
_builder.add_edge("analyze_bing_results",   "synthesize_analyses")
_builder.add_edge("analyze_reddit_results", "synthesize_analyses")

_builder.add_edge("synthesize_analyses", END)

# Compile once at import time — shared by CLI and Streamlit threads
graph = _builder.compile()
