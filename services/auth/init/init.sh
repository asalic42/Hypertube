#!/bin/bash

set -e

python manage.py migrate --noinput #applies database migrations
exec "$@"