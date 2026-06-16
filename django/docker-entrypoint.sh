#!/bin/bash
set -e

echo "Running migrations..."
uv run manage.py migrate --noinput

echo "Setting up test data..."
uv run manage.py seed_test_data

echo "Creating test user..."
uv run manage.py shell -c "
from dst.models import User, UserRole
user, created = User.objects.get_or_create(
    email='admin@test.com',
    defaults={
        'username': 'admin@test.com',
        'name': 'Admin User',
        'is_active': True,
        'is_staff': True,
        'is_superuser': True,
    },
)
if created:
    user.set_password('password123')
    user.save()
    UserRole.objects.create(user=user, role=UserRole.ALL_ACCESS)
    print('Test user created: admin@test.com / password123')
else:
    print('Test user already exists.')
"

echo "Starting Django dev server..."
exec uv run manage.py runserver 0.0.0.0:8000
