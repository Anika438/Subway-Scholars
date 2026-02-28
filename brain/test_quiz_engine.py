"""
Tests for Track Shifter — Quiz Engine
======================================
All Gemini API calls are mocked so tests run without a real API key.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from config import BrainConfig, QuizConfig, QuizDifficulty
from quiz_engine import (
    QuizEngine,
    QuizQuestion,
    QuizResult,
    _build_prompt,
    _extract_json,
    _normalise_answer,
    _parse_response,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

GOOD_JSON = json.dumps({
    "questions": [
        {
            "question": "What is the powerhouse of the cell?",
            "options": [
                "A) Nucleus",
                "B) Mitochondria",
                "C) Ribosome",
                "D) Golgi apparatus",
            ],
            "answer": "B",
        },
        {
            "question": "Which molecule carries genetic info?",
            "options": [
                "A) RNA",
                "B) Protein",
                "C) DNA",
                "D) Lipid",
            ],
            "answer": "C",
        },
        {
            "question": "What gas do plants absorb?",
            "options": [
                "A) Oxygen",
                "B) Nitrogen",
                "C) Carbon Dioxide",
                "D) Hydrogen",
            ],
            "answer": "C",
        },
    ]
})

FENCED_JSON = f"```json\n{GOOD_JSON}\n```"

MALFORMED_JSON = "{ this is not valid json }"

MISSING_QUESTIONS_KEY = json.dumps({"data": [{"q": "hello"}]})

PARTIAL_QUESTIONS = json.dumps({
    "questions": [
        {
            "question": "Valid question?",
            "options": ["A) 1", "B) 2", "C) 3", "D) 4"],
            "answer": "A",
        },
        {
            "question": "",
            "options": ["A) x"],
            "answer": "A",
        },
    ]
})

ANSWER_AS_FULL_TEXT = json.dumps({
    "questions": [
        {
            "question": "Capital of France?",
            "options": ["A) Berlin", "B) Paris", "C) Madrid", "D) Rome"],
            "answer": "B) Paris",
        },
    ]
})


@pytest.fixture
def config():
    return BrainConfig(
        quiz=QuizConfig(
            gemini_api_key="test-key-placeholder",
            max_retries=2,
            num_questions=3,
        )
    )


def _make_engine(config, response_text=GOOD_JSON, side_effect=None):
    """Create a QuizEngine with a mocked Gemini client."""
    with patch("quiz_engine.genai") as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        engine = QuizEngine(config)

        mock_response = MagicMock()
        if side_effect:
            mock_client.models.generate_content.side_effect = side_effect
        else:
            mock_response.text = response_text
            mock_client.models.generate_content.return_value = mock_response

        return engine


# ── Prompt Builder Tests ─────────────────────────────────────────────────────

class TestBuildPrompt:
    def test_basic_prompt_contains_topic_and_difficulty(self):
        prompt = _build_prompt("Biology", "medium")
        assert "Biology" in prompt
        assert "medium" in prompt

    def test_prompt_includes_context_when_provided(self):
        prompt = _build_prompt("Math", "easy", context="Focus on algebra")
        assert "Focus on algebra" in prompt

    def test_prompt_excludes_context_when_none(self):
        prompt = _build_prompt("History", "hard")
        assert "Additional context" not in prompt

    def test_prompt_includes_question_count(self):
        prompt = _build_prompt("Physics", "easy", n=5)
        assert "5" in prompt


# ── JSON Extraction Tests ────────────────────────────────────────────────────

class TestExtractJson:
    def test_extract_from_fenced_block(self):
        result = _extract_json(FENCED_JSON)
        parsed = json.loads(result)
        assert "questions" in parsed

    def test_extract_plain_json(self):
        result = _extract_json(GOOD_JSON)
        parsed = json.loads(result)
        assert "questions" in parsed

    def test_extract_strips_whitespace(self):
        result = _extract_json(f"  \n{GOOD_JSON}\n  ")
        parsed = json.loads(result)
        assert "questions" in parsed


# ── Answer Normalisation Tests ───────────────────────────────────────────────

class TestNormaliseAnswer:
    def test_single_letter(self):
        assert _normalise_answer("B") == "B"

    def test_lowercase(self):
        assert _normalise_answer("c") == "C"

    def test_letter_with_text(self):
        assert _normalise_answer("A) Something") == "A"

    def test_padded_whitespace(self):
        assert _normalise_answer("  d ") == "D"


# ── Response Parser Tests ────────────────────────────────────────────────────

class TestParseResponse:
    def test_parse_good_json(self):
        questions = _parse_response(GOOD_JSON)
        assert len(questions) == 3
        assert all(isinstance(q, QuizQuestion) for q in questions)
        assert questions[0].answer == "B"

    def test_parse_fenced_json(self):
        questions = _parse_response(FENCED_JSON)
        assert len(questions) == 3

    def test_malformed_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_response(MALFORMED_JSON)

    def test_missing_questions_key_raises(self):
        with pytest.raises(ValueError, match="Unexpected JSON structure"):
            _parse_response(MISSING_QUESTIONS_KEY)

    def test_partial_questions_skips_invalid(self):
        questions = _parse_response(PARTIAL_QUESTIONS)
        assert len(questions) == 1
        assert questions[0].question == "Valid question?"

    def test_answer_as_full_text_mapped(self):
        questions = _parse_response(ANSWER_AS_FULL_TEXT)
        assert questions[0].answer == "B"

    def test_list_format_accepted(self):
        list_json = json.dumps([
            {
                "question": "Q1?",
                "options": ["A) a", "B) b", "C) c", "D) d"],
                "answer": "A",
            }
        ])
        questions = _parse_response(list_json)
        assert len(questions) == 1


# ── QuizResult Tests ─────────────────────────────────────────────────────────

class TestQuizResult:
    def test_to_dict_schema(self):
        qs = [QuizQuestion("Q?", ["A) 1", "B) 2", "C) 3", "D) 4"], "A")]
        result = QuizResult(questions=qs)
        d = result.to_dict()
        assert "questions" in d
        assert len(d["questions"]) == 1
        assert d["questions"][0]["answer"] == "A"

    def test_empty_questions_to_dict(self):
        result = QuizResult(questions=[], error="Failed")
        d = result.to_dict()
        assert d["questions"] == []


# ── QuizEngine Integration Tests (mocked API) ───────────────────────────────

class TestQuizEngineGenerate:
    def test_successful_generation(self, config):
        engine = _make_engine(config, GOOD_JSON)
        result = engine.generate(study_topic="Biology", difficulty="medium")

        assert result.error is None
        assert len(result.questions) == 3
        assert result.questions[0].answer in "ABCD"

    def test_output_matches_required_schema(self, config):
        engine = _make_engine(config, GOOD_JSON)
        result = engine.generate(study_topic="Physics")
        d = result.to_dict()

        assert isinstance(d, dict)
        assert "questions" in d
        for q in d["questions"]:
            assert "question" in q
            assert "options" in q
            assert "answer" in q
            assert len(q["options"]) == 4
            assert q["answer"] in "ABCD"

    def test_uses_default_difficulty_from_config(self, config):
        engine = _make_engine(config, GOOD_JSON)
        result = engine.generate(study_topic="Chemistry")
        assert result.error is None

    def test_context_passed_through(self, config):
        engine = _make_engine(config, GOOD_JSON)
        result = engine.generate(
            study_topic="Math",
            difficulty="hard",
            context="Focus on calculus",
        )
        assert result.error is None
        assert len(result.questions) == 3

    def test_fenced_response_parsed(self, config):
        engine = _make_engine(config, FENCED_JSON)
        result = engine.generate(study_topic="Science")
        assert result.error is None
        assert len(result.questions) == 3

    def test_api_error_retries_then_fails(self, config):
        engine = _make_engine(
            config,
            side_effect=RuntimeError("API timeout"),
        )
        result = engine.generate(study_topic="History")

        assert result.error is not None
        assert "Failed after" in result.error
        assert len(result.questions) == 0

    def test_malformed_response_retries_then_fails(self, config):
        engine = _make_engine(config, MALFORMED_JSON)
        result = engine.generate(study_topic="Geography")

        assert result.error is not None
        assert len(result.questions) == 0

    def test_empty_response_retries_then_fails(self, config):
        engine = _make_engine(config, side_effect=ValueError("Gemini returned an empty response"))
        result = engine.generate(study_topic="Art")

        assert result.error is not None

    def test_history_tracking(self, config):
        engine = _make_engine(config, GOOD_JSON)
        engine.generate(study_topic="Bio")
        engine.generate(study_topic="Chem")

        assert len(engine.history) == 2

    def test_get_stats(self, config):
        engine = _make_engine(config, GOOD_JSON)
        engine.generate(study_topic="Bio")

        stats = engine.get_stats()
        assert stats["total_sessions"] == 1
        assert stats["successful_sessions"] == 1
        assert stats["failed_sessions"] == 0
        assert stats["total_questions_generated"] == 3

    @patch("quiz_engine.time.sleep")
    def test_retry_backoff_called(self, mock_sleep, config):
        engine = _make_engine(
            config,
            side_effect=RuntimeError("flaky"),
        )
        engine.generate(study_topic="Test")

        # With max_retries=2 we expect 1 sleep call (between attempt 1 and 2)
        assert mock_sleep.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
