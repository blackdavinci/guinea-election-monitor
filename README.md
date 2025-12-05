# Système de Veille Électorale - Guinée

Système automatisé de veille médiatique pour collecter, analyser et visualiser les articles sur les élections en Guinée.

## Fonctionnalités

- **Scraping automatisé** : Collecte quotidienne des articles depuis plusieurs sites d'actualités guinéens
- **Filtrage intelligent** : Calcul de pertinence basé sur des mots-clés configurables
- **Déduplication** : Détection des doublons par URL, titre et contenu
- **Stockage PostgreSQL** : Base de données robuste et performante
- **Visualisation Metabase** : Dashboards interactifs et exports (CSV, Excel, PDF)
- **Notifications** : Alertes Telegram/Email pour les articles importants (optionnel)

## Stack Technique

| Composant | Technologie |
|-----------|-------------|
| Scraping | Python (Requests + BeautifulSoup) |
| Planification | Cron (Linux/macOS) |
| Base de données | PostgreSQL 15 |
| Visualisation/BI | Metabase |
| Conteneurisation | Docker Compose |

## Structure du Projet

```
guinea-election-monitor/
├── config/
│   ├── settings.py          # Configuration générale
│   ├── sources.yaml         # Sites à scraper
│   └── keywords.yaml        # Mots-clés de filtrage
├── src/
│   ├── scraper/             # Module de scraping
│   ├── database/            # Modèles et opérations DB
│   ├── utils/               # Utilitaires
│   └── main.py              # Point d'entrée
├── scripts/
│   ├── init_db.py           # Initialisation DB
│   ├── run_scraper.py       # Exécution manuelle
│   ├── test_source.py       # Test d'une source
│   └── setup_cron.sh        # Configuration cron
├── docker/
│   └── docker-compose.yml   # PostgreSQL + Metabase
├── tests/                   # Tests unitaires
└── logs/                    # Fichiers de log
```

## Installation

### Prérequis

- Python 3.10+
- Docker et Docker Compose
- Git

### 1. Cloner le projet

```bash
git clone <repository-url>
cd guinea-election-monitor
```

### 2. Configurer l'environnement

```bash
# Copier le fichier d'exemple
cp .env .env

# Éditer avec vos valeurs
nano .env
```

Variables importantes à configurer :
```env
DB_PASSWORD=votre_mot_de_passe_securise
RELEVANCE_THRESHOLD=0.3
```

### 3. Créer l'environnement Python

```bash
# Créer le virtualenv
python -m venv venv

# Activer (Linux/macOS)
source venv/bin/activate

# Activer (Windows)
# venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt
```

### 4. Lancer les services Docker

```bash
cd docker
docker-compose up -d
cd ..
```

Cela démarre :
- PostgreSQL sur le port 5432
- Metabase sur le port 3000

### 5. Initialiser la base de données

```bash
python scripts/init_db.py
```

### 6. Tester le scraping

```bash
# Tester une source spécifique
python scripts/test_source.py "Guinée News"

# Lancer le scraping complet
python scripts/run_scraper.py
```

### 7. Configurer l'automatisation (optionnel)

```bash
# Linux/macOS : configurer le cron
bash scripts/setup_cron.sh
```

## Utilisation

### Scraping manuel

```bash
# Toutes les sources
python scripts/run_scraper.py

# Une source spécifique
python scripts/run_scraper.py "Guinée News"

# Plusieurs sources
python scripts/run_scraper.py "Guinée News" "Africaguinee"

# Lister les sources
python scripts/run_scraper.py --list
```

### Tester une source

```bash
# Test basique
python scripts/test_source.py "Guinée News"

# Mode verbose
python scripts/test_source.py "Guinée News" --verbose

# Limiter le nombre d'articles
python scripts/test_source.py "Guinée News" -n 10
```

### Accéder à Metabase

1. Ouvrir http://localhost:3000
2. Créer un compte administrateur (première connexion)
3. Ajouter la source de données :
   - Type : PostgreSQL
   - Host : `postgres` (si dans Docker) ou `localhost`
   - Port : 5432
   - Database : guinea_elections
   - User : postgres
   - Password : (votre mot de passe)

## Configuration

### Ajouter une nouvelle source

Éditer `config/sources.yaml` :

```yaml
sources:
  - name: Nouveau Site
    base_url: https://nouveausite.com
    category_urls:
      - https://nouveausite.com/politique/
    scraper_type: generic
    selectors:
      article_list: "article.post"
      title: "h2.title a"
      link: "h2.title a"
      date: "time"
      content: "div.content"
    encoding: utf-8
    is_active: true
```

Puis réinitialiser :
```bash
python scripts/init_db.py
```

### Modifier les mots-clés

Éditer `config/keywords.yaml` :

```yaml
keywords:
  election:
    weight: 1.0
    terms:
      - élection
      - scrutin
      - vote
      # Ajouter d'autres termes...
```

## Requêtes SQL utiles pour Metabase

### Articles récents à haute pertinence

```sql
SELECT
    a.title,
    a.url,
    s.name as source,
    a.published_date,
    a.relevance_score
FROM articles a
JOIN sources s ON a.source_id = s.id
WHERE a.relevance_score > 0.7
ORDER BY a.scraped_at DESC
LIMIT 50;
```

### Volume d'articles par jour

```sql
SELECT
    DATE(scraped_at) as date,
    COUNT(*) as articles
FROM articles
GROUP BY DATE(scraped_at)
ORDER BY date DESC;
```

### Top sources par nombre d'articles

```sql
SELECT
    s.name,
    COUNT(a.id) as total_articles,
    AVG(a.relevance_score) as avg_relevance
FROM sources s
LEFT JOIN articles a ON s.id = a.source_id
GROUP BY s.id, s.name
ORDER BY total_articles DESC;
```

### Mots-clés les plus fréquents

```sql
SELECT
    keyword,
    COUNT(*) as frequency
FROM articles,
     jsonb_array_elements_text(keywords_matched) as keyword
GROUP BY keyword
ORDER BY frequency DESC
LIMIT 20;
```

## Tests

```bash
# Exécuter tous les tests
pytest

# Tests avec couverture
pytest --cov=src

# Tests spécifiques
pytest tests/test_scraper.py -v
```

## Logs

Les logs sont stockés dans le dossier `logs/` :

- `scraper.log` : Logs du scraping
- `cron.log` : Logs des exécutions automatiques

## Dépannage

### Le scraping ne trouve pas d'articles

1. Vérifiez que l'URL est accessible
2. Testez les sélecteurs CSS avec l'inspecteur du navigateur
3. Le site a peut-être changé de structure

```bash
python scripts/test_source.py "Nom Source" --verbose
```

### Erreur de connexion PostgreSQL

1. Vérifiez que Docker est lancé : `docker ps`
2. Vérifiez les paramètres dans `.env`
3. Testez la connexion : `psql -h localhost -U postgres -d guinea_elections`

### Metabase ne démarre pas

```bash
# Voir les logs
docker logs guinea_elections_metabase

# Redémarrer
docker-compose restart metabase
```

## Maintenance

### Nettoyer les anciens articles

```python
from src.database.connection import session_scope
from src.database.operations import ArticleOperations

with session_scope() as session:
    # Supprimer les articles de plus de 90 jours
    count = ArticleOperations.delete_old_articles(session, days=90)
    print(f"{count} articles supprimés")
```

### Sauvegarder la base de données

```bash
docker exec guinea_elections_db pg_dump -U postgres guinea_elections > backup.sql
```

### Restaurer une sauvegarde

```bash
docker exec -i guinea_elections_db psql -U postgres guinea_elections < backup.sql
```

## Licence

Ce projet est sous licence MIT.

## Contribution

Les contributions sont les bienvenues ! Merci de :

1. Fork le projet
2. Créer une branche (`git checkout -b feature/amelioration`)
3. Commit les changements (`git commit -m 'Ajout fonctionnalité'`)
4. Push (`git push origin feature/amelioration`)
5. Ouvrir une Pull Request
