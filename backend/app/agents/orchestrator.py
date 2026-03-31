"""
PlannerAgent — decomposes a user query into a JSON plan, then executes it
step-by-step using the tool registry.

Execution flow:
  1. Call Gemini with the planner system prompt to get a JSON plan.
  2. Validate the plan against the tool registry.
  3. Execute each step sequentially, threading outputs into subsequent steps.
  4. Yield StepResult after each step (supports streaming).
  5. Return the final answer.
"""
import json
import logging
import time
from typing import Generator, List, Any, Dict

from langchain_google_genai import ChatGoogleGenerativeAI

from app.agents.prompts.planner import PLANNER_SYSTEM_PROMPT, ANSWER_PROMPT
from app.agents.tools import language_detector, retriever, translator, summarizer
from app.models.schemas import StepResult

logger = logging.getLogger(__name__)

VALID_TOOLS = {"detect_language", "retrieve", "translate_chunks", "summarize", "answer"}


class PlannerAgent:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

    # ── public interface ─────────────────────────────────────────────────────

    def run(self, query: str) -> tuple[str, List[StepResult]]:
        """Execute the full agentic pipeline. Returns (answer, steps)."""
        steps: List[StepResult] = []
        for step_result, _ in self._execute(query):
            steps.append(step_result)
        # The last step's output_summary is the final answer
        answer = steps[-1].output_summary if steps else "No answer generated."
        return answer, steps

    def stream(self, query: str) -> Generator[StepResult, None, None]:
        """Yield StepResult as each tool completes."""
        for step_result, _ in self._execute(query):
            yield step_result

    # ── internals ────────────────────────────────────────────────────────────

    def _execute(self, query: str):
        """
        Core execution generator.
        Yields (StepResult, raw_output) tuples.
        """
        plan = self._plan(query)

        # Shared state across steps
        chunks: List[Dict[str, Any]] = []
        detected_lang = "en"
        final_answer = ""

        for step in plan:
            tool = step["tool"]
            inp = step.get("input", {})
            t0 = time.monotonic()

            try:
                if tool == "detect_language":
                    text = inp.get("text", query)
                    detected_lang = language_detector.detect_language(text)
                    output = detected_lang
                    input_summary = f"text: {text[:60]}…" if len(text) > 60 else text
                    output_summary = f"Detected language: {detected_lang}"

                elif tool == "retrieve":
                    q = inp.get("query", query)
                    top_k = inp.get("top_k", 5)
                    chunks = retriever.retrieve_chunks(self.session_id, q, top_k=top_k)
                    output = chunks
                    input_summary = f"query: {q[:60]}, top_k: {top_k}"
                    output_summary = f"Retrieved {len(chunks)} chunks"

                elif tool == "translate_chunks":
                    src = inp.get("source_lang", "en")
                    tgt = inp.get("target_lang", detected_lang)
                    chunks = translator.translate_chunks(chunks, src, tgt)
                    output = chunks
                    input_summary = f"{src} → {tgt}, {len(chunks)} chunks"
                    output_summary = f"Translated {len(chunks)} chunks to {tgt}"

                elif tool == "summarize":
                    detail = inp.get("detail_level", "standard")
                    summary = summarizer.summarize_chunks(chunks, detail_level=detail)
                    final_answer = summary
                    output = summary
                    input_summary = f"detail_level: {detail}, {len(chunks)} chunks"
                    output_summary = summary[:200] + ("…" if len(summary) > 200 else "")

                elif tool == "answer":
                    answer_lang = inp.get("answer_language", detected_lang)
                    context = "\n\n---\n\n".join(c["content"] for c in chunks)
                    prompt = ANSWER_PROMPT.format(
                        answer_language=answer_lang, context=context, query=query
                    )
                    result = self._llm.invoke(prompt)
                    final_answer = result.content.strip()
                    output = final_answer
                    input_summary = f"query: {query[:60]}, lang: {answer_lang}"
                    output_summary = final_answer[:200] + ("…" if len(final_answer) > 200 else "")

                else:
                    logger.warning("Unknown tool in plan: %s — skipping", tool)
                    continue

            except Exception as exc:
                logger.error("Tool %s failed: %s", tool, exc, exc_info=True)
                step_result = StepResult(
                    tool=tool,
                    input_summary=str(inp)[:100],
                    output_summary=f"Error: {exc}",
                    latency_ms=int((time.monotonic() - t0) * 1000),
                    status="error",
                )
                yield step_result, None
                continue

            latency_ms = int((time.monotonic() - t0) * 1000)
            step_result = StepResult(
                tool=tool,
                input_summary=input_summary,
                output_summary=output_summary,
                latency_ms=latency_ms,
                status="completed",
            )
            yield step_result, output

    def _plan(self, query: str) -> List[Dict[str, Any]]:
        """Ask Gemini to produce a JSON execution plan, then validate it."""
        prompt = f"{PLANNER_SYSTEM_PROMPT}\n\nUser query: {query}"
        try:
            result = self._llm.invoke(prompt)
            raw = result.content.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            plan = json.loads(raw)
        except (json.JSONDecodeError, Exception) as exc:
            logger.error("Planner failed (%s) — using fallback plan", exc)
            plan = self._fallback_plan(query)

        return self._validate_plan(plan, query)

    def _validate_plan(
        self, plan: List[Dict[str, Any]], query: str
    ) -> List[Dict[str, Any]]:
        """Remove steps with unknown tools. Ensure at least detect+retrieve+answer."""
        valid = [s for s in plan if isinstance(s, dict) and s.get("tool") in VALID_TOOLS]
        if not valid:
            logger.warning("Plan was empty or all-invalid — using fallback")
            return self._fallback_plan(query)
        return valid

    @staticmethod
    def _fallback_plan(query: str) -> List[Dict[str, Any]]:
        """Minimal safe plan used when the LLM planner fails."""
        return [
            {"tool": "detect_language", "input": {"text": query}},
            {"tool": "retrieve", "input": {"query": query, "top_k": 5}},
            {"tool": "answer", "input": {"query": query, "answer_language": "en"}},
        ]
