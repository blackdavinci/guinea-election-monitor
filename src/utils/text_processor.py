"""
Utilitaires pour le traitement et l'analyse de texte.
"""

import hashlib
import re
import unicodedata
from typing import List, Optional, Set


class TextProcessor:
    """Classe pour le traitement et l'analyse de texte."""

    # Mots vides français courants
    FRENCH_STOPWORDS = {
        "le", "la", "les", "un", "une", "des", "du", "de", "d", "l",
        "et", "ou", "mais", "donc", "car", "ni", "or",
        "je", "tu", "il", "elle", "nous", "vous", "ils", "elles", "on",
        "ce", "cette", "ces", "mon", "ma", "mes", "ton", "ta", "tes",
        "son", "sa", "ses", "notre", "nos", "votre", "vos", "leur", "leurs",
        "qui", "que", "quoi", "dont", "où", "quel", "quelle", "quels", "quelles",
        "à", "au", "aux", "en", "dans", "sur", "sous", "par", "pour", "avec",
        "sans", "entre", "vers", "chez", "contre", "avant", "après",
        "est", "sont", "était", "étaient", "être", "avoir", "a", "ont", "eu",
        "fait", "faire", "dit", "dire", "peut", "peuvent", "pouvoir",
        "plus", "moins", "très", "bien", "aussi", "encore", "toujours",
        "tout", "tous", "toute", "toutes", "autre", "autres",
        "même", "mêmes", "si", "ne", "pas", "n", "y",
    }

    @staticmethod
    def clean_html(html: str) -> str:
        """
        Supprime les balises HTML, scripts et styles d'un texte.

        Args:
            html: Texte HTML à nettoyer

        Returns:
            Texte nettoyé
        """
        if not html:
            return ""

        # Supprimer les scripts et styles
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)

        # Supprimer les commentaires HTML
        html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)

        # Supprimer toutes les balises HTML
        html = re.sub(r"<[^>]+>", " ", html)

        # Décoder les entités HTML courantes
        html = html.replace("&nbsp;", " ")
        html = html.replace("&amp;", "&")
        html = html.replace("&lt;", "<")
        html = html.replace("&gt;", ">")
        html = html.replace("&quot;", '"')
        html = html.replace("&#39;", "'")

        # Nettoyer les espaces multiples
        html = re.sub(r"\s+", " ", html)

        return html.strip()

    @staticmethod
    def normalize_text(text: str, remove_accents: bool = False) -> str:
        """
        Normalise un texte (espaces, casse, optionnellement accents).

        Args:
            text: Texte à normaliser
            remove_accents: Si True, supprime les accents

        Returns:
            Texte normalisé
        """
        if not text:
            return ""

        # Mettre en minuscules
        text = text.lower()

        # Supprimer les accents si demandé
        if remove_accents:
            text = unicodedata.normalize("NFKD", text)
            text = "".join(c for c in text if not unicodedata.combining(c))

        # Normaliser les espaces
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    @staticmethod
    def extract_keywords(text: str, keyword_list: List[str]) -> List[str]:
        """
        Extrait les mots-clés présents dans un texte.

        Args:
            text: Texte à analyser
            keyword_list: Liste des mots-clés à rechercher

        Returns:
            Liste des mots-clés trouvés
        """
        if not text or not keyword_list:
            return []

        text_lower = text.lower()
        found_keywords = []

        for keyword in keyword_list:
            keyword_lower = keyword.lower()
            # Recherche avec limites de mots pour éviter les faux positifs
            pattern = r"\b" + re.escape(keyword_lower) + r"\b"
            if re.search(pattern, text_lower):
                found_keywords.append(keyword)

        return found_keywords

    @staticmethod
    def generate_summary(text: str, max_length: int = 200) -> str:
        """
        Génère un résumé simple d'un texte.

        Args:
            text: Texte à résumer
            max_length: Longueur maximale du résumé

        Returns:
            Résumé du texte
        """
        if not text:
            return ""

        # Nettoyer le texte
        text = TextProcessor.clean_html(text)
        text = re.sub(r"\s+", " ", text).strip()

        if len(text) <= max_length:
            return text

        # Couper au dernier espace avant la limite
        summary = text[:max_length]
        last_space = summary.rfind(" ")

        if last_space > max_length * 0.7:  # Si l'espace n'est pas trop loin
            summary = summary[:last_space]

        return summary.strip() + "..."

    @staticmethod
    def detect_language(text: str) -> str:
        """
        Détecte la langue d'un texte (français ou anglais).

        Args:
            text: Texte à analyser

        Returns:
            Code de langue ('fr' ou 'en')
        """
        if not text:
            return "fr"  # Par défaut

        text_lower = text.lower()

        # Mots indicateurs français
        french_indicators = [
            "le ", "la ", "les ", "un ", "une ", "des ",
            "est ", "sont ", "dans ", "pour ", "avec ",
            "qui ", "que ", "ce ", "cette ", "ces ",
            " et ", " ou ", " mais ", " donc ",
            "président", "ministre", "gouvernement",
            "élection", "guinée", "guinéen",
        ]

        # Mots indicateurs anglais
        english_indicators = [
            "the ", "a ", "an ", "is ", "are ", "in ",
            "for ", "with ", "and ", "or ", "but ",
            "this ", "that ", "these ", "those ",
            "president", "minister", "government",
            "election", "guinea", "guinean",
        ]

        french_count = sum(1 for word in french_indicators if word in text_lower)
        english_count = sum(1 for word in english_indicators if word in text_lower)

        return "fr" if french_count >= english_count else "en"

    @staticmethod
    def compute_hash(text: str) -> str:
        """
        Calcule un hash SHA-256 du texte.

        Args:
            text: Texte à hasher

        Returns:
            Hash hexadécimal
        """
        if not text:
            return ""

        # Normaliser le texte avant le hash
        normalized = TextProcessor.normalize_text(text, remove_accents=True)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def extract_sentences(text: str, min_length: int = 10) -> List[str]:
        """
        Extrait les phrases d'un texte.

        Args:
            text: Texte à analyser
            min_length: Longueur minimale d'une phrase

        Returns:
            Liste des phrases
        """
        if not text:
            return []

        # Séparer par les ponctuations de fin de phrase
        sentences = re.split(r"[.!?]+", text)

        # Nettoyer et filtrer
        result = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) >= min_length:
                result.append(sentence)

        return result

    @staticmethod
    def remove_stopwords(text: str) -> str:
        """
        Supprime les mots vides français d'un texte.

        Args:
            text: Texte à traiter

        Returns:
            Texte sans mots vides
        """
        if not text:
            return ""

        words = text.lower().split()
        filtered_words = [w for w in words if w not in TextProcessor.FRENCH_STOPWORDS]
        return " ".join(filtered_words)

    @staticmethod
    def get_word_frequency(text: str, top_n: int = 20) -> List[tuple]:
        """
        Calcule la fréquence des mots dans un texte.

        Args:
            text: Texte à analyser
            top_n: Nombre de mots les plus fréquents à retourner

        Returns:
            Liste de tuples (mot, fréquence)
        """
        if not text:
            return []

        # Normaliser et supprimer les mots vides
        text = TextProcessor.normalize_text(text)
        text = TextProcessor.remove_stopwords(text)

        # Compter les mots
        words = re.findall(r"\b\w+\b", text)
        word_count = {}

        for word in words:
            if len(word) > 2:  # Ignorer les mots très courts
                word_count[word] = word_count.get(word, 0) + 1

        # Trier par fréquence
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        return sorted_words[:top_n]
