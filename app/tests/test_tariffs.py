import pytest
from rest_framework import status
from django.urls import reverse
from app.models import Tariff


@pytest.mark.django_db(transaction=True)
class TestSearchTariffsView:

    def test_search_all_active_tariffs(self, api_client, create_tariffs):
        """Тест получения всех активных тарифов"""
        url = reverse('search_tariffs')
        response = api_client.get(url)

        assert response.status_code == 200
        assert len(response.data) == 2  # Только 2 активных тарифа

    def test_search_with_name_filter(self, api_client, create_tariffs):
        """Тест поиска с фильтром по имени"""
        url = reverse('search_tariffs')
        response = api_client.get(url, {'tariff_name': 'AWS'})

        assert response.status_code == 200
        assert len(response.data) == 1

    @pytest.mark.parametrize("search_term,expected_count", [
        ("AWS", 1),
        ("Google", 1),
        ("Azure Cloud", 0),  # Неактивный тариф
        ("", 2),  # Все активные
        ("несуществующий", 0),
    ])
    def test_various_search_terms(self, api_client, create_tariffs,
                                  search_term, expected_count):
        """Параметризованный тест различных поисковых запросов"""
        url = reverse('search_tariffs')
        response = api_client.get(url, {'tariff_name': search_term})

        assert response.status_code == 200
        assert len(response.data) == expected_count


@pytest.mark.django_db(transaction=True)
class TestGetTariffByIdView:

    def test_get_existing_tariff(self, api_client, create_tariffs):
        """Тест получения существующего тарифа по ID"""
        # Берем первый созданный тариф
        tariff = Tariff.objects.filter(status=1).first()

        url = reverse('get_tariff_by_id', args=[tariff.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == tariff.id
        assert response.data['name'] == tariff.name
        assert response.data['price'] == tariff.price
        assert response.data['ram'] == tariff.ram
        assert response.data['cpu'] == tariff.cpu
        assert response.data['ssd'] == tariff.ssd
        assert response.data['status'] == tariff.status

    def test_get_nonexistent_tariff(self, api_client):
        """Тест получения несуществующего тарифа"""
        url = reverse('get_tariff_by_id', args=[999])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_deleted_tariff(self, api_client, create_tariffs):
        """Тест получения удаленного тарифа (status=2)"""
        deleted_tariff = Tariff.objects.filter(status=2).first()

        url = reverse('get_tariff_by_id', args=[deleted_tariff.id])
        response = api_client.get(url)

        # Если endpoint возвращает удаленные тарифы
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 2

    def test_tariff_response_structure(self, api_client, create_tariffs):
        """Тест структуры ответа тарифа"""
        tariff = Tariff.objects.first()

        url = reverse('get_tariff_by_id', args=[tariff.id])
        response = api_client.get(url)

        expected_fields = ['id', 'name', 'description', 'status',
                           'price', 'ram', 'cpu', 'ssd', 'image']

        for field in expected_fields:
            assert field in response.data