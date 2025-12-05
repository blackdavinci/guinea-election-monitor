"""
Scraper spécialisé pour Guineenews.org

Ce scraper:
- Parcourt toutes les catégories du site
- Récupère uniquement les articles du jour
- Extrait les tags de chaque article
- Compte les occurrences du mot "élection"
- Génère un résumé automatique
"""

import hashlib
import logging
import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from dateutil import parser as date_parser
from bs4 import BeautifulSoup

from ..base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class GuineenewsScraper(BaseScraper):
    """
    Scraper spécialisé pour le site Guineenews.org
    """

    def __init__(
        self,
        source_name: str = "Guineenews",
        base_url: str = "https://guineenews.org",
        selectors: Dict[str, str] = None,
        encoding: str = "utf-8",
        **kwargs,
    ):
        super().__init__(source_name, base_url, **kwargs)

        self.encoding = encoding

        # Sélecteurs par défaut pour Guineenews
        default_selectors = {
            "article_list": "article.listing-item",
            "title": "h2 a",
            "link": "h2 a",
            "date": "time",
            "content": "div.entry-content",
            "tags": "a[rel='tag']",
        }

        # Fusionner avec les sélecteurs passés (seulement si non-None)
        if selectors:
            for key, value in selectors.items():
                if value is not None:
                    default_selectors[key] = value

        self.selectors = default_selectors
        self.article_list_selector = self.selectors.get("article_list")
        self.title_selector = self.selectors.get("title")
        self.link_selector = self.selectors.get("link")
        self.date_selector = self.selectors.get("date")
        self.content_selector = self.selectors.get("content")
        self.tags_selector = self.selectors.get("tags")

    def parse_article_list(self, html: str) -> List[Dict[str, Any]]:
        """
        Parse la liste des articles depuis une page de catégorie.
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
        Parse le contenu complet d'un article avec extraction des tags.
        """
        soup = self.parse_html(html)

        # Extraire le titre
        title = self._extract_title(soup)

        # Extraire le contenu
        content = self._extract_content(soup)

        # Extraire la date
        published_date = self._extract_date(soup)

        # Extraire les tags
        tags = self._extract_tags(soup)

        return {
            "title": title,
            "content": content,
            "published_date": published_date,
            "tags": tags,
        }

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extrait le titre de l'article."""
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
        content_elem = None

        # Pour Guineenews: prendre le .entry-content avec le plus de contenu
        all_entry_content = soup.select('.entry-content')
        if all_entry_content:
            # Trouver celui avec le plus de texte
            best_elem = max(all_entry_content, key=lambda x: len(x.get_text(strip=True)))
            if len(best_elem.get_text(strip=True)) > 100:
                content_elem = best_elem

        if not content_elem:
            # Essayer d'autres sélecteurs
            selectors = [
                "div.post-content",
                "div.article-content",
                "div.article-body",
                "div.content-wrap",
                "article .content",
                "article",
            ]
            for selector in selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    text = content_elem.get_text(strip=True)
                    if len(text) > 100:
                        break
                    else:
                        content_elem = None

        # Si toujours rien, essayer og:description
        if not content_elem:
            og_desc = soup.find('meta', property='og:description')
            if og_desc and og_desc.get('content'):
                return og_desc.get('content')

        if not content_elem:
            return ""

        return self._clean_content(content_elem)

    def _clean_content(self, element: BeautifulSoup) -> str:
        """Nettoie le contenu HTML et extrait le texte."""
        # Faire une copie de l'élément pour ne pas modifier l'original
        from copy import copy
        element = BeautifulSoup(str(element), 'lxml')

        # Supprimer uniquement les éléments vraiment parasites
        selectors_to_remove = [
            "script", "style", "nav", "aside", "iframe", "noscript",
            ".widget", ".tagcloud", ".sidebar", ".share-buttons",
            ".advertisement", ".ad", ".related-posts",
        ]
        for selector in selectors_to_remove:
            for tag in element.select(selector):
                tag.decompose()

        # Extraire le texte
        text = element.get_text(separator=" ", strip=True)

        # Nettoyer les espaces multiples
        text = re.sub(r"\s+", " ", text)

        # Supprimer les patterns de métadonnées et widgets
        patterns_to_remove = [
            r"Followers\s*Subscribers\s*Followers?",
            r"Partager\s*(sur\s*)?(Facebook|Twitter|WhatsApp|LinkedIn|Email)?",
            r"Share\s*(on\s*)?(Facebook|Twitter|WhatsApp|LinkedIn|Email)?",
        ]
        for pattern in patterns_to_remove:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Nettoyer à nouveau les espaces
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def _extract_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extrait la date de publication."""
        date_elem = soup.select_one(self.date_selector)

        if not date_elem:
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

        date_str = date_elem.get("datetime") or date_elem.get_text(strip=True)
        return self._parse_date(date_str)

    def _extract_tags(self, soup: BeautifulSoup) -> List[str]:
        """Extrait les tags de l'article."""
        tags = []

        # Chercher les tags avec le sélecteur configuré
        tag_elements = soup.select(self.tags_selector)

        if not tag_elements:
            # Essayer d'autres sélecteurs courants
            alternative_selectors = [
                ".post-tags a",
                ".entry-tags a",
                ".tags a",
                ".tag-links a",
                "a.tag",
            ]
            for selector in alternative_selectors:
                tag_elements = soup.select(selector)
                if tag_elements:
                    break

        for tag_elem in tag_elements:
            tag_text = tag_elem.get_text(strip=True)
            if tag_text and tag_text not in tags:
                tags.append(tag_text)

        return tags

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse une chaîne de date en objet datetime."""
        if not date_str:
            return None

        date_str = date_str.strip()

        # Si c'est un format ISO (ex: 2025-12-04T14:50:03+00:00), ne pas utiliser dayfirst
        if 'T' in date_str and date_str.count('-') >= 2:
            try:
                # Format ISO - pas de dayfirst
                parsed = date_parser.parse(date_str)
                # Enlever le timezone pour comparer avec date.today()
                if parsed.tzinfo:
                    parsed = parsed.replace(tzinfo=None)
                return parsed
            except (ValueError, TypeError):
                pass

        # Patterns français courants
        french_months = {
            "janvier": "January", "février": "February", "mars": "March",
            "avril": "April", "mai": "May", "juin": "June",
            "juillet": "July", "août": "August", "septembre": "September",
            "octobre": "October", "novembre": "November", "décembre": "December",
        }

        date_str_lower = date_str.lower()
        for fr, en in french_months.items():
            date_str_lower = date_str_lower.replace(fr, en)

        try:
            return date_parser.parse(date_str_lower, dayfirst=True, fuzzy=True)
        except (ValueError, TypeError):
            pass

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

    def count_election_occurrences(self, text: str) -> int:
        """
        Compte le nombre d'occurrences des termes liés aux élections dans le texte.
        """
        if not text:
            return 0

        text_lower = text.lower()

        # Patterns pour détecter tous les termes liés aux élections
        patterns = [
            r'\bélection[s]?\b',
            r'\belection[s]?\b',  # Sans accent
            r'\bélectoral[es]?\b',
            r'\belectoral[es]?\b',
            r'\bélecteur[s]?\b',
            r'\belecteur[s]?\b',
            r'\bscrutin[s]?\b',
            r'\bvote[s]?\b',
            r'\bvoter\b',
            r'\bvotant[es]?\b',
            r'\burne[s]?\b',
            r'\bcandidat[es]?\b',
            r'\bcandidature[s]?\b',
            r'\bsuffrage[s]?\b',
            r'\bcampagne électorale\b',
            r'\bcampagne electorale\b',
            r'\bpériode électorale\b',
            r'\bperiode electorale\b',
            r'\bbureau[x]? de vote\b',
            r'\bbulletin[s]? de vote\b',
            r'\bprésidentielle[s]?\b',
            r'\bpresidentielle[s]?\b',
            r'\blégislative[s]?\b',
            r'\blegislative[s]?\b',
        ]

        count = 0
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            count += len(matches)

        return count

    def generate_summary(self, content: str, max_length: int = 500) -> str:
        """
        Génère un résumé automatique de l'article.

        Stratégie simple: extraire les premières phrases qui font sens.
        """
        if not content:
            return ""

        # Nettoyer le contenu
        content = content.strip()

        # Diviser en phrases
        sentences = re.split(r'(?<=[.!?])\s+', content)

        summary = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Ignorer les phrases trop courtes ou qui ressemblent à des métadonnées
            if len(sentence) < 20:
                continue
            if sentence.startswith(("Partager", "Suivez", "Abonnez", "Publicité", "Lire aussi")):
                continue

            if len(summary) + len(sentence) + 1 <= max_length:
                if summary:
                    summary += " "
                summary += sentence
            else:
                break

        # S'assurer qu'on a au moins quelque chose
        if len(summary) < 50 and content:
            summary = content[:max_length].rsplit(' ', 1)[0] + "..."

        return summary

    def generate_guid(self, url: str) -> str:
        """Génère un identifiant unique basé sur l'URL."""
        return hashlib.sha256(url.encode('utf-8')).hexdigest()

    def is_article_from_today(self, published_date: Optional[datetime]) -> bool:
        """Vérifie si l'article est du jour."""
        if not published_date:
            # Si pas de date, on considère que c'est potentiellement du jour
            return True

        today = date.today()
        return published_date.date() == today

    def extract_date_from_url(self, url: str) -> Optional[datetime]:
        """
        Extrait la date d'une URL WordPress typique.
        Format: /2025/12/05/titre-article/
        """
        match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
        if match:
            try:
                year = int(match.group(1))
                month = int(match.group(2))
                day = int(match.group(3))
                return datetime(year, month, day)
            except (ValueError, TypeError):
                pass
        return None

    def scrape_category(
        self,
        category_url: str,
        categorie_name: str,
        max_articles: int = 50,
        only_today: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Scrape tous les articles d'une catégorie.

        Args:
            category_url: URL de la page catégorie
            categorie_name: Nom de la catégorie
            max_articles: Nombre maximum d'articles à récupérer
            only_today: Si True, ne récupère que les articles du jour

        Returns:
            Liste des articles avec leur contenu complet
        """
        logger.info(f"[{self.source_name}] Scraping de {category_url} (catégorie: {categorie_name})")

        # Récupérer la liste des articles
        article_list = self.scrape_article_list(category_url, self.encoding)

        if not article_list:
            logger.warning(f"[{self.source_name}] Aucun article trouvé sur {category_url}")
            return []

        # Limiter le nombre d'articles
        article_list = article_list[:max_articles]

        articles = []
        articles_to_scrape = []

        # Première passe: filtrer par date (extraite de l'URL ou de la liste)
        for article_info in article_list:
            url = article_info.get("url")
            if not url:
                continue

            # Essayer d'obtenir la date depuis l'info de la liste ou depuis l'URL
            published_date = article_info.get("published_date")
            if not published_date:
                published_date = self.extract_date_from_url(url)

            # Filtrer les articles qui ne sont pas du jour
            if only_today and published_date:
                if not self.is_article_from_today(published_date):
                    logger.debug(f"Article ignoré (pas du jour, date={published_date.date()}): {url}")
                    continue

            articles_to_scrape.append({
                "url": url,
                "published_date": published_date,
            })

        logger.info(f"[{self.source_name}] {len(articles_to_scrape)} articles à scraper après filtrage date")

        # Deuxième passe: scraper les articles filtrés
        for article_info in articles_to_scrape:
            url = article_info.get("url")

            try:
                article_data = self.scrape_full_article(url, categorie_name)
                if article_data:
                    # Fusionner avec les données de la liste
                    if not article_data.get("date_publication") and article_info.get("published_date"):
                        article_data["date_publication"] = article_info["published_date"]

                    # Revérifier que c'est bien un article du jour après avoir lu le contenu
                    if only_today and article_data.get("date_publication"):
                        if not self.is_article_from_today(article_data["date_publication"]):
                            logger.debug(f"Article ignoré après lecture (pas du jour): {url}")
                            continue

                    articles.append(article_data)

            except Exception as e:
                logger.error(f"[{self.source_name}] Erreur lors du scraping de {url}: {e}")
                continue

        logger.info(f"[{self.source_name}] {len(articles)} articles du jour scrapés dans {categorie_name}")
        return articles

    def scrape_full_article(
        self,
        url: str,
        categorie: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Scrape un article complet avec toutes les métadonnées.

        Returns:
            Dictionnaire formaté selon le schéma de la base de données
        """
        self._respect_delay()

        html = self.fetch_page(url, self.encoding)
        if not html:
            return None

        article_data = self.parse_article_content(html)

        content = article_data.get("content", "")
        title = article_data.get("title", "")

        # Compter les occurrences de "élection"
        full_text = f"{title} {content}"
        compte_election = self.count_election_occurrences(full_text)

        # Générer le résumé
        resume = self.generate_summary(content)

        # Générer le GUID
        guid = self.generate_guid(url)

        return {
            "titre": title,
            "source": self.source_name,
            "lien": url,
            "date_publication": article_data.get("published_date"),
            "resume": resume,
            "tags": article_data.get("tags", []),
            "categorie": categorie,
            "compte_election": compte_election,
            "date_import": datetime.utcnow(),
            "guid": guid,
            "contenu": content,
        }

    def scrape_all_categories(
        self,
        category_configs: List[Dict[str, str]],
        max_articles_per_category: int = 50,
        only_today: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Scrape toutes les catégories configurées.

        Args:
            category_configs: Liste de dict avec 'url' et 'categorie'
            max_articles_per_category: Nombre max d'articles par catégorie
            only_today: Si True, ne récupère que les articles du jour

        Returns:
            Liste de tous les articles collectés
        """
        all_articles = []
        urls_seen = set()

        for cat_config in category_configs:
            cat_url = cat_config.get("url")
            cat_name = cat_config.get("categorie", "Non classé")

            if not cat_url:
                continue

            logger.info(f"[{self.source_name}] Traitement de la catégorie: {cat_name}")

            articles = self.scrape_category(
                category_url=cat_url,
                categorie_name=cat_name,
                max_articles=max_articles_per_category,
                only_today=only_today,
            )

            # Éviter les doublons (un article peut apparaître dans plusieurs catégories)
            for article in articles:
                if article["lien"] not in urls_seen:
                    urls_seen.add(article["lien"])
                    all_articles.append(article)
                else:
                    logger.debug(f"Article en doublon ignoré: {article['lien']}")

        logger.info(f"[{self.source_name}] Total: {len(all_articles)} articles uniques collectés")
        return all_articles
