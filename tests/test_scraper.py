"""
Tests unitaires pour le module scraper.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Ajouter le chemin du projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scraper.base_scraper import BaseScraper
from src.scraper.generic_scraper import GenericScraper


# HTML de test
SAMPLE_ARTICLE_LIST_HTML = """
<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
    <article class="post">
        <h2 class="entry-title"><a href="/article/1">Premier article sur l'élection</a></h2>
        <time class="entry-date" datetime="2024-01-15">15 janvier 2024</time>
    </article>
    <article class="post">
        <h2 class="entry-title"><a href="/article/2">Deuxième article politique</a></h2>
        <time class="entry-date" datetime="2024-01-16">16 janvier 2024</time>
    </article>
</body>
</html>
"""

SAMPLE_ARTICLE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Article</title></head>
<body>
    <article>
        <h1 class="entry-title">Titre de l'article sur les élections</h1>
        <time class="entry-date" datetime="2024-01-15">15 janvier 2024</time>
        <div class="entry-content">
            <p>Contenu de l'article sur les élections présidentielles en Guinée.</p>
            <p>Le président Mamadi Doumbouya a annoncé le chronogramme.</p>
        </div>
    </article>
</body>
</html>
"""


class TestGenericScraperInit:
    """Tests pour l'initialisation du GenericScraper."""

    def test_init_with_selectors(self):
        selectors = {
            "article_list": "article.post",
            "title": "h2 a",
            "link": "h2 a",
            "date": "time",
            "content": "div.content",
        }
        scraper = GenericScraper(
            source_name="Test",
            base_url="https://example.com",
            selectors=selectors,
        )
        assert scraper.source_name == "Test"
        assert scraper.base_url == "https://example.com"
        assert scraper.article_list_selector == "article.post"


class TestGenericScraperParseArticleList:
    """Tests pour parse_article_list."""

    def test_parse_article_list_extracts_articles(self):
        selectors = {
            "article_list": "article.post",
            "title": "h2.entry-title a",
            "link": "h2.entry-title a",
            "date": "time.entry-date",
        }
        scraper = GenericScraper(
            source_name="Test",
            base_url="https://example.com",
            selectors=selectors,
        )

        articles = scraper.parse_article_list(SAMPLE_ARTICLE_LIST_HTML)

        assert len(articles) == 2
        assert articles[0]["title"] == "Premier article sur l'élection"
        assert articles[0]["url"] == "https://example.com/article/1"
        assert articles[1]["title"] == "Deuxième article politique"

    def test_parse_article_list_handles_empty_html(self):
        selectors = {"article_list": "article"}
        scraper = GenericScraper(
            source_name="Test",
            base_url="https://example.com",
            selectors=selectors,
        )

        articles = scraper.parse_article_list("<html><body></body></html>")
        assert articles == []


class TestGenericScraperParseArticleContent:
    """Tests pour parse_article_content."""

    def test_parse_article_content_extracts_data(self):
        selectors = {
            "article_list": "article",
            "title": "h1.entry-title",
            "date": "time.entry-date",
            "content": "div.entry-content",
        }
        scraper = GenericScraper(
            source_name="Test",
            base_url="https://example.com",
            selectors=selectors,
        )

        article = scraper.parse_article_content(SAMPLE_ARTICLE_HTML)

        assert "élections" in article["title"]
        assert "élections" in article["content"]
        assert "Guinée" in article["content"]
        assert article["published_date"] is not None


class TestCalculateRelevance:
    """Tests pour calculate_relevance."""

    def test_calculate_relevance_with_keywords(self):
        selectors = {"article_list": "article"}
        scraper = GenericScraper(
            source_name="Test",
            base_url="https://example.com",
            selectors=selectors,
        )

        keywords_dict = {
            "election": [
                {"keyword": "élection", "weight": 1.0},
                {"keyword": "vote", "weight": 0.8},
            ],
            "personnalites": [
                {"keyword": "Mamadi Doumbouya", "weight": 0.9},
            ],
        }

        text = "L'élection présidentielle en Guinée. Mamadi Doumbouya a parlé."
        score, keywords = scraper.calculate_relevance(text, keywords_dict)

        assert score > 0
        assert "élection" in keywords
        assert "Mamadi Doumbouya" in keywords

    def test_calculate_relevance_no_keywords(self):
        selectors = {"article_list": "article"}
        scraper = GenericScraper(
            source_name="Test",
            base_url="https://example.com",
            selectors=selectors,
        )

        keywords_dict = {
            "election": [{"keyword": "xyz123", "weight": 1.0}],
        }

        text = "Un texte sans rapport avec les élections"
        score, keywords = scraper.calculate_relevance(text, keywords_dict)

        assert score == 0
        assert keywords == []

    def test_calculate_relevance_empty_text(self):
        selectors = {"article_list": "article"}
        scraper = GenericScraper(
            source_name="Test",
            base_url="https://example.com",
            selectors=selectors,
        )

        keywords_dict = {"cat": [{"keyword": "test", "weight": 1.0}]}
        score, keywords = scraper.calculate_relevance("", keywords_dict)

        assert score == 0.0
        assert keywords == []


class TestMakeAbsoluteUrl:
    """Tests pour make_absolute_url."""

    def test_make_absolute_url_relative(self):
        selectors = {"article_list": "article"}
        scraper = GenericScraper(
            source_name="Test",
            base_url="https://example.com",
            selectors=selectors,
        )

        result = scraper.make_absolute_url("/article/123")
        assert result == "https://example.com/article/123"

    def test_make_absolute_url_already_absolute(self):
        selectors = {"article_list": "article"}
        scraper = GenericScraper(
            source_name="Test",
            base_url="https://example.com",
            selectors=selectors,
        )

        url = "https://other.com/article"
        result = scraper.make_absolute_url(url)
        assert result == url


class TestIsValidUrl:
    """Tests pour is_valid_url."""

    def test_is_valid_url_same_domain(self):
        selectors = {"article_list": "article"}
        scraper = GenericScraper(
            source_name="Test",
            base_url="https://example.com",
            selectors=selectors,
        )

        assert scraper.is_valid_url("https://example.com/article")

    def test_is_valid_url_different_domain(self):
        selectors = {"article_list": "article"}
        scraper = GenericScraper(
            source_name="Test",
            base_url="https://example.com",
            selectors=selectors,
        )

        assert not scraper.is_valid_url("https://other.com/article")

    def test_is_valid_url_invalid(self):
        selectors = {"article_list": "article"}
        scraper = GenericScraper(
            source_name="Test",
            base_url="https://example.com",
            selectors=selectors,
        )

        assert not scraper.is_valid_url("not a url")


class TestParseDate:
    """Tests pour _parse_date."""

    def test_parse_date_iso_format(self):
        selectors = {"article_list": "article"}
        scraper = GenericScraper(
            source_name="Test",
            base_url="https://example.com",
            selectors=selectors,
        )

        result = scraper._parse_date("2024-01-15T10:30:00")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_date_french_format(self):
        selectors = {"article_list": "article"}
        scraper = GenericScraper(
            source_name="Test",
            base_url="https://example.com",
            selectors=selectors,
        )

        result = scraper._parse_date("15 janvier 2024")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1

    def test_parse_date_invalid(self):
        selectors = {"article_list": "article"}
        scraper = GenericScraper(
            source_name="Test",
            base_url="https://example.com",
            selectors=selectors,
        )

        result = scraper._parse_date("not a date")
        assert result is None

    def test_parse_date_empty(self):
        selectors = {"article_list": "article"}
        scraper = GenericScraper(
            source_name="Test",
            base_url="https://example.com",
            selectors=selectors,
        )

        assert scraper._parse_date("") is None
        assert scraper._parse_date(None) is None
