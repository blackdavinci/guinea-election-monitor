"""
Utilitaires pour les notifications (email, Telegram).
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional

import requests

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config.settings import NOTIFICATION_CONFIG

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Classe pour envoyer des notifications via Telegram."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
    ):
        self.bot_token = bot_token or NOTIFICATION_CONFIG.get("telegram_bot_token")
        self.chat_id = chat_id or NOTIFICATION_CONFIG.get("telegram_chat_id")
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    def is_configured(self) -> bool:
        """Vérifie si le notifier est configuré."""
        return bool(self.bot_token and self.chat_id)

    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Envoie un message via Telegram.

        Args:
            message: Message à envoyer
            parse_mode: Mode de parsing (HTML ou Markdown)

        Returns:
            True si le message a été envoyé avec succès
        """
        if not self.is_configured():
            logger.warning("Telegram non configuré, notification ignorée")
            return False

        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
            }
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            logger.info("Notification Telegram envoyée avec succès")
            return True
        except requests.RequestException as e:
            logger.error(f"Erreur lors de l'envoi de la notification Telegram: {e}")
            return False

    def send_article_alert(
        self,
        title: str,
        url: str,
        source: str,
        relevance_score: float,
    ) -> bool:
        """
        Envoie une alerte pour un nouvel article pertinent.

        Args:
            title: Titre de l'article
            url: URL de l'article
            source: Nom de la source
            relevance_score: Score de pertinence

        Returns:
            True si l'alerte a été envoyée
        """
        message = (
            f"🗞️ <b>Nouvel article pertinent</b>\n\n"
            f"📰 <b>{title}</b>\n"
            f"📍 Source: {source}\n"
            f"📊 Pertinence: {relevance_score:.0%}\n\n"
            f"🔗 <a href=\"{url}\">Lire l'article</a>"
        )
        return self.send_message(message)

    def send_daily_summary(
        self,
        total_articles: int,
        high_relevance_count: int,
        sources_status: dict,
    ) -> bool:
        """
        Envoie un résumé quotidien.

        Args:
            total_articles: Nombre total d'articles collectés
            high_relevance_count: Nombre d'articles à haute pertinence
            sources_status: Statut de chaque source

        Returns:
            True si le résumé a été envoyé
        """
        status_lines = []
        for source, status in sources_status.items():
            emoji = "✅" if status == "success" else "⚠️" if status == "partial" else "❌"
            status_lines.append(f"  {emoji} {source}")

        message = (
            f"📊 <b>Résumé quotidien - Veille Électorale Guinée</b>\n\n"
            f"📰 Articles collectés: {total_articles}\n"
            f"⭐ Articles pertinents: {high_relevance_count}\n\n"
            f"<b>Statut des sources:</b>\n"
            + "\n".join(status_lines)
        )
        return self.send_message(message)


class EmailNotifier:
    """Classe pour envoyer des notifications par email."""

    def __init__(
        self,
        smtp_server: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        recipient_email: Optional[str] = None,
    ):
        self.smtp_server = smtp_server or NOTIFICATION_CONFIG.get("smtp_server")
        self.smtp_port = smtp_port or NOTIFICATION_CONFIG.get("smtp_port") or 587
        self.smtp_user = smtp_user or NOTIFICATION_CONFIG.get("smtp_user")
        self.smtp_password = smtp_password or NOTIFICATION_CONFIG.get("smtp_password")
        self.recipient_email = recipient_email or NOTIFICATION_CONFIG.get("notification_email")

    def is_configured(self) -> bool:
        """Vérifie si le notifier est configuré."""
        return all([
            self.smtp_server,
            self.smtp_user,
            self.smtp_password,
            self.recipient_email,
        ])

    def send_email(
        self,
        subject: str,
        body: str,
        is_html: bool = False,
    ) -> bool:
        """
        Envoie un email.

        Args:
            subject: Sujet de l'email
            body: Corps de l'email
            is_html: Si True, le corps est en HTML

        Returns:
            True si l'email a été envoyé avec succès
        """
        if not self.is_configured():
            logger.warning("Email non configuré, notification ignorée")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.smtp_user
            msg["To"] = self.recipient_email

            content_type = "html" if is_html else "plain"
            msg.attach(MIMEText(body, content_type, "utf-8"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info("Email envoyé avec succès")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email: {e}")
            return False

    def send_daily_report(
        self,
        total_articles: int,
        articles: List[dict],
        sources_status: dict,
    ) -> bool:
        """
        Envoie un rapport quotidien par email.

        Args:
            total_articles: Nombre total d'articles
            articles: Liste des articles les plus pertinents
            sources_status: Statut de chaque source

        Returns:
            True si le rapport a été envoyé
        """
        # Construire le HTML
        articles_html = ""
        for article in articles[:10]:  # Top 10
            articles_html += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">
                    <a href="{article.get('url', '#')}" style="color: #0066cc; text-decoration: none;">
                        {article.get('title', 'Sans titre')}
                    </a>
                </td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">
                    {article.get('source', 'N/A')}
                </td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">
                    {article.get('relevance_score', 0):.0%}
                </td>
            </tr>
            """

        sources_html = ""
        for source, status in sources_status.items():
            color = "#28a745" if status == "success" else "#ffc107" if status == "partial" else "#dc3545"
            sources_html += f'<li style="color: {color};">{source}: {status}</li>'

        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #333;">📊 Rapport Quotidien - Veille Électorale Guinée</h1>

            <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="margin-top: 0;">Résumé</h3>
                <p><strong>Articles collectés:</strong> {total_articles}</p>
                <p><strong>Articles à haute pertinence:</strong> {len(articles)}</p>
            </div>

            <h2>Top Articles</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: #333; color: white;">
                        <th style="padding: 10px; text-align: left;">Titre</th>
                        <th style="padding: 10px; text-align: left;">Source</th>
                        <th style="padding: 10px; text-align: left;">Pertinence</th>
                    </tr>
                </thead>
                <tbody>
                    {articles_html}
                </tbody>
            </table>

            <h2>Statut des Sources</h2>
            <ul>
                {sources_html}
            </ul>

            <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
            <p style="color: #666; font-size: 12px;">
                Ce rapport a été généré automatiquement par le système de veille électorale.
            </p>
        </body>
        </html>
        """

        return self.send_email(
            subject=f"[Veille Guinée] Rapport - {total_articles} articles",
            body=body,
            is_html=True,
        )


class NotificationManager:
    """Gestionnaire centralisé des notifications."""

    def __init__(self):
        self.telegram = TelegramNotifier()
        self.email = EmailNotifier()

    def notify_new_article(
        self,
        title: str,
        url: str,
        source: str,
        relevance_score: float,
        min_relevance: float = 0.7,
    ) -> None:
        """
        Notifie d'un nouvel article si suffisamment pertinent.

        Args:
            title: Titre de l'article
            url: URL de l'article
            source: Nom de la source
            relevance_score: Score de pertinence
            min_relevance: Score minimum pour notifier
        """
        if relevance_score >= min_relevance:
            if self.telegram.is_configured():
                self.telegram.send_article_alert(
                    title, url, source, relevance_score
                )

    def send_daily_summary(
        self,
        total_articles: int,
        high_relevance_articles: List[dict],
        sources_status: dict,
    ) -> None:
        """
        Envoie le résumé quotidien via tous les canaux configurés.

        Args:
            total_articles: Nombre total d'articles
            high_relevance_articles: Articles à haute pertinence
            sources_status: Statut des sources
        """
        if self.telegram.is_configured():
            self.telegram.send_daily_summary(
                total_articles,
                len(high_relevance_articles),
                sources_status,
            )

        if self.email.is_configured():
            self.email.send_daily_report(
                total_articles,
                high_relevance_articles,
                sources_status,
            )
