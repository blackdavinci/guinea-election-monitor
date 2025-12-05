"""
Utilitaires pour la détection de doublons.
"""

import logging
from typing import Optional, List
from urllib.parse import urlparse, parse_qs, urlencode

try:
    from Levenshtein import ratio as levenshtein_ratio
except ImportError:
    # Fallback si python-Levenshtein n'est pas installé
    def levenshtein_ratio(s1: str, s2: str) -> float:
        """Calcul simplifié de similarité."""
        if not s1 or not s2:
            return 0.0
        if s1 == s2:
            return 1.0

        len1, len2 = len(s1), len(s2)
        if len1 == 0 or len2 == 0:
            return 0.0

        # Ratio basé sur la longueur commune
        common = sum(1 for c in s1 if c in s2)
        return 2.0 * common / (len1 + len2)

from .text_processor import TextProcessor

logger = logging.getLogger(__name__)


class Deduplicator:
    """Classe pour la détection de doublons d'articles."""

    # Seuil de similarité pour considérer deux textes comme identiques
    TITLE_SIMILARITY_THRESHOLD = 0.85
    CONTENT_SIMILARITY_THRESHOLD = 0.90

    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalise une URL pour la comparaison.

        Args:
            url: URL à normaliser

        Returns:
            URL normalisée
        """
        if not url:
            return ""

        # Parser l'URL
        parsed = urlparse(url.lower().strip())

        # Reconstruire sans fragments et avec params triés
        query_params = parse_qs(parsed.query)
        # Supprimer les paramètres de tracking courants
        tracking_params = {
            "utm_source", "utm_medium", "utm_campaign", "utm_content",
            "utm_term", "fbclid", "gclid", "ref", "source",
        }
        filtered_params = {
            k: v for k, v in query_params.items()
            if k.lower() not in tracking_params
        }

        # Reconstruire l'URL
        path = parsed.path.rstrip("/")
        if filtered_params:
            query = urlencode(filtered_params, doseq=True)
            return f"{parsed.scheme}://{parsed.netloc}{path}?{query}"
        return f"{parsed.scheme}://{parsed.netloc}{path}"

    @staticmethod
    def is_duplicate_url(url1: str, url2: str) -> bool:
        """
        Vérifie si deux URLs sont identiques (après normalisation).

        Args:
            url1: Première URL
            url2: Deuxième URL

        Returns:
            True si les URLs sont identiques
        """
        return Deduplicator.normalize_url(url1) == Deduplicator.normalize_url(url2)

    @staticmethod
    def calculate_title_similarity(title1: str, title2: str) -> float:
        """
        Calcule la similarité entre deux titres.

        Args:
            title1: Premier titre
            title2: Deuxième titre

        Returns:
            Score de similarité entre 0 et 1
        """
        if not title1 or not title2:
            return 0.0

        # Normaliser les titres
        t1 = TextProcessor.normalize_text(title1, remove_accents=True)
        t2 = TextProcessor.normalize_text(title2, remove_accents=True)

        if t1 == t2:
            return 1.0

        return levenshtein_ratio(t1, t2)

    @staticmethod
    def is_duplicate_title(
        title1: str,
        title2: str,
        threshold: float = None,
    ) -> bool:
        """
        Vérifie si deux titres sont similaires (potentiellement doublons).

        Args:
            title1: Premier titre
            title2: Deuxième titre
            threshold: Seuil de similarité (défaut: TITLE_SIMILARITY_THRESHOLD)

        Returns:
            True si les titres sont similaires
        """
        if threshold is None:
            threshold = Deduplicator.TITLE_SIMILARITY_THRESHOLD

        similarity = Deduplicator.calculate_title_similarity(title1, title2)
        return similarity >= threshold

    @staticmethod
    def calculate_content_similarity(content1: str, content2: str) -> float:
        """
        Calcule la similarité entre deux contenus.

        Args:
            content1: Premier contenu
            content2: Deuxième contenu

        Returns:
            Score de similarité entre 0 et 1
        """
        if not content1 or not content2:
            return 0.0

        # Normaliser les contenus
        c1 = TextProcessor.normalize_text(content1, remove_accents=True)
        c2 = TextProcessor.normalize_text(content2, remove_accents=True)

        if c1 == c2:
            return 1.0

        # Pour les longs textes, utiliser une approche par chunks
        if len(c1) > 1000 or len(c2) > 1000:
            return Deduplicator._calculate_chunk_similarity(c1, c2)

        return levenshtein_ratio(c1, c2)

    @staticmethod
    def _calculate_chunk_similarity(text1: str, text2: str, chunk_size: int = 200) -> float:
        """
        Calcule la similarité par chunks pour les longs textes.

        Args:
            text1: Premier texte
            text2: Deuxième texte
            chunk_size: Taille des chunks

        Returns:
            Score de similarité moyen
        """
        # Diviser en chunks
        chunks1 = [text1[i:i + chunk_size] for i in range(0, len(text1), chunk_size)]
        chunks2 = [text2[i:i + chunk_size] for i in range(0, len(text2), chunk_size)]

        if not chunks1 or not chunks2:
            return 0.0

        # Calculer la similarité moyenne des premiers chunks
        num_chunks = min(5, len(chunks1), len(chunks2))
        similarities = []

        for i in range(num_chunks):
            sim = levenshtein_ratio(chunks1[i], chunks2[i])
            similarities.append(sim)

        return sum(similarities) / len(similarities) if similarities else 0.0

    @staticmethod
    def is_duplicate_content(
        content1: str,
        content2: str,
        threshold: float = None,
    ) -> bool:
        """
        Vérifie si deux contenus sont similaires.

        Args:
            content1: Premier contenu
            content2: Deuxième contenu
            threshold: Seuil de similarité

        Returns:
            True si les contenus sont similaires
        """
        if threshold is None:
            threshold = Deduplicator.CONTENT_SIMILARITY_THRESHOLD

        similarity = Deduplicator.calculate_content_similarity(content1, content2)
        return similarity >= threshold

    @staticmethod
    def is_duplicate_by_hash(hash1: str, hash2: str) -> bool:
        """
        Vérifie si deux articles sont identiques par leur hash.

        Args:
            hash1: Hash du premier article
            hash2: Hash du deuxième article

        Returns:
            True si les hash sont identiques
        """
        if not hash1 or not hash2:
            return False
        return hash1 == hash2

    @staticmethod
    def find_duplicates(
        articles: List[dict],
        check_title: bool = True,
        check_content: bool = False,
    ) -> List[tuple]:
        """
        Trouve les doublons dans une liste d'articles.

        Args:
            articles: Liste de dictionnaires avec 'title', 'content', 'url'
            check_title: Vérifier les titres similaires
            check_content: Vérifier les contenus similaires

        Returns:
            Liste de tuples (index1, index2, type_de_doublon)
        """
        duplicates = []
        n = len(articles)

        for i in range(n):
            for j in range(i + 1, n):
                art1, art2 = articles[i], articles[j]

                # Vérifier l'URL
                if Deduplicator.is_duplicate_url(
                    art1.get("url", ""),
                    art2.get("url", ""),
                ):
                    duplicates.append((i, j, "url"))
                    continue

                # Vérifier le titre
                if check_title and Deduplicator.is_duplicate_title(
                    art1.get("title", ""),
                    art2.get("title", ""),
                ):
                    duplicates.append((i, j, "title"))
                    continue

                # Vérifier le contenu
                if check_content and Deduplicator.is_duplicate_content(
                    art1.get("content", ""),
                    art2.get("content", ""),
                ):
                    duplicates.append((i, j, "content"))

        return duplicates

    @staticmethod
    def deduplicate_list(
        articles: List[dict],
        check_title: bool = True,
    ) -> List[dict]:
        """
        Supprime les doublons d'une liste d'articles.

        Args:
            articles: Liste d'articles
            check_title: Vérifier aussi les titres similaires

        Returns:
            Liste dédupliquée
        """
        if not articles:
            return []

        seen_urls = set()
        seen_titles = []
        unique_articles = []

        for article in articles:
            url = Deduplicator.normalize_url(article.get("url", ""))

            # Vérifier l'URL
            if url in seen_urls:
                continue

            # Vérifier le titre si demandé
            if check_title:
                title = article.get("title", "")
                is_dup = False
                for seen_title in seen_titles:
                    if Deduplicator.is_duplicate_title(title, seen_title):
                        is_dup = True
                        break
                if is_dup:
                    continue
                seen_titles.append(title)

            seen_urls.add(url)
            unique_articles.append(article)

        logger.info(
            f"Déduplication: {len(articles)} -> {len(unique_articles)} articles"
        )
        return unique_articles
