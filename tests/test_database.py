"""
Tests unitaires pour les opérations de base de données.

Note: Ces tests nécessitent une base de données PostgreSQL de test.
Pour les exécuter, configurez une base de test dans .env.test
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Ajouter le chemin du projet au PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestSourceModel:
    """Tests pour le modèle Source (sans connexion DB)."""

    def test_source_repr(self):
        from src.database.models import Source

        source = Source(id=1, name="Test Source", base_url="https://example.com")
        repr_str = repr(source)
        assert "Source" in repr_str
        assert "Test Source" in repr_str


class TestArticleModel:
    """Tests pour le modèle Article (sans connexion DB)."""

    def test_article_repr(self):
        from src.database.models import Article

        article = Article(
            id=1,
            source_id=1,
            title="Un titre très long qui devrait être tronqué dans la représentation",
            url="https://example.com/article",
        )
        repr_str = repr(article)
        assert "Article" in repr_str
        assert "..." in repr_str  # Titre tronqué


class TestKeywordModel:
    """Tests pour le modèle Keyword (sans connexion DB)."""

    def test_keyword_repr(self):
        from src.database.models import Keyword

        keyword = Keyword(id=1, keyword="élection", category="election")
        repr_str = repr(keyword)
        assert "Keyword" in repr_str
        assert "élection" in repr_str


class TestScrapingLogModel:
    """Tests pour le modèle ScrapingLog (sans connexion DB)."""

    def test_scraping_log_repr(self):
        from src.database.models import ScrapingLog

        log = ScrapingLog(id=1, source_id=1, status="success")
        repr_str = repr(log)
        assert "ScrapingLog" in repr_str
        assert "success" in repr_str


# Tests avec mock de session

class TestArticleOperationsMocked:
    """Tests pour ArticleOperations avec session mockée."""

    def test_create_article_success(self):
        from src.database.operations import ArticleOperations
        from src.database.models import Article

        # Mock de la session
        mock_session = MagicMock()
        mock_session.flush = MagicMock()

        # Créer un article
        article = ArticleOperations.create(
            mock_session,
            source_id=1,
            title="Test Article",
            url="https://example.com/test",
            content="Test content",
        )

        # Vérifier que add a été appelé
        mock_session.add.assert_called_once()

    def test_exists_by_url(self):
        from src.database.operations import ArticleOperations

        mock_session = MagicMock()
        # Simuler qu'un article existe
        mock_session.execute.return_value.scalar.return_value = 1

        result = ArticleOperations.exists_by_url(mock_session, "https://example.com/test")
        assert result is True

    def test_not_exists_by_url(self):
        from src.database.operations import ArticleOperations

        mock_session = MagicMock()
        # Simuler qu'aucun article n'existe
        mock_session.execute.return_value.scalar.return_value = 0

        result = ArticleOperations.exists_by_url(mock_session, "https://example.com/test")
        assert result is False


class TestSourceOperationsMocked:
    """Tests pour SourceOperations avec session mockée."""

    def test_get_all_active(self):
        from src.database.operations import SourceOperations
        from src.database.models import Source

        mock_session = MagicMock()

        # Créer des sources mock
        mock_sources = [
            Source(id=1, name="Source 1", base_url="https://example1.com", is_active=True),
            Source(id=2, name="Source 2", base_url="https://example2.com", is_active=True),
        ]

        mock_session.execute.return_value.scalars.return_value.all.return_value = mock_sources

        result = SourceOperations.get_all_active(mock_session)
        assert len(result) == 2

    def test_get_by_name(self):
        from src.database.operations import SourceOperations
        from src.database.models import Source

        mock_session = MagicMock()

        mock_source = Source(id=1, name="Test Source", base_url="https://example.com")
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_source

        result = SourceOperations.get_by_name(mock_session, "Test Source")
        assert result is not None
        assert result.name == "Test Source"


class TestKeywordOperationsMocked:
    """Tests pour KeywordOperations avec session mockée."""

    def test_get_all_active(self):
        from src.database.operations import KeywordOperations
        from src.database.models import Keyword

        mock_session = MagicMock()

        mock_keywords = [
            Keyword(id=1, keyword="élection", category="election", is_active=True),
            Keyword(id=2, keyword="vote", category="election", is_active=True),
        ]

        mock_session.execute.return_value.scalars.return_value.all.return_value = mock_keywords

        result = KeywordOperations.get_all_active(mock_session)
        assert len(result) == 2

    def test_get_keywords_dict(self):
        from src.database.operations import KeywordOperations
        from src.database.models import Keyword

        mock_session = MagicMock()

        mock_keywords = [
            Keyword(id=1, keyword="élection", category="election", weight=1.0, is_active=True),
            Keyword(id=2, keyword="vote", category="election", weight=0.8, is_active=True),
            Keyword(id=3, keyword="président", category="personnalites", weight=0.9, is_active=True),
        ]

        mock_session.execute.return_value.scalars.return_value.all.return_value = mock_keywords

        result = KeywordOperations.get_keywords_dict(mock_session)

        assert "election" in result
        assert "personnalites" in result
        assert len(result["election"]) == 2
        assert len(result["personnalites"]) == 1


class TestLogOperationsMocked:
    """Tests pour LogOperations avec session mockée."""

    def test_create_log(self):
        from src.database.operations import LogOperations

        mock_session = MagicMock()

        log = LogOperations.create(mock_session, source_id=1)

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    def test_update_log(self):
        from src.database.operations import LogOperations
        from src.database.models import ScrapingLog

        mock_session = MagicMock()
        mock_log = ScrapingLog(id=1, source_id=1, status="running")
        mock_session.get.return_value = mock_log

        result = LogOperations.update(
            mock_session,
            log_id=1,
            status="success",
            articles_found=10,
            articles_saved=8,
        )

        assert result.status == "success"
        assert result.articles_found == 10
        assert result.articles_saved == 8
