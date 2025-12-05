"""
Scraper générique utilisant des sélecteurs CSS configurables.
"""

import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from dateutil import parser as date_parser
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class GenericScraper(BaseScraper):
    """
    Scraper générique qui utilise des sélecteurs CSS pour extraire les données.
    """

    def __init__(
        self,
        source_name: str,
        base_url: str,
        selectors: Dict[str, str],
        encoding: str = "utf-8",
        **kwargs,
    ):
        """
        Initialise le scraper générique.

        Args:
            source_name: Nom de la source
            base_url: URL de base du site
            selectors: Dictionnaire des sélecteurs CSS
            encoding: Encodage du site
            **kwargs: Arguments supplémentaires pour BaseScraper
        """
        super().__init__(source_name, base_url, **kwargs)

        self.selectors = selectors
        self.encoding = encoding

        # Sélecteurs par défaut
        self.article_list_selector = selectors.get("article_list", "article")
        self.title_selector = selectors.get("title", "h2 a")
        self.link_selector = selectors.get("link", "h2 a")
        self.date_selector = selectors.get("date", "time")
        self.content_selector = selectors.get("content", "div.content")

    def parse_article_list(self, html: str) -> List[Dict[str, Any]]:
        """
        Parse la liste des articles depuis une page.

        Args:
            html: Contenu HTML de la page

        Returns:
            Liste de dictionnaires avec les infos de base des articles
        """
        soup = self.parse_html(html)
        articles = []

        article_elements = soup.select(self.article_list_selector)
        logger.debug(f"Trouvé {len(article_elements)} éléments article")

        for element in article_elements:
            try:
                article_info = self._extract_article_info(element)
                if article_info and article_info.get("url"):
                    articles.append(article_info)
            except Exception as e:
                logger.warning(f"Erreur lors de l'extraction d'un article: {e}")
                continue

        logger.info(f"[{self.source_name}] {len(articles)} articles extraits de la liste")
        return articles

    def _extract_article_info(self, element: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """
        Extrait les informations de base d'un article depuis un élément HTML.

        Args:
            element: Élément HTML de l'article

        Returns:
            Dictionnaire avec les infos ou None
        """
        # Extraire le titre
        title_elem = element.select_one(self.title_selector)
        title = title_elem.get_text(strip=True) if title_elem else None

        # Extraire le lien
        link_elem = element.select_one(self.link_selector)
        if link_elem:
            url = link_elem.get("href", "")
            url = self.make_absolute_url(url)
        else:
            url = None

        # Extraire la date
        date_elem = element.select_one(self.date_selector)
        published_date = None
        if date_elem:
            # Essayer l'attribut datetime d'abord
            date_str = date_elem.get("datetime") or date_elem.get_text(strip=True)
            published_date = self._parse_date(date_str)

        if not title or not url:
            return None

        return {
            "title": title,
            "url": url,
            "published_date": published_date,
        }

    def parse_article_content(self, html: str) -> Dict[str, Any]:
        """
        Parse le contenu complet d'un article.

        Args:
            html: Contenu HTML de la page article

        Returns:
            Dictionnaire avec le contenu de l'article
        """
        soup = self.parse_html(html)

        # Extraire le titre (parfois différent de la liste)
        title = self._extract_title(soup)

        # Extraire le contenu
        content = self._extract_content(soup)

        # Extraire la date
        published_date = self._extract_date(soup)

        return {
            "title": title,
            "content": content,
            "published_date": published_date,
        }

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extrait le titre de l'article."""
        # Essayer plusieurs sélecteurs courants
        selectors = [
            "h1.entry-title",
            "h1.post-title",
            "h1.article-title",
            "article h1",
            ".post h1",
            "h1",
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                title = elem.get_text(strip=True)
                if title and len(title) > 5:
                    return title

        return ""

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extrait le contenu de l'article."""
        # Essayer le sélecteur configuré d'abord
        content_elem = soup.select_one(self.content_selector)

        if not content_elem:
            # Essayer d'autres sélecteurs courants
            selectors = [
                "div.entry-content",
                "div.post-content",
                "div.article-content",
                "div.article-body",
                "article .content",
                "article",
            ]
            for selector in selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    break

        if not content_elem:
            return ""

        # Nettoyer le contenu
        return self._clean_content(content_elem)

    def _clean_content(self, element: BeautifulSoup) -> str:
        """Nettoie le contenu HTML et extrait le texte."""
        # Supprimer les éléments indésirables
        for tag in element.select("script, style, nav, header, footer, aside, .share, .social, .related, .comments, .advertisement, .ad"):
            tag.decompose()

        # Extraire le texte
        text = element.get_text(separator=" ", strip=True)

        # Nettoyer les espaces multiples
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def _extract_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extrait la date de publication."""
        # Essayer le sélecteur configuré
        date_elem = soup.select_one(self.date_selector)

        if not date_elem:
            # Essayer d'autres sélecteurs courants
            selectors = [
                "time.entry-date",
                "time.published",
                "time[datetime]",
                "span.date",
                "span.post-date",
                ".meta time",
                ".entry-meta time",
            ]
            for selector in selectors:
                date_elem = soup.select_one(selector)
                if date_elem:
                    break

        if not date_elem:
            return None

        # Essayer l'attribut datetime d'abord
        date_str = date_elem.get("datetime") or date_elem.get_text(strip=True)
        return self._parse_date(date_str)

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse une chaîne de date en objet datetime.

        Args:
            date_str: Chaîne de date à parser

        Returns:
            Objet datetime ou None
        """
        if not date_str:
            return None

        # Nettoyer la chaîne
        date_str = date_str.strip()

        # Patterns français courants
        french_months = {
            "janvier": "January", "février": "February", "mars": "March",
            "avril": "April", "mai": "May", "juin": "June",
            "juillet": "July", "août": "August", "septembre": "September",
            "octobre": "October", "novembre": "November", "décembre": "December",
        }

        for fr, en in french_months.items():
            date_str = date_str.lower().replace(fr, en)

        try:
            # Utiliser dateutil pour parser intelligemment
            return date_parser.parse(date_str, dayfirst=True, fuzzy=True)
        except (ValueError, TypeError):
            pass

        # Essayer des formats spécifiques
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%d %B %Y",
            "%d %b %Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        logger.debug(f"Impossible de parser la date: {date_str}")
        return None

    def scrape_category(
        self,
        category_url: str,
        keywords_dict: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        max_articles: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Scrape tous les articles d'une catégorie.

        Args:
            category_url: URL de la page catégorie
            keywords_dict: Mots-clés pour le calcul de pertinence
            max_articles: Nombre maximum d'articles à récupérer

        Returns:
            Liste des articles avec leur contenu complet
        """
        logger.info(f"[{self.source_name}] Scraping de {category_url}")

        # Récupérer la liste des articles
        article_list = self.scrape_article_list(category_url, self.encoding)

        if not article_list:
            logger.warning(f"[{self.source_name}] Aucun article trouvé sur {category_url}")
            return []

        # Limiter le nombre d'articles
        article_list = article_list[:max_articles]

        articles = []
        for article_info in article_list:
            url = article_info.get("url")
            if not url:
                continue

            try:
                article_data = self.scrape_article(url, self.encoding, keywords_dict)
                if article_data:
                    # Fusionner les données de la liste et du contenu
                    article_data["published_date"] = (
                        article_data.get("published_date")
                        or article_info.get("published_date")
                    )
                    articles.append(article_data)
            except Exception as e:
                logger.error(f"[{self.source_name}] Erreur lors du scraping de {url}: {e}")
                continue

        logger.info(f"[{self.source_name}] {len(articles)} articles scrapés avec succès")
        return articles
