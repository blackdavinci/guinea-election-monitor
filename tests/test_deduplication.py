"""
Tests unitaires pour le module deduplication.
"""

import pytest
import sys
from pathlib import Path

# Ajouter le chemin du projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.deduplication import Deduplicator


class TestNormalizeUrl:
    """Tests pour la fonction normalize_url."""

    def test_normalize_url_removes_trailing_slash(self):
        url = "https://example.com/article/"
        result = Deduplicator.normalize_url(url)
        assert not result.endswith("/")

    def test_normalize_url_lowercase(self):
        url = "HTTPS://EXAMPLE.COM/Article"
        result = Deduplicator.normalize_url(url)
        assert result == result.lower()

    def test_normalize_url_removes_utm_params(self):
        url = "https://example.com/article?utm_source=twitter&utm_medium=social"
        result = Deduplicator.normalize_url(url)
        assert "utm_source" not in result
        assert "utm_medium" not in result

    def test_normalize_url_preserves_important_params(self):
        url = "https://example.com/article?id=123&page=2"
        result = Deduplicator.normalize_url(url)
        assert "id=123" in result or "id" in result

    def test_normalize_url_handles_empty(self):
        assert Deduplicator.normalize_url("") == ""


class TestIsDuplicateUrl:
    """Tests pour la fonction is_duplicate_url."""

    def test_is_duplicate_url_same(self):
        url1 = "https://example.com/article"
        url2 = "https://example.com/article"
        assert Deduplicator.is_duplicate_url(url1, url2)

    def test_is_duplicate_url_trailing_slash(self):
        url1 = "https://example.com/article"
        url2 = "https://example.com/article/"
        assert Deduplicator.is_duplicate_url(url1, url2)

    def test_is_duplicate_url_utm_params(self):
        url1 = "https://example.com/article"
        url2 = "https://example.com/article?utm_source=twitter"
        assert Deduplicator.is_duplicate_url(url1, url2)

    def test_is_duplicate_url_different(self):
        url1 = "https://example.com/article1"
        url2 = "https://example.com/article2"
        assert not Deduplicator.is_duplicate_url(url1, url2)


class TestCalculateTitleSimilarity:
    """Tests pour la fonction calculate_title_similarity."""

    def test_calculate_title_similarity_identical(self):
        title = "Élection présidentielle en Guinée"
        result = Deduplicator.calculate_title_similarity(title, title)
        assert result == 1.0

    def test_calculate_title_similarity_very_similar(self):
        title1 = "Élection présidentielle en Guinée"
        title2 = "Élection présidentielle de Guinée"
        result = Deduplicator.calculate_title_similarity(title1, title2)
        assert result > 0.8

    def test_calculate_title_similarity_different(self):
        title1 = "Élection présidentielle"
        title2 = "Match de football"
        result = Deduplicator.calculate_title_similarity(title1, title2)
        assert result < 0.5

    def test_calculate_title_similarity_empty(self):
        assert Deduplicator.calculate_title_similarity("", "test") == 0.0
        assert Deduplicator.calculate_title_similarity("test", "") == 0.0


class TestIsDuplicateTitle:
    """Tests pour la fonction is_duplicate_title."""

    def test_is_duplicate_title_identical(self):
        title = "Élection présidentielle"
        assert Deduplicator.is_duplicate_title(title, title)

    def test_is_duplicate_title_similar(self):
        title1 = "Élection présidentielle en Guinée 2025"
        title2 = "Élection présidentielle de Guinée 2025"
        assert Deduplicator.is_duplicate_title(title1, title2)

    def test_is_duplicate_title_different(self):
        title1 = "Élection présidentielle"
        title2 = "Football: résultats du match"
        assert not Deduplicator.is_duplicate_title(title1, title2)

    def test_is_duplicate_title_custom_threshold(self):
        title1 = "abc"
        title2 = "abd"
        # Avec un seuil bas, ça devrait être considéré comme doublon
        assert Deduplicator.is_duplicate_title(title1, title2, threshold=0.5)
        # Avec un seuil haut, non
        assert not Deduplicator.is_duplicate_title(title1, title2, threshold=0.95)


class TestIsDuplicateByHash:
    """Tests pour la fonction is_duplicate_by_hash."""

    def test_is_duplicate_by_hash_same(self):
        hash1 = "abc123"
        hash2 = "abc123"
        assert Deduplicator.is_duplicate_by_hash(hash1, hash2)

    def test_is_duplicate_by_hash_different(self):
        hash1 = "abc123"
        hash2 = "def456"
        assert not Deduplicator.is_duplicate_by_hash(hash1, hash2)

    def test_is_duplicate_by_hash_empty(self):
        assert not Deduplicator.is_duplicate_by_hash("", "abc")
        assert not Deduplicator.is_duplicate_by_hash("abc", "")
        assert not Deduplicator.is_duplicate_by_hash("", "")


class TestFindDuplicates:
    """Tests pour la fonction find_duplicates."""

    def test_find_duplicates_by_url(self):
        articles = [
            {"url": "https://example.com/article1", "title": "Title 1"},
            {"url": "https://example.com/article1", "title": "Title 2"},
            {"url": "https://example.com/article2", "title": "Title 3"},
        ]
        duplicates = Deduplicator.find_duplicates(articles)
        assert len(duplicates) == 1
        assert duplicates[0][2] == "url"

    def test_find_duplicates_by_title(self):
        articles = [
            {"url": "https://example.com/article1", "title": "Élection en Guinée"},
            {"url": "https://example.com/article2", "title": "Élection de Guinée"},
            {"url": "https://example.com/article3", "title": "Match de football"},
        ]
        duplicates = Deduplicator.find_duplicates(articles, check_title=True)
        # Les deux premiers articles ont des titres similaires
        assert len(duplicates) >= 1

    def test_find_duplicates_no_duplicates(self):
        articles = [
            {"url": "https://example.com/article1", "title": "Title 1"},
            {"url": "https://example.com/article2", "title": "Title 2"},
            {"url": "https://example.com/article3", "title": "Title 3"},
        ]
        duplicates = Deduplicator.find_duplicates(articles, check_title=False)
        assert len(duplicates) == 0


class TestDeduplicateList:
    """Tests pour la fonction deduplicate_list."""

    def test_deduplicate_list_removes_url_duplicates(self):
        articles = [
            {"url": "https://example.com/article1", "title": "Title 1"},
            {"url": "https://example.com/article1", "title": "Title 1 Copy"},
            {"url": "https://example.com/article2", "title": "Title 2"},
        ]
        result = Deduplicator.deduplicate_list(articles, check_title=False)
        assert len(result) == 2

    def test_deduplicate_list_removes_title_duplicates(self):
        articles = [
            {"url": "https://example.com/article1", "title": "Élection présidentielle"},
            {"url": "https://example.com/article2", "title": "Élection présidentielle"},
            {"url": "https://example.com/article3", "title": "Autre sujet"},
        ]
        result = Deduplicator.deduplicate_list(articles, check_title=True)
        assert len(result) == 2

    def test_deduplicate_list_preserves_first(self):
        articles = [
            {"url": "https://example.com/article1", "title": "First"},
            {"url": "https://example.com/article1", "title": "Second"},
        ]
        result = Deduplicator.deduplicate_list(articles)
        assert result[0]["title"] == "First"

    def test_deduplicate_list_empty(self):
        assert Deduplicator.deduplicate_list([]) == []
