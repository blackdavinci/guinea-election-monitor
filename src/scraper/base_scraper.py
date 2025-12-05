"""
Classe abstraite de base pour les scrapers.
"""

import logging
import random
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config.settings import SCRAPING_CONFIG, USER_AGENTS

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Classe abstraite de base pour tous les scrapers."""

    def __init__(
        self,
        source_name: str,
        base_url: str,
        request_delay: float = None,
        timeout: int = None,
        max_retries: int = None,
    ):
        self.source_name = source_name
        self.base_url = base_url
        self.request_delay = request_delay or SCRAPING_CONFIG["request_delay"]
        self.timeout = timeout or SCRAPING_CONFIG["request_timeout"]
        self.max_retries = max_retries or SCRAPING_CONFIG["max_retries"]

        # Session HTTP avec configuration
        self.session = requests.Session()
        self._update_user_agent()

    def _update_user_agent(self) -> None:
        """Met à jour le User-Agent avec rotation."""
        user_agent = random.choice(USER_AGENTS)
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })

    def _respect_delay(self) -> None:
        """Respecte le délai entre les requêtes."""
        delay = self.request_delay + random.uniform(0, 1)
        time.sleep(delay)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.RequestException, requests.Timeout)),
    )
    def fetch_page(self, url: str, encoding: str = "utf-8") -> Optional[str]:
        """
        Récupère le contenu HTML d'une page.

        Args:
            url: URL de la page à récupérer
            encoding: Encodage de la page

        Returns:
            Contenu HTML de la page ou None en cas d'erreur
        """
        try:
            # Rotation du User-Agent occasionnelle
            if random.random() < 0.3:
                self._update_user_agent()

            response = self.session.get(
                url,
                timeout=self.timeout,
                allow_redirects=True,
            )
            response.raise_for_status()

            # Gérer l'encodage
            if encoding:
                response.encoding = encoding
            elif response.encoding is None:
                response.encoding = "utf-8"

            logger.debug(f"Page récupérée avec succès: {url}")
            return response.text

        except requests.Timeout:
            logger.warning(f"Timeout lors de la récupération de {url}")
            raise
        except requests.RequestException as e:
            logger.error(f"Erreur lors de la récupération de {url}: {e}")
            raise

    def parse_html(self, html: str) -> BeautifulSoup:
        """
        Parse le contenu HTML avec BeautifulSoup.

        Args:
            html: Contenu HTML à parser

        Returns:
            Objet BeautifulSoup
        """
        return BeautifulSoup(html, "lxml")

    def make_absolute_url(self, url: str) -> str:
        """
        Convertit une URL relative en URL absolue.

        Args:
            url: URL (relative ou absolue)

        Returns:
            URL absolue
        """
        if url.startswith(("http://", "https://")):
            return url
        return urljoin(self.base_url, url)

    def is_valid_url(self, url: str) -> bool:
        """
        Vérifie si une URL est valide et appartient au même domaine.

        Args:
            url: URL à vérifier

        Returns:
            True si l'URL est valide
        """
        try:
            parsed = urlparse(url)
            base_parsed = urlparse(self.base_url)
            return (
                parsed.scheme in ("http", "https")
                and parsed.netloc == base_parsed.netloc
            )
        except Exception:
            return False

    def calculate_relevance(
        self,
        text: str,
        keywords_dict: Dict[str, List[Dict[str, Any]]],
    ) -> tuple[float, List[str]]:
        """
        Calcule le score de pertinence d'un texte basé sur les mots-clés.

        Un article doit contenir au moins un mot-clé des catégories "election"
        ou "processus" pour être considéré pertinent.

        Args:
            text: Texte à analyser
            keywords_dict: Dictionnaire des mots-clés par catégorie

        Returns:
            Tuple (score de pertinence entre 0 et 1, liste des mots-clés trouvés)
        """
        if not text:
            return 0.0, []

        text_lower = text.lower()
        total_score = 0.0
        keywords_found = []

        # Catégories obligatoires - au moins un mot-clé de ces catégories requis
        required_categories = {"election", "processus"}
        has_required_keyword = False

        for category, keywords_list in keywords_dict.items():
            for kw_info in keywords_list:
                keyword = kw_info["keyword"].lower()
                weight = kw_info.get("weight", 1.0)

                if keyword in text_lower:
                    total_score += weight
                    keywords_found.append(kw_info["keyword"])

                    # Vérifier si c'est un mot-clé obligatoire
                    if category in required_categories:
                        has_required_keyword = True

        # Si aucun mot-clé électoral/processus trouvé, score = 0
        if not has_required_keyword:
            return 0.0, keywords_found

        # Normaliser le score entre 0 et 1
        # 3 mots-clés importants = score max
        relevance = min(1.0, total_score / 3.0)

        return round(relevance, 3), list(set(keywords_found))

    @abstractmethod
    def parse_article_list(self, html: str) -> List[Dict[str, Any]]:
        """
        Parse la liste des articles depuis une page.

        Args:
            html: Contenu HTML de la page liste

        Returns:
            Liste de dictionnaires avec les infos de base des articles
        """
        pass

    @abstractmethod
    def parse_article_content(self, html: str) -> Dict[str, Any]:
        """
        Parse le contenu complet d'un article.

        Args:
            html: Contenu HTML de la page article

        Returns:
            Dictionnaire avec le contenu de l'article
        """
        pass

    def scrape_article_list(
        self,
        url: str,
        encoding: str = "utf-8",
    ) -> List[Dict[str, Any]]:
        """
        Scrape une page liste d'articles.

        Args:
            url: URL de la page liste
            encoding: Encodage de la page

        Returns:
            Liste des articles trouvés
        """
        html = self.fetch_page(url, encoding)
        if html:
            return self.parse_article_list(html)
        return []

    def scrape_article(
        self,
        url: str,
        encoding: str = "utf-8",
        keywords_dict: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Scrape un article complet.

        Args:
            url: URL de l'article
            encoding: Encodage de la page
            keywords_dict: Dictionnaire des mots-clés pour calculer la pertinence

        Returns:
            Dictionnaire avec les données de l'article
        """
        self._respect_delay()

        html = self.fetch_page(url, encoding)
        if not html:
            return None

        article_data = self.parse_article_content(html)
        article_data["url"] = url

        # Calculer la pertinence si des mots-clés sont fournis
        if keywords_dict:
            text_to_analyze = f"{article_data.get('title', '')} {article_data.get('content', '')}"
            relevance, keywords_found = self.calculate_relevance(
                text_to_analyze, keywords_dict
            )
            article_data["relevance_score"] = relevance
            article_data["keywords_matched"] = keywords_found

        return article_data

    def close(self) -> None:
        """Ferme la session HTTP."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
