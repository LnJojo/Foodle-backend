#!/bin/sh
set -e

# Applique les migrations au démarrage du conteneur
# (pas au build : à ce stade la DB n'existe pas encore)
echo "Applying migrations..."
python manage.py migrate --noinput

# Collecte les fichiers statiques (admin Django, etc.)
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Lance Gunicorn : le serveur WSGI de production
# --workers 3 = 3 processus parallèles (règle : 2 * CPU + 1)
# exec remplace le processus shell par gunicorn (bonne pratique Docker)
echo "Starting Gunicorn..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --access-logfile - \
    --error-logfile -
