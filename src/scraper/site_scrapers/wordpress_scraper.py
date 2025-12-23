"""
Scraper WordPress générique pour les sites d'actualités guinéens.

Ce scraper supporte:
- Guinée7
- Ledjely
- Mosaique Guinée
- Média Guinée
- Guinéematin
- Et autres sites WordPress similaires

Fonctionnalités:
- Parcourt toutes les catégories du site
- Récupère uniquement les articles du jour
- Extrait les tags de chaque article
- Compte les occurrences des termes liés aux élections
- Génère un résumé automatique
"""

import hashlib
import logging
import re
import subprocess
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from dateutil import parser as date_parser
from bs4 import BeautifulSoup

try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False

from ..base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class WordPressScraper(BaseScraper):
    """
    Scraper générique pour les sites WordPress d'actualités guinéens.
    """

    # Configurations par site
    SITE_CONFIGS = {
        "guinee7": {
            "article_list": "article",
            "title": "h2.entry-title a, h3.entry-title a, h2 a, h3 a",
            "link": "h2.entry-title a, h3.entry-title a, h2 a, h3 a",
            "date": "time[datetime]",
            "content": ".entry-content",
            "tags": "a[rel='tag']",
        },
        "ledjely": {
            "article_list": "article.hentry, article.penci-post-item",
            "title": "h3 a, h2 a, .penci__post-title a",
            "link": "h3 a, h2 a, .penci__post-title a",
            "date": "time[datetime]",
            "content": ".penci-entry-content, .entry-content, .post-content",
            "tags": "a[rel='tag'], .penci-post-tags a",
        },
        "guinee360": {
            "article_list": "article, .post-item",
            "title": "h2 a, h3 a, .entry-title a",
            "link": "h2 a, h3 a, .entry-title a",
            "date": "time[datetime], .post-date",
            "content": ".entry-content, .post-content",
            "tags": "a[rel='tag']",
        },
        "mosaiqueguinee": {
            "article_list": "article.jeg_post",
            "title": "h3.jeg_post_title a, h3 a, h2 a",
            "link": "h3.jeg_post_title a, h3 a, h2 a",
            "date": "time[datetime], .jeg_meta_date",
            "content": ".jeg_inner_content .content-inner, .entry-content, .content-inner",
            "tags": "a[rel='tag'], .jeg_post_tags a",
        },
        "visionguinee": {
            "article_list": "article, .post",
            "title": "h2 a, h3 a, .entry-title a",
            "link": "h2 a, h3 a, .entry-title a",
            "date": "time[datetime]",
            "content": ".entry-content, .post-content",
            "tags": "a[rel='tag']",
        },
        "mediaguinee": {
            "article_list": ".listing-item, article",
            "title": "h2.title a, h3.title a, .title a, h2 a, h3 a",
            "link": "h2.title a, h3.title a, .title a, h2 a, h3 a",
            "date": "time[datetime]",
            "content": ".entry-content, .td-post-content, .post-content",
            "tags": "a[rel='tag']",
        },
        "guineematin": {
            "article_list": ".td-module-container, article",
            "title": ".td-module-title a, h3 a, h2 a",
            "link": ".td-module-title a, h3 a, h2 a",
            "date": "time[datetime], .td-post-date",
            "content": ".td-post-content, .entry-content",
            "tags": "a[rel='tag'], .td-tags a",
        },
        "guinee114": {
            "article_list": "article, .post",
            "title": "h2 a, h3 a, .entry-title a",
            "link": "h2 a, h3 a, .entry-title a",
            "date": "time[datetime]",
            "content": ".entry-content, .post-content",
            "tags": "a[rel='tag']",
        },
        "africaguinee": {
            "article_list": "article, .post",
            "title": "h2 a, h3 a, .entry-title a",
            "link": "h2 a, h3 a, .entry-title a",
            "date": "time[datetime], .post-date",
            "content": ".entry-content, .post-content",
            "tags": "a[rel='tag']",
        },
    }

    # Sites nécessitant cloudscraper (protection Cloudflare)
    CLOUDSCRAPER_SITES = ["africaguinee"]

    def __init__(
        self,
        source_name: str,
        base_url: str,
        site_type: str = None,
        selectors: Dict[str, str] = None,
        encoding: str = "utf-8",
        use_curl: bool = True,
        **kwargs,
    ):
        super().__init__(source_name, base_url, **kwargs)

        self.encoding = encoding
        self.use_curl = use_curl
        self.site_type = site_type

        # Utiliser cloudscraper pour les sites protégés par Cloudflare
        self.use_cloudscraper = site_type and site_type.lower() in self.CLOUDSCRAPER_SITES
        self.cloudscraper_session = None
        if self.use_cloudscraper and CLOUDSCRAPER_AVAILABLE:
            self.cloudscraper_session = cloudscraper.create_scraper(
                browser={'browser': 'chrome', 'platform': 'darwin', 'mobile': False}
            )
            logger.info(f"[{source_name}] Utilisation de cloudscraper pour contourner Cloudflare")

        # Déterminer la configuration à utiliser
        if site_type and site_type.lower() in self.SITE_CONFIGS:
            self.selectors = self.SITE_CONFIGS[site_type.lower()].copy()
        else:
            # Configuration par défaut
            self.selectors = {
                "article_list": "article",
                "title": "h2 a, h3 a, .entry-title a",
                "link": "h2 a, h3 a, .entry-title a",
                "date": "time[datetime]",
                "content": ".entry-content",
                "tags": "a[rel='tag']",
            }

        # Permettre la surcharge par des sélecteurs personnalisés (seulement si non-None)
        if selectors:
            for key, value in selectors.items():
                if value is not None:
                    self.selectors[key] = value

        self.article_list_selector = self.selectors.get("article_list", "article")
        self.title_selector = self.selectors.get("title", "h2 a")
        self.link_selector = self.selectors.get("link", "h2 a")
        self.date_selector = self.selectors.get("date", "time")
        self.content_selector = self.selectors.get("content", ".entry-content")
        self.tags_selector = self.selectors.get("tags", "a[rel='tag']")

    def fetch_with_curl(self, url: str, timeout: int = 60) -> Optional[str]:
        """
        Récupère une page en utilisant curl (plus fiable pour certains sites).
        """
        try:
            cmd = [
                'curl', '-s', '-L',
                '--max-time', str(timeout),
                '--compressed',
                '-H', 'Accept: text/html',
                '-A', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                url
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
            if result.returncode == 0 and result.stdout:
                return result.stdout
            else:
                logger.warning(f"curl a échoué pour {url}: code {result.returncode}")
                return None
        except subprocess.TimeoutExpired:
            logger.warning(f"curl timeout pour {url}")
            return None
        except Exception as e:
            logger.warning(f"Erreur curl pour {url}: {e}")
            return None

    def fetch_with_cloudscraper(self, url: str, timeout: int = 60) -> Optional[str]:
        """
        Récupère une page en utilisant cloudscraper (contourne Cloudflare).
        """
        if not self.cloudscraper_session:
            logger.warning(f"cloudscraper non disponible pour {url}")
            return None

        try:
            response = self.cloudscraper_session.get(url, timeout=timeout)
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"cloudscraper a échoué pour {url}: status {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"Erreur cloudscraper pour {url}: {e}")
            return None

    def fetch_page(self, url: str, encoding: str = "utf-8") -> Optional[str]:
        """
        Récupère une page avec fallback curl si nécessaire.
        Utilise cloudscraper pour les sites protégés par Cloudflare.
        """
        # Utiliser cloudscraper pour les sites protégés
        if self.use_cloudscraper and self.cloudscraper_session:
            html = self.fetch_with_cloudscraper(url)
            if html and len(html) > 1000:
                return html
            logger.warning(f"[{self.source_name}] cloudscraper a échoué, fallback vers curl")

        if self.use_curl:
            html = self.fetch_with_curl(url)
            if html and len(html) > 1000:
                return html

        # Fallback vers la méthode standard
        return super().fetch_page(url, encoding)

    def parse_article_list(self, html: str) -> List[Dict[str, Any]]:
        """
        Parse la liste des articles depuis une page de catégorie.
        """
        soup = self.parse_html(html)
        articles = []

        # Essayer plusieurs sélecteurs si le premier ne fonctionne pas
        article_elements = soup.select(self.article_list_selector)

        if not article_elements:
            # Fallback sur des sélecteurs communs
            fallback_selectors = ["article", ".hentry", ".td-module-container"]
            for sel in fallback_selectors:
                article_elements = soup.select(sel)
                if article_elements:
                    logger.debug(f"Utilisation du sélecteur fallback: {sel}")
                    break

        # Si toujours rien ou très peu d'éléments, essayer l'approche par titres
        if not article_elements or len(article_elements) < 3:
            logger.debug("Peu/pas de conteneurs article, recherche directe des titres")
            title_articles = self._parse_articles_from_titles(soup)
            # Utiliser l'approche par titres si elle trouve plus d'articles
            if len(title_articles) > len(article_elements):
                return title_articles

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

    def _parse_articles_from_titles(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Approche alternative: extraire les articles en cherchant directement les titres.
        Utilisé quand il n'y a pas de conteneur article standard.
        """
        articles = []
        urls_seen = set()

        # Chercher les titres avec différents sélecteurs
        title_selectors = [
            'h3.jeg_post_title a',  # JNews theme
            'h2.entry-title a',
            'h3.entry-title a',
            '.td-module-title a',  # Flavor theme
            '.post-title a',
        ]

        for sel in title_selectors:
            title_links = soup.select(sel)
            if title_links:
                logger.debug(f"Titres trouvés avec {sel}: {len(title_links)}")
                for link in title_links:
                    url = link.get('href', '')
                    if not url or url in urls_seen:
                        continue

                    url = self.make_absolute_url(url)
                    urls_seen.add(url)

                    title = link.get_text(strip=True)
                    if title and len(title) > 5:
                        articles.append({
                            "title": title,
                            "url": url,
                            "published_date": None,  # Sera extrait de la page article
                        })

                break  # Utiliser le premier sélecteur qui fonctionne

        logger.info(f"[{self.source_name}] {len(articles)} articles extraits (via titres)")
        return articles

    def _extract_article_info(self, element: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """
        Extrait les informations de base d'un article depuis un élément HTML.
        """
        # Extraire le titre et le lien
        title = None
        url = None

        # Essayer plusieurs sélecteurs pour le titre
        for sel in self.title_selector.split(", "):
            title_elem = element.select_one(sel.strip())
            if title_elem:
                title = title_elem.get_text(strip=True)
                url = title_elem.get("href", "")
                if title and url:
                    break

        if url:
            url = self.make_absolute_url(url)

        # Extraire la date
        published_date = None
        for sel in self.date_selector.split(", "):
            date_elem = element.select_one(sel.strip())
            if date_elem:
                date_str = date_elem.get("datetime") or date_elem.get_text(strip=True)
                if date_str:
                    published_date = self._parse_date(date_str)
                    break

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
            "h1.penci__post-title",
            "h1.jeg_post_title",
            "h1.td-post-title",
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

        # Fallback: og:title
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title.get('content')

        return ""

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extrait le contenu de l'article."""
        content_elem = None

        # Essayer les sélecteurs configurés
        for sel in self.content_selector.split(", "):
            elements = soup.select(sel.strip())
            if elements:
                # Prendre celui avec le plus de contenu
                best_elem = max(elements, key=lambda x: len(x.get_text(strip=True)))
                if len(best_elem.get_text(strip=True)) > 100:
                    content_elem = best_elem
                    break

        if not content_elem:
            # Essayer d'autres sélecteurs courants
            fallback_selectors = [
                ".entry-content",
                ".post-content",
                ".td-post-content",
                ".penci-entry-content",
                ".jeg_inner_content",
                ".content-inner",
                "article .content",
                "article",
            ]
            for selector in fallback_selectors:
                elements = soup.select(selector)
                if elements:
                    best_elem = max(elements, key=lambda x: len(x.get_text(strip=True)))
                    text = best_elem.get_text(strip=True)
                    if len(text) > 100:
                        content_elem = best_elem
                        break

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
        # Faire une copie de l'élément
        from copy import copy
        element = BeautifulSoup(str(element), 'lxml')

        # Supprimer les éléments parasites
        selectors_to_remove = [
            "script", "style", "nav", "aside", "iframe", "noscript",
            ".widget", ".tagcloud", ".sidebar", ".share-buttons",
            ".advertisement", ".ad", ".related-posts", ".jeg_share_button",
            ".penci-social-share", ".td-post-sharing", ".jeg_sharebar",
        ]
        for selector in selectors_to_remove:
            for tag in element.select(selector):
                tag.decompose()

        # Extraire le texte
        text = element.get_text(separator=" ", strip=True)

        # Nettoyer les espaces multiples
        text = re.sub(r"\s+", " ", text)

        # Supprimer les patterns de métadonnées
        patterns_to_remove = [
            r"Followers\s*Subscribers\s*Followers?",
            r"Partager\s*(sur\s*)?(Facebook|Twitter|WhatsApp|LinkedIn|Email)?",
            r"Share\s*(on\s*)?(Facebook|Twitter|WhatsApp|LinkedIn|Email)?",
            r"Lire aussi\s*:.*?(?=\.|$)",
        ]
        for pattern in patterns_to_remove:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _extract_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extrait la date de publication."""
        # Essayer les sélecteurs configurés
        for sel in self.date_selector.split(", "):
            date_elem = soup.select_one(sel.strip())
            if date_elem:
                date_str = date_elem.get("datetime") or date_elem.get_text(strip=True)
                if date_str:
                    parsed = self._parse_date(date_str)
                    if parsed:
                        return parsed

        # Fallback: article:published_time
        meta_date = soup.find('meta', property='article:published_time')
        if meta_date and meta_date.get('content'):
            return self._parse_date(meta_date.get('content'))

        return None

    def _extract_tags(self, soup: BeautifulSoup) -> List[str]:
        """Extrait les tags de l'article."""
        tags = []

        # Essayer les sélecteurs configurés
        for sel in self.tags_selector.split(", "):
            tag_elements = soup.select(sel.strip())
            if tag_elements:
                for tag_elem in tag_elements:
                    tag_text = tag_elem.get_text(strip=True)
                    if tag_text and tag_text not in tags and len(tag_text) < 50:
                        tags.append(tag_text)
                if tags:
                    break

        return tags

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse une chaîne de date en objet datetime."""
        if not date_str:
            return None

        date_str = date_str.strip()

        # Format ISO (ex: 2025-12-04T14:50:03+00:00)
        if 'T' in date_str and date_str.count('-') >= 2:
            try:
                parsed = date_parser.parse(date_str)
                if parsed.tzinfo:
                    parsed = parsed.replace(tzinfo=None)
                return parsed
            except (ValueError, TypeError):
                pass

        # Mois français
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

        return None

    def count_election_occurrences(self, text: str) -> int:
        """Compte le nombre d'occurrences des termes liés aux élections."""
        if not text:
            return 0

        text_lower = text.lower()

        patterns = [
            r'\bélection[s]?\b',
            r'\belection[s]?\b',
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
            r'\bréférendum\b',
            r'\breferendum\b',
        ]

        count = 0
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            count += len(matches)

        return count

    def generate_summary(self, content: str, max_length: int = 500) -> str:
        """Génère un résumé automatique de l'article."""
        if not content:
            return ""

        content = content.strip()
        sentences = re.split(r'(?<=[.!?])\s+', content)

        summary = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 20:
                continue
            if sentence.startswith(("Partager", "Suivez", "Abonnez", "Publicité", "Lire aussi")):
                continue

            if len(summary) + len(sentence) + 1 <= max_length:
                if summary:
                    summary += " "
                summary += sentence
            else:
                break

        if len(summary) < 50 and content:
            summary = content[:max_length].rsplit(' ', 1)[0] + "..."

        return summary

    def generate_guid(self, url: str) -> str:
        """Génère un identifiant unique basé sur l'URL."""
        return hashlib.sha256(url.encode('utf-8')).hexdigest()

    def is_article_in_date_range(self, published_date: Optional[datetime], days_back: int = 0, only_yesterday: bool = False) -> bool:
        """
        Vérifie si l'article est dans la plage de dates acceptable.

        Args:
            published_date: Date de publication de l'article
            days_back: Nombre de jours en arrière à accepter (0 = aujourd'hui seulement)
            only_yesterday: Si True, ne capture QUE le jour précédent (ignore aujourd'hui)
        """
        if not published_date:
            return True
        from datetime import timedelta
        today = date.today()
        article_date = published_date.date()

        if only_yesterday:
            # Ne capturer QUE les articles de la veille
            yesterday = today - timedelta(days=1)
            return article_date == yesterday
        else:
            # Capturer aujourd'hui jusqu'à (aujourd'hui - days_back)
            min_date = today - timedelta(days=days_back)
            return min_date <= article_date <= today

    def extract_date_from_url(self, url: str) -> Optional[datetime]:
        """
        Extrait la date d'une URL WordPress typique.
        Format: /2025/12/05/titre-article/
        """
        # Pattern pour extraire l'année/mois/jour de l'URL
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
        days_back: int = 0,
        only_yesterday: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Scrape tous les articles d'une catégorie.

        Args:
            days_back: Nombre de jours en arrière à inclure (0 = aujourd'hui)
            only_yesterday: Si True, ne capture QUE les articles de la veille
        """
        logger.info(f"[{self.source_name}] Scraping de {category_url} (catégorie: {categorie_name})")

        html = self.fetch_page(category_url, self.encoding)
        if not html:
            logger.warning(f"[{self.source_name}] Impossible de récupérer {category_url}")
            return []

        article_list = self.parse_article_list(html)

        if not article_list:
            logger.warning(f"[{self.source_name}] Aucun article trouvé sur {category_url}")
            return []

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

            # Filtrer les articles qui ne sont pas dans la plage de dates
            if only_today and published_date:
                if not self.is_article_in_date_range(published_date, days_back, only_yesterday):
                    logger.debug(f"Article ignoré (hors plage, date={published_date.date()}): {url}")
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
                    if not article_data.get("date_publication") and article_info.get("published_date"):
                        article_data["date_publication"] = article_info["published_date"]

                    # Double vérification de la date (au cas où)
                    if only_today and article_data.get("date_publication"):
                        if not self.is_article_in_date_range(article_data["date_publication"], days_back, only_yesterday):
                            continue

                    articles.append(article_data)

            except Exception as e:
                logger.error(f"[{self.source_name}] Erreur lors du scraping de {url}: {e}")
                continue

        logger.info(f"[{self.source_name}] {len(articles)} articles récents scrapés dans {categorie_name}")
        return articles

    def scrape_full_article(
        self,
        url: str,
        categorie: str,
    ) -> Optional[Dict[str, Any]]:
        """Scrape un article complet avec toutes les métadonnées."""
        self._respect_delay()

        html = self.fetch_page(url, self.encoding)
        if not html:
            return None

        article_data = self.parse_article_content(html)

        content = article_data.get("content", "")
        title = article_data.get("title", "")

        full_text = f"{title} {content}"
        compte_election = self.count_election_occurrences(full_text)

        resume = self.generate_summary(content)
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
        days_back: int = 0,
        only_yesterday: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Scrape toutes les catégories configurées.

        Args:
            days_back: Nombre de jours en arrière à inclure (0 = aujourd'hui)
            only_yesterday: Si True, ne capture QUE les articles de la veille
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
                days_back=days_back,
                only_yesterday=only_yesterday,
            )

            for article in articles:
                if article["lien"] not in urls_seen:
                    urls_seen.add(article["lien"])
                    all_articles.append(article)
                else:
                    logger.debug(f"Article en doublon ignoré: {article['lien']}")

        logger.info(f"[{self.source_name}] Total: {len(all_articles)} articles uniques collectés")
        return all_articles
