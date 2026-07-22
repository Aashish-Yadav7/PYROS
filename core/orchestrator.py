"""
core/orchestrator.py

The brain — advanced version.

New capabilities vs the basic version:
1. MULTI-ROUND TOOL USE: the model can call a tool, look at the result,
   then decide to call ANOTHER tool before finally answering — not just one.
2. CONTEXT SUMMARIZATION: when chat history gets long, older messages are
   compressed into a short summary instead of being dropped or overflowing
   the model's context window.
3. LLM-AS-A-JUDGE SELF-CHECK: for important replies, a second quick model
   call reviews the draft answer for obvious mistakes before it's shown to you.
4. FEEDBACK-AWARE PROMPTING: recent things you corrected get quietly folded
   into the system prompt so PYROS avoids repeating the same mistake.
5. USAGE TRACKING: logs which provider answered and roughly how long it took.
"""
import json
import time
import logging
from core.model_router import LLMRouter
import memory.history_store as history
import memory.vector_store as vectors
import core.settings as settings

logger = logging.getLogger("orchestrator")

router = LLMRouter()

BASE_SYSTEM_PROMPT = """You are PYROS, a personal AI assistant built from scratch by your user.
You are helpful, direct, and honest. You have access to tools for opening apps,
sending emails, and browsing the web. Use a tool whenever the request calls for
an action, not just an explanation. If a task needs multiple steps (e.g. look
something up, then act on it), use tools one at a time and reason between steps."""

MAX_TOOL_ROUNDS = 4
SUMMARIZE_AFTER = 30
JUDGE_ENABLED = True


def _get_feedback_notes() -> str:
    mistakes = history.get_negative_feedback_examples(limit=5)
    if not mistakes:
        return ""
    lines = [m["correction"] for m in mistakes if m["correction"]]
    if not lines:
        return ""
    return "Things you were corrected on recently, avoid repeating these:\n- " + "\n- ".join(lines)


def _maybe_summarize_history():
    all_recent = history.get_recent_messages(limit=SUMMARIZE_AFTER + 1)
    if len(all_recent) <= SUMMARIZE_AFTER:
        return

    old_chunk = all_recent[: len(all_recent) // 2]
    text_block = "\n".join(f"{m['role']}: {m['content']}" for m in old_chunk)

    summary_prompt = [
        {"role": "system", "content": "Summarize this conversation excerpt in 3-4 short sentences, keeping key facts and decisions."},
        {"role": "user", "content": text_block},
    ]
    try:
        response = router.chat(summary_prompt)
        summary = response.choices[0].message.content
        history.add_message("system", f"[Summary of earlier conversation]: {summary}")
        logger.info("Compressed old history into a summary message.")
    except Exception as e:
        logger.warning(f"Summarization skipped due to error: {e}")


def _build_context(user_text: str) -> list:
    messages = [{"role": "system", "content": BASE_SYSTEM_PROMPT}]

    feedback_notes = _get_feedback_notes()
    if feedback_notes:
        messages.append({"role": "system", "content": feedback_notes})

    doc_hits = vectors.search_documents(user_text, top_k=settings.RAG_TOP_K)
    doc_hits = vectors.re_rank(doc_hits, keep_top=3)
    if doc_hits:
        context_block = "\n\n".join(h["text"] for h in doc_hits)
        messages.append({
            "role": "system",
            "content": f"Relevant information from your stored documents:\n{context_block}",
        })

    messages.extend(history.get_recent_messages(limit=settings.CONVERSATION_HISTORY_LIMIT))
    messages.append({"role": "user", "content": user_text})
    return messages


def _judge_reply(user_text: str, draft_reply: str) -> str:
    if not JUDGE_ENABLED:
        return draft_reply

    judge_prompt = [
        {
            "role": "system",
            "content": (
                "You review draft AI answers for obvious factual errors, contradictions, "
                "or unhelpfulness. If the draft is fine, reply with exactly: OK. "
                "If it has a real problem, reply with a corrected version only."
            ),
        },
        {"role": "user", "content": f"Question: {user_text}\n\nDraft answer: {draft_reply}"},
    ]
    try:
        response = router.chat(judge_prompt)
        verdict = response.choices[0].message.content.strip()
        if verdict.upper().startswith("OK"):
            return draft_reply
        return verdict
    except Exception as e:
        logger.warning(f"Judge pass skipped due to error: {e}")
        return draft_reply


def run(user_text: str, tools: list = None, tool_functions: dict = None, use_judge: bool = True) -> dict:
    start_time = time.time()
    history.add_message("user", user_text)
    _maybe_summarize_history()

    messages = _build_context(user_text)
    tool_call_count = 0
    reply_text = "I hit my tool-use safety limit for this request — here's what I have so far."

    for _ in range(MAX_TOOL_ROUNDS):
        response = router.chat(messages, tools=tools)
        msg = response.choices[0].message

        if getattr(msg, "tool_calls", None) and tool_functions:
            messages.append(msg)
            for call in msg.tool_calls:
                fn = tool_functions.get(call.function.name)
                result = f"Unknown tool: {call.function.name}"
                if fn:
                    try:
                        args = json.loads(call.function.arguments)
                        result = fn(**args)
                    except Exception as e:
                        result = f"Tool error: {e}"
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": str(result),
                })
            tool_call_count += 1
            continue

        reply_text = msg.content
        break

    if use_judge:
        reply_text = _judge_reply(user_text, reply_text)

    message_id = history.add_message("assistant", reply_text)
    vectors.add_conversation_memory(f"User: {user_text}\nPYROS: {reply_text}")

    elapsed = round(time.time() - start_time, 2)
    logger.info(f"Handled request in {elapsed}s with {tool_call_count} tool round(s)")

    return {
        "reply": reply_text,
        "message_id": message_id,
        "tool_calls": tool_call_count,
        "elapsed_seconds": elapsed,
    }


def submit_feedback(message_id: str, rating: str, correction: str = ""):
    history.add_feedback(message_id, rating, correction)