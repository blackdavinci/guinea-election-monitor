"""
Tests unitaires pour le module text_processor.
"""

import pytest
import sys
from pathlib import Path

# Ajouter le chemin du projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.text_processor import TextProcessor


class TestCleanHtml:
    """Tests pour la fonction clean_html."""

    def test_clean_html_removes_tags(self):
        html = "<p>Hello <strong>World</strong></p>"
        result = TextProcessor.clean_html(html)
        assert "<p>" not in result
        assert "<strong>" not in result
        assert "Hello" in result
        assert "World" in result

    def test_clean_html_removes_scripts(self):
        html = "<p>Text</p><script>alert('test');</script><p>More</p>"
        result = TextProcessor.clean_html(html)
        assert "alert" not in result
        assert "Text" in result
        assert "More" in result

    def test_clean_html_removes_styles(self):
        html = "<style>.class { color: red; }</style><p>Content</p>"
        result = TextProcessor.clean_html(html)
        assert "color" not in result
        assert "Content" in result

    def test_clean_html_handles_empty_string(self):
        assert TextProcessor.clean_html("") == ""

    def test_clean_html_handles_none(self):
        assert TextProcessor.clean_html(None) == ""

    def test_clean_html_decodes_entities(self):
        html = "&nbsp;&amp;&lt;&gt;"
        result = TextProcessor.clean_html(html)
        assert "&" in result


class TestNormalizeText:
    """Tests pour la fonction normalize_text."""

    def test_normalize_text_lowercase(self):
        result = TextProcessor.normalize_text("HELLO World")
        assert result == "hello world"

    def test_normalize_text_removes_extra_spaces(self):
        result = TextProcessor.normalize_text("hello    world")
        assert result == "hello world"

    def test_normalize_text_trims(self):
        result = TextProcessor.normalize_text("  hello  ")
        assert result == "hello"

    def test_normalize_text_preserves_accents_by_default(self):
        result = TextProcessor.normalize_text("élection")
        assert "é" in result

    def test_normalize_text_removes_accents_when_requested(self):
        result = TextProcessor.normalize_text("élection", remove_accents=True)
        assert "é" not in result
        assert "election" in result

    def test_normalize_text_handles_empty(self):
        assert TextProcessor.normalize_text("") == ""


class TestExtractKeywords:
    """Tests pour la fonction extract_keywords."""

    def test_extract_keywords_finds_matches(self):
        text = "L'élection présidentielle en Guinée"
        keywords = ["élection", "présidentielle", "vote"]
        result = TextProcessor.extract_keywords(text, keywords)
        assert "élection" in result
        assert "présidentielle" in result
        assert "vote" not in result

    def test_extract_keywords_case_insensitive(self):
        text = "ELECTION présidentielle"
        keywords = ["élection", "Présidentielle"]
        result = TextProcessor.extract_keywords(text, keywords)
        # Note: la recherche est sensible à la casse pour les accents
        assert "Présidentielle" in result

    def test_extract_keywords_empty_text(self):
        result = TextProcessor.extract_keywords("", ["test"])
        assert result == []

    def test_extract_keywords_empty_list(self):
        result = TextProcessor.extract_keywords("test", [])
        assert result == []


class TestGenerateSummary:
    """Tests pour la fonction generate_summary."""

    def test_generate_summary_truncates(self):
        text = "A" * 300
        result = TextProcessor.generate_summary(text, max_length=100)
        assert len(result) <= 103  # 100 + "..."

    def test_generate_summary_short_text(self):
        text = "Short text"
        result = TextProcessor.generate_summary(text, max_length=100)
        assert result == text

    def test_generate_summary_cuts_at_word(self):
        text = "Hello world this is a test"
        result = TextProcessor.generate_summary(text, max_length=15)
        assert result.endswith("...")
        # Should cut at a word boundary
        assert "Hello" in result

    def test_generate_summary_handles_empty(self):
        assert TextProcessor.generate_summary("") == ""


class TestDetectLanguage:
    """Tests pour la fonction detect_language."""

    def test_detect_language_french(self):
        text = "Le président a annoncé les élections pour le mois prochain"
        result = TextProcessor.detect_language(text)
        assert result == "fr"

    def test_detect_language_english(self):
        text = "The president announced the elections for next month"
        result = TextProcessor.detect_language(text)
        assert result == "en"

    def test_detect_language_default(self):
        result = TextProcessor.detect_language("")
        assert result == "fr"  # Default


class TestComputeHash:
    """Tests pour la fonction compute_hash."""

    def test_compute_hash_consistent(self):
        text = "test content"
        hash1 = TextProcessor.compute_hash(text)
        hash2 = TextProcessor.compute_hash(text)
        assert hash1 == hash2

    def test_compute_hash_different_for_different_text(self):
        hash1 = TextProcessor.compute_hash("text1")
        hash2 = TextProcessor.compute_hash("text2")
        assert hash1 != hash2

    def test_compute_hash_handles_empty(self):
        assert TextProcessor.compute_hash("") == ""

    def test_compute_hash_is_sha256(self):
        result = TextProcessor.compute_hash("test")
        assert len(result) == 64  # SHA-256 produces 64 hex characters


class TestExtractSentences:
    """Tests pour la fonction extract_sentences."""

    def test_extract_sentences_basic(self):
        text = "First sentence. Second sentence! Third one?"
        result = TextProcessor.extract_sentences(text)
        assert len(result) == 3

    def test_extract_sentences_filters_short(self):
        text = "OK. This is a longer sentence that should pass."
        result = TextProcessor.extract_sentences(text, min_length=10)
        assert len(result) == 1
        assert "longer" in result[0]

    def test_extract_sentences_empty(self):
        assert TextProcessor.extract_sentences("") == []


class TestRemoveStopwords:
    """Tests pour la fonction remove_stopwords."""

    def test_remove_stopwords_french(self):
        text = "le chat est sur la table"
        result = TextProcessor.remove_stopwords(text)
        assert "le" not in result.split()
        assert "est" not in result.split()
        assert "chat" in result
        assert "table" in result

    def test_remove_stopwords_empty(self):
        assert TextProcessor.remove_stopwords("") == ""


class TestGetWordFrequency:
    """Tests pour la fonction get_word_frequency."""

    def test_get_word_frequency_counts(self):
        text = "élection élection vote président"
        result = TextProcessor.get_word_frequency(text)
        # "élection" should be most frequent
        assert result[0][0] == "élection"
        assert result[0][1] == 2

    def test_get_word_frequency_limits(self):
        text = "a b c d e f g h i j"
        result = TextProcessor.get_word_frequency(text, top_n=3)
        assert len(result) <= 3

    def test_get_word_frequency_empty(self):
        assert TextProcessor.get_word_frequency("") == []
