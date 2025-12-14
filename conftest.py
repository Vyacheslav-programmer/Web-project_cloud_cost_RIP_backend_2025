import os
import django

# Устанавливает переменную окружения для настроек Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lab4.settings')

# Инициализирует Django
django.setup()