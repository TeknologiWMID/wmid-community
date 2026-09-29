#!/bin/sh
set -e

echo "Menjalankan migrasi database..."
python manage.py migrate --noinput

echo "Mengumpulkan file statis..."
python manage.py collectstatic --noinput

exec "$@"
