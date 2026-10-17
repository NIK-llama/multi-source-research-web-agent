"""
main.py — Terminal CLI entrypoint for the Multi-Source Research Agent.

Run with:
    python main.py
    or: uv run python main.py
"""

import sys

from agent import graph

# Ensure UTF-8 output encoding for emojis on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def run_chatbot() -> None:
    print("=" * 60)
    print("🔬 Multi-Source Research Agent (CLI)")
    print("Type 'exit' or 'quit' to quit")
    print("=" * 60 + "\n")

    while True:
        try:
            user_input = input("Ask me anything: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        state = {
            "messages": [{"role": "user", "content": user_input}],
            "user_question": user_input,
            "google_results": None,
            "bing_results": None,
            "reddit_results": None,
            "selected_reddit_urls": None,
            "reddit_post_data": None,
            "google_analysis": None,
            "bing_analysis": None,
            "reddit_analysis": None,
            "final_answer": None,
        }

        print("\n🚀 Starting parallel research pipeline…")
        try:
            final_state = graph.invoke(state)
            final_answer = final_state.get("final_answer")

            if final_answer:
                print(f"\n{'=' * 80}")
                print("RESEARCH REPORT")
                print("=" * 80)
                print(final_answer)
                print("=" * 80 + "\n")
            else:
                print("\n⚠️  No answer could be generated. Please try again.\n")
        except Exception as exc:
            print(f"\n❌ Research error: {exc}\n")


if __name__ == "__main__":
    run_chatbot()
