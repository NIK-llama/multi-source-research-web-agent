"""
agent/prompts.py

All LLM prompt templates for the research pipeline, plus convenience
functions that assemble the final message arrays passed to the model.
"""

from typing import Any

# ── Prompt templates ─────────────────────────────────────────────────────────

class PromptTemplates:
    """Container for all prompt templates used in the research assistant."""

    # ── Reddit URL selection ─────────────────────────────────────────────────

    @staticmethod
    def reddit_url_analysis_system() -> str:
        """System prompt for selecting the most relevant Reddit post URLs."""
        return (
            "You are an expert at evaluating Reddit search results for research relevance.\n\n"
            "Your task: Given a user's question and a list of Reddit post titles/URLs, "
            "select up to 3 posts that are most likely to contain useful, direct discussion "
            "about the question.\n\n"
            "Selection criteria (all must apply):\n"
            "- The post title directly relates to the question topic\n"
            "- The post appears to be a genuine discussion (not a meme, shitpost, or off-topic content)\n"
            "- The subreddit is relevant to the question domain\n\n"
            "If no posts clearly meet these criteria, return an empty list. Do NOT force selections.\n"
            "Return a structured response with the selected URLs (maximum 3)."
        )

    @staticmethod
    def reddit_url_analysis_user(user_question: str, reddit_results: str) -> str:
        """User prompt for selecting relevant Reddit post URLs."""
        return (
            f"User Question: {user_question}\n\n"
            f"Reddit Search Results:\n{reddit_results}\n\n"
            "Select up to 3 Reddit posts most relevant to answering the user's question. "
            "If none are clearly relevant, return an empty list."
        )

    # ── Google analysis ──────────────────────────────────────────────────────

    @staticmethod
    def google_analysis_system() -> str:
        """System prompt for extracting insights from Google search results."""
        return (
            "You are an expert research analyst. Your task is to extract the most relevant "
            "insights from Google search results to help answer a user's question.\n\n"
            "Instructions:\n"
            "- Focus only on information directly relevant to the question\n"
            "- Prioritize authoritative and factual sources\n"
            "- Extract key facts, statistics, expert opinions, and verified claims\n"
            "- Note any consensus or disagreement between sources\n"
            "- If the results are insufficient or irrelevant, clearly state that\n\n"
            "Format your analysis in clear, concise bullet points grouped by theme. "
            "Always cite the source type (e.g., news article, official site, Wikipedia)."
        )

    @staticmethod
    def google_analysis_user(user_question: str, google_results: str) -> str:
        """User prompt for analyzing Google search results."""
        return (
            f"Question: {user_question}\n\n"
            f"Google Search Results:\n{google_results}\n\n"
            "Extract and summarize the key insights from these results that directly help "
            "answer the question. Be factual and concise."
        )

    # ── Bing analysis ────────────────────────────────────────────────────────

    @staticmethod
    def bing_analysis_system() -> str:
        """System prompt for extracting complementary insights from Bing search results."""
        return (
            "You are an expert research analyst. Your task is to extract complementary "
            "insights from Bing search results to help answer a user's question.\n\n"
            "Instructions:\n"
            "- Focus on information not already obvious from the question itself\n"
            "- Look for recent news, alternative perspectives, and technical details\n"
            "- Extract specific facts, dates, quotes, and verifiable claims\n"
            "- Note any source credibility concerns\n"
            "- If the results are insufficient or irrelevant, clearly state that\n\n"
            "Format your analysis in clear, concise bullet points. Always note the type of source."
        )

    @staticmethod
    def bing_analysis_user(user_question: str, bing_results: str) -> str:
        """User prompt for analyzing Bing search results."""
        return (
            f"Question: {user_question}\n\n"
            f"Bing Search Results:\n{bing_results}\n\n"
            "Extract and summarize the key insights from these results that directly help "
            "answer the question. Focus on details not covered by other common sources."
        )

    # ── Reddit analysis ──────────────────────────────────────────────────────

    @staticmethod
    def reddit_analysis_system() -> str:
        """System prompt for extracting insights from Reddit discussions."""
        return (
            "You are an expert at extracting meaningful insights from Reddit discussions.\n\n"
            "Your task: Analyze Reddit search results and any retrieved post comments to "
            "surface real community opinions and experiences relevant to the user's question.\n\n"
            "Instructions:\n"
            "- Identify recurring themes, opinions, and sentiments in the community\n"
            "- Distinguish between upvoted/consensus views and minority opinions\n"
            "- Extract specific, quotable comments or points when available\n"
            "- Note the subreddit context (e.g., r/finance vs r/conspiracy have different credibility)\n"
            "- If post comment data is empty or unavailable, analyze based on post titles and subreddit names alone\n"
            "- Be honest if the Reddit data is sparse or not directly relevant\n\n"
            "Format as a clear summary with themes and supporting evidence."
        )

    @staticmethod
    def reddit_analysis_user(
        user_question: str,
        reddit_results: str,
        reddit_post_data: Any,
    ) -> str:
        """User prompt for analyzing Reddit discussions."""
        post_data_section = (
            f"Detailed Post Comments:\n{reddit_post_data}"
            if reddit_post_data
            else "Detailed Post Comments: Not available — analyze from search titles only."
        )
        return (
            f"Question: {user_question}\n\n"
            f"Reddit Search Results (post titles and URLs):\n{reddit_results}\n\n"
            f"{post_data_section}\n\n"
            "Summarize the Reddit community's perspective on this question. "
            "Note the overall sentiment, key opinions, and any notable debates."
        )

    # ── Synthesis ────────────────────────────────────────────────────────────

    @staticmethod
    def synthesis_system() -> str:
        """System prompt for synthesizing all source analyses into one answer."""
        return (
            "You are an expert research synthesizer. Your job is to combine analyses "
            "from Google, Bing, and Reddit into one clear, well-structured, comprehensive answer.\n\n"
            "Rules:\n"
            "1. Always produce a complete answer — even if some sources returned no data\n"
            "2. Use the available sources and clearly note when a source had no relevant data\n"
            "3. Identify where sources agree and where they conflict\n"
            "4. Structure your response with clear headers (##) and bullet points\n"
            "5. Cite the source type (Google, Bing, Reddit) for specific claims\n"
            "6. End with a concise \"Bottom Line\" summary (2-3 sentences max)\n"
            "7. Do NOT say \"I cannot answer\" — always synthesize what is available\n\n"
            "The answer must be in clean markdown format."
        )

    @staticmethod
    def synthesis_user(
        user_question: str,
        google_analysis: str,
        bing_analysis: str,
        reddit_analysis: str,
    ) -> str:
        """User prompt for final multi-source synthesis."""
        return (
            f"Question: {user_question}\n\n"
            f"--- Google Analysis ---\n{google_analysis}\n\n"
            f"--- Bing Analysis ---\n{bing_analysis}\n\n"
            f"--- Reddit Community Analysis ---\n{reddit_analysis}\n\n"
            "Synthesize these into a comprehensive, well-structured answer to the question. "
            "Use markdown headers and bullet points. End with a \"## Bottom Line\" section."
        )


# ── Message-array builders ───────────────────────────────────────────────────

def _build_messages(system: str, user: str) -> list[dict[str, Any]]:
    """Return a ``[system, user]`` message list for an LLM call."""
    return [
        {"role": "system", "content": system},
        {"role": "user",   "content": user},
    ]


def get_reddit_url_analysis_messages(
    user_question: str,
    reddit_results: str,
) -> list[dict[str, Any]]:
    """Build the message array for Reddit URL relevance selection."""
    return _build_messages(
        PromptTemplates.reddit_url_analysis_system(),
        PromptTemplates.reddit_url_analysis_user(user_question, reddit_results),
    )


def get_google_analysis_messages(
    user_question: str,
    google_results: str,
) -> list[dict[str, Any]]:
    """Build the message array for Google results analysis."""
    return _build_messages(
        PromptTemplates.google_analysis_system(),
        PromptTemplates.google_analysis_user(user_question, google_results),
    )


def get_bing_analysis_messages(
    user_question: str,
    bing_results: str,
) -> list[dict[str, Any]]:
    """Build the message array for Bing results analysis."""
    return _build_messages(
        PromptTemplates.bing_analysis_system(),
        PromptTemplates.bing_analysis_user(user_question, bing_results),
    )


def get_reddit_analysis_messages(
    user_question: str,
    reddit_results: str,
    reddit_post_data: Any,
) -> list[dict[str, Any]]:
    """Build the message array for Reddit discussion analysis."""
    return _build_messages(
        PromptTemplates.reddit_analysis_system(),
        PromptTemplates.reddit_analysis_user(user_question, reddit_results, reddit_post_data),
    )


def get_synthesis_messages(
    user_question: str,
    google_analysis: str,
    bing_analysis: str,
    reddit_analysis: str,
) -> list[dict[str, Any]]:
    """Build the message array for final multi-source synthesis."""
    return _build_messages(
        PromptTemplates.synthesis_system(),
        PromptTemplates.synthesis_user(
            user_question, google_analysis, bing_analysis, reddit_analysis
        ),
    )
