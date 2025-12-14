import pytest
from rest_framework.test import APIClient
from app.models import Tariff


@pytest.fixture
def api_client():
    """Создает и возвращает клиент для тестирования DRF API"""
    return APIClient()


@pytest.fixture
def create_tariffs():
    """Фикстура для создания тестовых тарифов"""
    # Создаем тарифы
    tariff1 = Tariff.objects.create(
        name="AWS EC2",
        description="Amazon Elastic Compute Cloud",
        ram=16,
        cpu=4,
        ssd=40,
        price=1000,
        status=1
    )
    tariff2 = Tariff.objects.create(
        name="Google Cloud",
        description="Google Cloud Platform",
        ram=32,
        cpu=2,
        ssd=20,
        price=3000,
        status=1
    )
    tariff3 = Tariff.objects.create(
        name="Azure Cloud",
        description="Microsoft Azure",
        ram=16,
        cpu=8,
        ssd=10,
        price=2500,
        status=2  # Удален
    )
    return [tariff1, tariff2, tariff3]