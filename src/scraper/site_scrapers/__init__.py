"""
Scrapers spécifiques par site.
"""

from .guineenews_scraper import GuineenewsScraper
from .wordpress_scraper import WordPressScraper

__all__ = ["GuineenewsScraper", "WordPressScraper"]
