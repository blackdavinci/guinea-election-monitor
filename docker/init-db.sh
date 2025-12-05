#!/bin/bash
set -e

# Ce script crée les bases de données nécessaires
# Il est exécuté automatiquement au premier démarrage de PostgreSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Créer la base de données pour Metabase si elle n'existe pas
    SELECT 'CREATE DATABASE metabase'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'metabase')\gexec

    -- Créer des extensions utiles
    CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- Pour la recherche fuzzy
    CREATE EXTENSION IF NOT EXISTS unaccent; -- Pour ignorer les accents

    -- Message de confirmation
    DO \$\$
    BEGIN
        RAISE NOTICE 'Bases de données initialisées avec succès!';
    END \$\$;
EOSQL

echo "Initialisation de la base de données terminée."
