"""Feedback rewriting.

Turns short / informal / grammatically weak student feedback into polished,
authentic, presentation-ready testimonials.

Two engines are available:

* ``anthropic`` - uses the Claude API for natural, non-robotic rewrites.
* ``rule``      - a fully offline fallback that does conservative grammar and
                  capitalisation cleanup (no network, no API key required).

The rewrite is intentionally faithful: it never invents achievements,
exaggerates, or changes meaning. Junk inputs ("NA", "-", "good") are handled
gracefully.
"""

from __future__ import annotations

import logging
import re

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger("feedback_sync.rewriter")

# Tokens that carry no usable feedback content.
_JUNK_TOKENS = {"", "na", "n/a", "nil", "none", "-", "--", ".", "no", "nothing"}

_SYSTEM_PROMPT = """\
You are an expert editor who polishes raw student feedback into professional, \
presentation-ready testimonials for an education company.

Rewrite the student's feedback so it is:
- grammatically correct, fluent, and easy to read
- natural and human sounding, NOT robotic or templated
- warm and emotionally engaging, while remaining authentic
- concise (1-3 sentences)

Strict rules:
- DO NOT invent achievements, facts, names, or details not implied by the original.
- DO NOT exaggerate beyond the sentiment expressed.
- DO NOT change the meaning or the original intent.
- Preserve the instructor's name and the topic if they appear.
- Vary the phrasing between testimonials; never make them sound identical.
- Output ONLY the rewritten testimonial text, with no quotes, labels, or preamble.\
"""

# Few-shot examples mirroring the project's required output style.
_FEWSHOT = [
    (
        "very good class beautifully explained intangible assets",
        "The session was extremely insightful, and the concepts around intangible "
        "assets were explained with excellent clarity. The practical examples made "
        "the topic very easy to understand.",
    ),
    (
        "class was excellent wherever confusing teaches repeatedly",
        "The class was highly interactive and engaging. What stood out most was the "
        "instructor's patience in revisiting difficult concepts until everyone "
        "understood them clearly.",
    ),
    (
        "madam taught very good tips on cold emails",
        "The session on cold emailing was highly practical and informative. The "
        "strategies and techniques shared can be directly applied in real-world "
        "client communication.",
    ),
]


def is_usable(raw: str, min_chars: int = 2) -> bool:
    """Return True if ``raw`` contains feedback worth rewriting."""
    if raw is None:
        return False
    cleaned = raw.strip()
    if len(cleaned) < min_chars:
        return False
    return cleaned.lower() not in _JUNK_TOKENS


class Rewriter:
    """Base interface."""

    def rewrite(self, raw: str, context: dict | None = None) -> str:  # pragma: no cover
        raise NotImplementedError


class RuleBasedRewriter(Rewriter):
    """Offline, deterministic cleanup. Used when no LLM is configured."""

    def rewrite(self, raw: str, context: dict | None = None) -> str:
        text = re.sub(r"\s+", " ", raw.strip())
        # Capitalise the first letter.
        if text:
            text = text[0].upper() + text[1:]
        # Ensure terminal punctuation.
        if text and text[-1] not in ".!?":
            text += "."
        # Capitalise the pronoun "i".
        text = re.sub(r"\bi\b", "I", text)
        return text


class AnthropicRewriter(Rewriter):
    """LLM-backed rewriter using the Claude API with retries."""

    def __init__(self, api_key: str, model: str, max_tokens: int = 400):
        # Imported lazily so the package works without the SDK in rule mode.
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def _build_messages(self, raw: str, context: dict | None) -> list[dict]:
        messages: list[dict] = []
        for raw_ex, good_ex in _FEWSHOT:
            messages.append({"role": "user", "content": f"Raw feedback:\n{raw_ex}"})
            messages.append({"role": "assistant", "content": good_ex})

        ctx_lines = []
        if context:
            for key in ("Course", "Expert", "Topic"):
                val = (context.get(key) or "").strip()
                if val:
                    ctx_lines.append(f"{key}: {val}")
        ctx_block = ("\n".join(ctx_lines) + "\n\n") if ctx_lines else ""
        messages.append(
            {"role": "user", "content": f"{ctx_block}Raw feedback:\n{raw}"}
        )
        return messages

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=2, min=2, max=16),
        retry=retry_if_exception_type(Exception),
    )
    def _call(self, raw: str, context: dict | None) -> str:
        # Prompt caching on the system block keeps repeated daily runs cheap.
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=self._build_messages(raw, context),
        )
        parts = [b.text for b in response.content if getattr(b, "type", None) == "text"]
        return "".join(parts).strip()

    def rewrite(self, raw: str, context: dict | None = None) -> str:
        text = self._call(raw, context)
        # Strip stray wrapping quotes the model may add.
        text = text.strip().strip('"').strip("'").strip()
        if not text:
            logger.warning("Empty rewrite returned; falling back to rule cleanup.")
            return RuleBasedRewriter().rewrite(raw, context)
        return text


def build_rewriter(cfg) -> Rewriter:
    """Factory: choose an engine based on configuration, with safe fallback."""
    if cfg.rewrite_engine == "anthropic":
        try:
            logger.info("Using Anthropic rewriter (model=%s).", cfg.rewrite_model)
            return AnthropicRewriter(
                api_key=cfg.anthropic_api_key,
                model=cfg.rewrite_model,
                max_tokens=cfg.rewrite_max_tokens,
            )
        except Exception as exc:  # pragma: no cover - defensive import/init guard
            logger.error(
                "Could not initialise Anthropic rewriter (%s); "
                "falling back to offline rule-based cleanup.",
                exc,
            )
    logger.info("Using offline rule-based rewriter.")
    return RuleBasedRewriter()
