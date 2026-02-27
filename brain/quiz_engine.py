"""
Track Shifter -- Quiz Engine
=============================
Generates multiple-choice quiz questions using the Gemini API.

When the user opens a distraction app during focus, the Navigator
triggers a quiz obstacle.  This module sends a prompt to Gemini,
parses the structured JSON response, and returns clean question
objects ready for the front-end.

Dependencies:
    pip install google-genai
"""

from __future__ import annotations

import json
import re
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from google import genai

from config import BrainConfig, QuizConfig, QuizDifficulty


# -- Data models --------------------------------------------------------------

@dataclass
class QuizQuestion:
    """A single parsed quiz question."""
    question: str
    options: List[str]
    answer: str           # the correct option letter, e.g. "B"


@dataclass
class QuizResult:
    """Structured output returned to the caller."""
    questions: List[QuizQuestion]
    raw_response: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to the required JSON schema."""
        return {
            "questions": [
                {
                    "question": q.question,
                    "options": q.options,
                    "answer": q.answer,
                }
                for q in self.questions
            ]
        }


# -- Prompt builder -----------------------------------------------------------

_PROMPT_TEMPLATE = (
    "Generate {n} concise multiple choice questions with 4 options each "
    "based on the topic: {topic}. "
    "Difficulty level: {difficulty}. "
    "{context_line}"
    "Clearly indicate the correct answer. "
    "Keep them short for 5-second recall.\n\n"
    "Return ONLY valid JSON in this exact format, with no extra text:\n"
    '{{\n'
    '  "questions": [\n'
    '    {{\n'
    '      "question": "...",\n'
    '      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],\n'
    '      "answer": "B"\n'
    '    }}\n'
    '  ]\n'
    '}}'
)


def _build_prompt(
    topic: str,
    difficulty: str,
    n: int = 3,
    context: Optional[str] = None,
) -> str:
    context_line = f"Additional context: {context}. " if context else ""
    return _PROMPT_TEMPLATE.format(
        n=n,
        topic=topic,
        difficulty=difficulty,
        context_line=context_line,
    )


# -- Response parser ----------------------------------------------------------

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```")


def _extract_json(text: str) -> str:
    """Pull JSON from a fenced code block or return the raw text."""
    m = _JSON_BLOCK_RE.search(text)
    if m:
        return m.group(1).strip()
    return text.strip()


def _normalise_answer(ans: str) -> str:
    """Normalise an answer to a single uppercase letter."""
    ans = ans.strip().upper()
    if ans and ans[0] in "ABCD":
        return ans[0]
    return ans


def _parse_response(raw: str) -> List[QuizQuestion]:
    """
    Parse the LLM response into a list of QuizQuestion.

    Handles common LLM quirks:
      - JSON wrapped in ``` fences
      - answer as full text instead of letter
      - missing keys
    """
    json_str = _extract_json(raw)
    data = json.loads(json_str)

    questions_raw: List[Dict[str, Any]] = []
    if isinstance(data, dict) and "questions" in data:
        questions_raw = data["questions"]
    elif isinstance(data, list):
        questions_raw = data
    else:
        raise ValueError("Unexpected JSON structure -- missing 'questions' key")

    parsed: List[QuizQuestion] = []
    for q in questions_raw:
        question_text = q.get("question", "").strip()
        options = [str(o).strip() for o in q.get("options", [])]
        raw_answer = str(q.get("answer", "")).strip()

        # If the answer is the full option text, map it back to a letter
        answer_letter = _normalise_answer(raw_answer)
        if answer_letter not in "ABCD":
            for i, opt in enumerate(options):
                if raw_answer.lower() in opt.lower():
                    answer_letter = chr(ord("A") + i)
                    break

        if not question_text or len(options) != 4:
            continue  # skip malformed entries

        parsed.append(QuizQuestion(
            question=question_text,
            options=options,
            answer=answer_letter,
        ))

    if not parsed:
        raise ValueError("No valid questions could be parsed from LLM response")

    return parsed


# -- Quiz Engine --------------------------------------------------------------

class QuizEngine:
    """
    LLM-powered quiz obstacle generator.

    Usage::

        engine = QuizEngine()                         # uses default config
        result = engine.generate(
            study_topic="Photosynthesis",
            difficulty="medium",
            context="Focus on the light-dependent reactions",
        )
        print(result.to_dict())

    The engine will retry up to ``config.quiz.max_retries`` times on API
    errors or malformed responses before returning an error result.
    """

    def __init__(self, config: Optional[BrainConfig] = None) -> None:
        self.config = config or BrainConfig()
        self._qcfg: QuizConfig = self.config.quiz
        self._client = genai.Client(api_key=self._qcfg.gemini_api_key)
        self._history: List[QuizResult] = []

    # -- Public API -----------------------------------------------------------

    @property
    def history(self) -> List[QuizResult]:
        return list(self._history)

    def generate(
        self,
        study_topic: str,
        difficulty: str = "",
        context: Optional[str] = None,
    ) -> QuizResult:
        """
        Generate quiz questions via the Gemini API.

        Args:
            study_topic:  the subject the user is studying
            difficulty:   "easy" | "medium" | "hard" (defaults to config)
            context:      optional extra context / notes for the prompt

        Returns:
            A ``QuizResult`` with parsed questions or an error message.
        """
        diff = difficulty or self._qcfg.default_difficulty.value
        prompt = _build_prompt(
            topic=study_topic,
            difficulty=diff,
            n=self._qcfg.num_questions,
            context=context,
        )

        last_error: str = ""
        for attempt in range(1, self._qcfg.max_retries + 1):
            try:
                raw_text = self._call_api(prompt)
                questions = _parse_response(raw_text)

                result = QuizResult(questions=questions, raw_response=raw_text)
                self._history.append(result)
                return result

            except json.JSONDecodeError as exc:
                last_error = f"JSON parse error (attempt {attempt}): {exc}"
            except ValueError as exc:
                last_error = f"Validation error (attempt {attempt}): {exc}"
            except Exception as exc:
                last_error = f"API error (attempt {attempt}): {exc}\n{traceback.format_exc()}"

            # Brief back-off before retry
            if attempt < self._qcfg.max_retries:
                time.sleep(1 * attempt)

        # All retries exhausted
        error_result = QuizResult(
            questions=[],
            error=f"Failed after {self._qcfg.max_retries} attempts. Last error: {last_error}",
        )
        self._history.append(error_result)
        return error_result

    # -- Internal -------------------------------------------------------------

    def _call_api(self, prompt: str) -> str:
        """Send the prompt to the Gemini API and return the text response."""
        response = self._client.models.generate_content(
            model=self._qcfg.gemini_model,
            contents=prompt,
        )
        text = response.text
        if not text:
            raise ValueError("Gemini returned an empty response")
        return text

    def get_stats(self) -> Dict[str, Any]:
        """Summary statistics across all quiz sessions."""
        total = len(self._history)
        successful = sum(1 for r in self._history if r.error is None)
        total_questions = sum(len(r.questions) for r in self._history)
        return {
            "total_sessions": total,
            "successful_sessions": successful,
            "failed_sessions": total - successful,
            "total_questions_generated": total_questions,
        }
