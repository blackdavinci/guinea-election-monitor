#!/bin/bash
#
# Configuration du cron pour le scraping automatique
#
# Ce script ajoute des tâches cron pour exécuter le scraper:
# - Tous les jours à 6h00 et 18h00
#
# Usage:
#   bash scripts/setup_cron.sh          # Ajouter le cron
#   bash scripts/setup_cron.sh --remove  # Supprimer le cron
#

set -e

# Déterminer les chemins
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python"
LOG_FILE="$PROJECT_DIR/logs/cron.log"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=============================================="
echo "Configuration du Cron - Veille Électorale"
echo "=============================================="
echo ""

# Vérifier si on veut supprimer
if [[ "$1" == "--remove" ]]; then
    echo -e "${YELLOW}Suppression des tâches cron...${NC}"

    # Supprimer les lignes contenant notre projet
    crontab -l 2>/dev/null | grep -v "$PROJECT_DIR" | crontab - 2>/dev/null || true

    echo -e "${GREEN}✅ Tâches cron supprimées${NC}"
    exit 0
fi

# Vérifier que le venv existe
if [[ ! -f "$VENV_PYTHON" ]]; then
    echo -e "${RED}❌ Environnement virtuel non trouvé!${NC}"
    echo "   Créez-le d'abord avec:"
    echo "   python -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Créer le dossier logs si nécessaire
mkdir -p "$PROJECT_DIR/logs"

# Créer le script wrapper
WRAPPER_SCRIPT="$PROJECT_DIR/scripts/cron_wrapper.sh"
cat > "$WRAPPER_SCRIPT" << EOF
#!/bin/bash
# Wrapper script pour le cron
# Généré automatiquement par setup_cron.sh

cd "$PROJECT_DIR"
source "$PROJECT_DIR/venv/bin/activate"

# Charger les variables d'environnement
if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

# Exécuter le scraper
python scripts/run_scraper.py >> "$LOG_FILE" 2>&1

# Ajouter un séparateur dans les logs
echo "========================================" >> "$LOG_FILE"
EOF

chmod +x "$WRAPPER_SCRIPT"
echo -e "${GREEN}✅ Script wrapper créé: $WRAPPER_SCRIPT${NC}"

# Définir les tâches cron
# Format: minute heure jour_du_mois mois jour_de_la_semaine commande
CRON_JOBS="
# Veille Électorale Guinée - Scraping automatique
0 6 * * * $WRAPPER_SCRIPT
0 18 * * * $WRAPPER_SCRIPT
"

# Ajouter au crontab (en préservant les tâches existantes)
echo -e "${YELLOW}Configuration du crontab...${NC}"

# Récupérer le crontab actuel (sans nos lignes)
CURRENT_CRONTAB=$(crontab -l 2>/dev/null | grep -v "$PROJECT_DIR" | grep -v "Veille Électorale" || true)

# Créer le nouveau crontab
echo "$CURRENT_CRONTAB" > /tmp/new_crontab
echo "$CRON_JOBS" >> /tmp/new_crontab

# Installer le nouveau crontab
crontab /tmp/new_crontab
rm /tmp/new_crontab

echo -e "${GREEN}✅ Crontab configuré avec succès${NC}"
echo ""
echo "Tâches planifiées:"
echo "  - Tous les jours à 06:00"
echo "  - Tous les jours à 18:00"
echo ""
echo "Pour vérifier: crontab -l"
echo "Pour supprimer: bash scripts/setup_cron.sh --remove"
echo "Logs: $LOG_FILE"
