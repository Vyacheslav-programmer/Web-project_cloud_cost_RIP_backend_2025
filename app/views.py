import uuid
from datetime import timedelta

from django.contrib.auth import authenticate
from django.core.cache import cache
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from lab4 import settings
from .calc import calc
from .permissions import IsModerator, IsAuthenticated, IsBuyer
from .redis import session_storage
from .serializers import *
from .utils import get_session, get_draft_forecast, identity_user


@swagger_auto_schema(
    method='GET',
    manual_parameters=[
        openapi.Parameter(
            'tariff_name',
            openapi.IN_QUERY,
            type=openapi.TYPE_STRING
        )
    ],
    responses={
        status.HTTP_200_OK: openapi.Response(
            schema=TariffsSerializer(many=True),
            description=""
        )
    }
)
@api_view(["GET"])
def search_tariffs(request):
    tariff_name = request.GET.get("tariff_name", "")

    # Создаем ключ кэша на основе параметров запроса
    cache_key = f"tariffs_list_{tariff_name}"

    # Пытаемся получить данные из Redis
    cached_data = cache.get(cache_key)

    if cached_data is not None:
        # Если данные есть в кэше, возвращаем их
        return Response(cached_data)

    # Если данных нет в кэше, получаем из БД
    tariffs = Tariff.objects.filter(status=1)
    if tariff_name:
        tariffs = tariffs.filter(name__icontains=tariff_name)

    serializer = TariffsSerializer(tariffs, many=True)

    # Время жизни кэша
    cache_timeout = settings.CACHE_TTL
    # Сохраняем данные в Redis
    cache.set(cache_key, serializer.data, timeout=cache_timeout)

    return Response(serializer.data)


@swagger_auto_schema(
    method='GET',
    responses={
        status.HTTP_200_OK: openapi.Response(
            schema=TariffSerializer,
            description=""
        )
    }
)
@api_view(["GET"])
def get_tariff_by_id(request, tariff_id):
    if not Tariff.objects.filter(pk=tariff_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    tariff = Tariff.objects.get(pk=tariff_id)
    serializer = TariffSerializer(tariff)

    return Response(serializer.data)


@swagger_auto_schema(
    method='PUT',
    request_body=TariffSerializer,
    responses={
        status.HTTP_200_OK: openapi.Response(
            schema=TariffSerializer,
            description=""
        )
    }
)
@api_view(["PUT"])
@permission_classes([IsModerator])
def update_tariff(request, tariff_id):
    if not Tariff.objects.filter(pk=tariff_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    tariff = Tariff.objects.get(pk=tariff_id)

    serializer = TariffSerializer(tariff, data=request.data, partial=True)

    if serializer.is_valid(raise_exception=True):
        serializer.save()

    return Response(serializer.data)


@swagger_auto_schema(
    method='POST',
    request_body=TariffAddSerializer,
    responses={
        status.HTTP_200_OK: openapi.Response(
            schema=TariffSerializer,
            description=""
        )
    }
)
@api_view(["POST"])
@permission_classes([IsModerator])
def create_tariff(request):
    serializer = TariffAddSerializer(data=request.data, partial=False)

    serializer.is_valid(raise_exception=True)

    Tariff.objects.create(**serializer.validated_data)

    tariffs = Tariff.objects.filter(status=1)
    serializer = TariffSerializer(tariffs, many=True)

    return Response(serializer.data)


@swagger_auto_schema(
    method='DELETE',
    responses={
        status.HTTP_200_OK: openapi.Response(
            schema=TariffSerializer,
            description=""
        )
    }
)
@api_view(["DELETE"])
@permission_classes([IsModerator])
def delete_tariff(request, tariff_id):
    if not Tariff.objects.filter(pk=tariff_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    tariff = Tariff.objects.get(pk=tariff_id)
    tariff.status = 2
    tariff.save()

    tariffs = Tariff.objects.filter(status=1)
    serializer = TariffSerializer(tariffs, many=True)

    return Response(serializer.data)


@swagger_auto_schema(
    method='POST',
    responses={
        status.HTTP_200_OK: openapi.Response(
            schema=ForecastSerializer,
            description=""
        )
    }
)
@api_view(["POST"])
@permission_classes([IsBuyer])
def add_tariff_to_forecast(request, tariff_id):
    if not Tariff.objects.filter(pk=tariff_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    tariff = Tariff.objects.get(pk=tariff_id)

    draft_forecast = get_draft_forecast(request)

    if draft_forecast is None:
        draft_forecast = Forecast.objects.create()
        draft_forecast.owner = identity_user(request)
        draft_forecast.save()

    if TariffForecast.objects.filter(forecast=draft_forecast, tariff=tariff).exists():
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    item = TariffForecast.objects.create(
        forecast=draft_forecast,
        tariff=tariff
    )
    item.save()

    serializer = ForecastSerializer(draft_forecast)
    return Response(serializer.data["tariffs"])


@swagger_auto_schema(
    method='POST',
    manual_parameters=[
        openapi.Parameter('image', openapi.IN_FORM, type=openapi.TYPE_FILE),
    ],
    responses={
        status.HTTP_200_OK: openapi.Response(
            schema=TariffSerializer,
            description=""
        )
    }
)
@api_view(["POST"])
@permission_classes([IsModerator])
@parser_classes((MultiPartParser,))
def update_tariff_image(request, tariff_id):
    if not Tariff.objects.filter(pk=tariff_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    tariff = Tariff.objects.get(pk=tariff_id)

    image = request.data.get("image")
    if image is None:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    tariff.image = image
    tariff.save()

    serializer = TariffSerializer(tariff)
    return Response(serializer.data)


@swagger_auto_schema(
    method='GET',
    manual_parameters=[
        openapi.Parameter(
            'status',
            openapi.IN_QUERY,
            type=openapi.TYPE_NUMBER
        ),
        openapi.Parameter(
            'date_formation_start',
            openapi.IN_QUERY,
            type=openapi.TYPE_STRING
        ),
        openapi.Parameter(
            'date_formation_end',
            openapi.IN_QUERY,
            type=openapi.TYPE_STRING
        )
    ],
    responses={
        status.HTTP_200_OK: openapi.Response(
            schema=ForecastsSerializer(many=True),
            description=""
        )
    }
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search_forecasts(request):
    status = int(request.GET.get("status", 0))
    date_formation_start = request.GET.get("date_formation_start")
    date_formation_end = request.GET.get("date_formation_end")

    forecasts = Forecast.objects.exclude(status__in=[1, 5])

    user = identity_user(request)
    if not user.is_superuser:
        forecasts = forecasts.filter(owner=user)

    if status > 0:
        forecasts = forecasts.filter(status=status)

    if date_formation_start and parse_datetime(date_formation_start):
        forecasts = forecasts.filter(date_formation__gt=parse_datetime(date_formation_start) - timedelta(days=1))

    if date_formation_end and parse_datetime(date_formation_end):
        forecasts = forecasts.filter(date_formation__lt=parse_datetime(date_formation_end) + timedelta(days=1))

    serializer = ForecastsSerializer(forecasts, many=True)

    return Response(serializer.data)


@swagger_auto_schema(
    method='GET',
    responses={
        status.HTTP_200_OK: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "tariffs_count": openapi.Schema(type=openapi.TYPE_NUMBER),
                "draft_forecast": openapi.Schema(type=openapi.TYPE_NUMBER)
            },
            required=["tariffs_count", "draft_forecast"]
        )
    }
)
@api_view(["GET"])
@permission_classes([IsBuyer])
def get_cart_info(request):
    resp = {
        "tariffs_count": 0,
        "draft_forecast": 0
    }

    draft_forecast = get_draft_forecast(request)
    if draft_forecast:
        tariffs = TariffForecast.objects.filter(forecast=draft_forecast)
        resp = {
            "tariffs_count": tariffs.count(),
            "draft_forecast": draft_forecast.pk
        }

    return Response(resp)


@swagger_auto_schema(
    method='GET',
    responses={
        status.HTTP_200_OK: openapi.Response(
            schema=ForecastSerializer,
            description=""
        )
    }
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_forecast_by_id(request, forecast_id):
    if not Forecast.objects.filter(pk=forecast_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    forecast = Forecast.objects.get(pk=forecast_id)

    user = identity_user(request)
    if not user.is_superuser and forecast.owner != user:
        return Response(status=status.HTTP_404_NOT_FOUND)

    serializer = ForecastSerializer(forecast, many=False)
    return Response(serializer.data)


@swagger_auto_schema(
    method='PUT',
    request_body=ForecastSerializer,
    responses={
        status.HTTP_200_OK: openapi.Response(
            schema=ForecastSerializer,
            description=""
        )
    }
)
@api_view(["PUT"])
@permission_classes([IsBuyer])
def update_forecast(request, forecast_id):
    user = identity_user(request)
    if not Forecast.objects.filter(pk=forecast_id, owner=user).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    forecast = Forecast.objects.get(pk=forecast_id)
    serializer = ForecastSerializer(forecast, data=request.data, partial=True)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    serializer.save()

    return Response(serializer.data)


@swagger_auto_schema(
    method='PUT',
    responses={
        status.HTTP_200_OK: openapi.Response(
            schema=ForecastSerializer,
            description=""
        )
    }
)
@api_view(["PUT"])
@permission_classes([IsBuyer])
def update_status_user(request, forecast_id):
    user = identity_user(request)
    if not Forecast.objects.filter(pk=forecast_id, owner=user).exists():
        return Response({
            "error": "прогноз не найден"
        }, status=status.HTTP_404_NOT_FOUND)

    forecast = Forecast.objects.get(pk=forecast_id)

    if forecast.status != 1:
        return Response({
            "error": "прогноз не в том статусе"
        }, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    forecast.status = 2
    forecast.date_formation = timezone.now()
    forecast.save()

    serializer = ForecastSerializer(forecast)
    return Response(serializer.data)


@swagger_auto_schema(
    method='PUT',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'status': openapi.Schema(type=openapi.TYPE_NUMBER),
        }
    ),
    responses={
        status.HTTP_200_OK: openapi.Response(
            schema=ForecastSerializer,
            description=""
        )
    }
)
@api_view(["PUT"])
@permission_classes([IsModerator])
def update_status_admin(request, forecast_id):
    if not Forecast.objects.filter(pk=forecast_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    request_status = int(request.data["status"])
    if request_status not in [3, 4]:
        return Response({
            "error": "некорректный status"
        }, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    forecast = Forecast.objects.get(pk=forecast_id)

    if forecast.status != 2:
        return Response({
            "error": "прогноз не в том статусе"
        }, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    if request_status == 3:
        serializer = ForecastSerializer(forecast)
        forecast.price = calc(serializer.data)

    forecast.date_complete = timezone.now()
    forecast.status = request_status
    forecast.moderator = identity_user(request)
    forecast.save()

    serializer = ForecastSerializer(forecast)
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='DELETE',
    responses={
        status.HTTP_200_OK: openapi.Response(
            schema=ForecastSerializer,
            description=""
        )
    }
)
@api_view(["DELETE"])
@permission_classes([IsBuyer])
def delete_forecast(request, forecast_id):
    user = identity_user(request)
    if not Forecast.objects.filter(pk=forecast_id, owner=user).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    forecast = Forecast.objects.get(pk=forecast_id)

    if forecast.status != 1:
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    forecast.status = 5
    forecast.save()

    serializer = ForecastSerializer(forecast, many=False)

    return Response(serializer.data)


@swagger_auto_schema(
    method='DELETE',
    responses={
        status.HTTP_200_OK: openapi.Response(
            schema=TariffItemSerializer(many=True),
            description=""
        )
    }
)
@api_view(["DELETE"])
@permission_classes([IsBuyer])
def delete_tariff_from_forecast(request, forecast_id, tariff_id):
    user = identity_user(request)
    if not Forecast.objects.filter(pk=forecast_id, owner=user).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    if not TariffForecast.objects.filter(forecast_id=forecast_id, tariff_id=tariff_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    item = TariffForecast.objects.get(forecast_id=forecast_id, tariff_id=tariff_id)
    item.delete()

    items = TariffForecast.objects.filter(forecast_id=forecast_id)
    data = [TariffItemSerializer(item.tariff, context={"count": item.count}).data for item in items]

    return Response(data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='PUT',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'count': openapi.Schema(type=openapi.TYPE_NUMBER),
        },
        required=["count"],
    ),
    responses={
        status.HTTP_200_OK: openapi.Response(
            schema=TariffForecastSerializer,
            description=""
        )
    }
)
@api_view(["PUT"])
@permission_classes([IsBuyer])
def update_tariff_in_forecast(request, forecast_id, tariff_id):
    user = identity_user(request)
    if not Forecast.objects.filter(pk=forecast_id, owner=user).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    if not TariffForecast.objects.filter(tariff_id=tariff_id, forecast_id=forecast_id).exists():
        return Response(status=status.HTTP_404_NOT_FOUND)

    forecast = Forecast.objects.get(pk=forecast_id)
    if forecast.status != 1:
        return Response({
            "error": "Некорректный статус прогноза"
        }, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    item = TariffForecast.objects.get(tariff_id=tariff_id, forecast_id=forecast_id)

    serializer = TariffForecastSerializer(item, data=request.data, partial=True)

    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response(serializer.data)


@swagger_auto_schema(
    method='POST',
    request_body=UserRegisterSerializer,
    responses={
        status.HTTP_200_OK: openapi.Response(
            schema=UserSerializer,
            description=""
        )
    }
)
@api_view(["POST"])
def register(request):
    serializer = UserRegisterSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(status=status.HTTP_409_CONFLICT)

    user = serializer.save()

    session_id = str(uuid.uuid4())
    session_storage.set(session_id, user.id)

    serializer = UserSerializer(user)
    response = Response(serializer.data, status=status.HTTP_201_CREATED)
    response.set_cookie("session_id", session_id, samesite="lax")

    return response


@swagger_auto_schema(
    method='POST',
    request_body=UserLoginSerializer,
    responses={
        status.HTTP_200_OK: openapi.Response(
            schema=UserSerializer,
            description=""
        )
    }
)
@api_view(["POST"])
def login(request):
    serializer = UserLoginSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

    user = authenticate(**serializer.data)
    if user is None:
        return Response(status=status.HTTP_401_UNAUTHORIZED)

    session_id = str(uuid.uuid4())
    session_storage.set(session_id, user.id)

    serializer = UserSerializer(user)
    response = Response(serializer.data, status=status.HTTP_200_OK)
    response.set_cookie("session_id", session_id, samesite="lax")

    return response


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    session = get_session(request)
    session_storage.delete(session)

    response = Response(status=status.HTTP_200_OK)
    response.delete_cookie('session_id')

    return response


@swagger_auto_schema(
    method='GET',
    responses={
        status.HTTP_200_OK: openapi.Response(
            schema=UserSerializer,
            description=""
        )
    }
)
@api_view(["GET"])
def user_info(request):
    user = identity_user(request)
    if user is None:
        return Response(status=status.HTTP_401_UNAUTHORIZED)

    serializer = UserSerializer(user, many=False)
    return Response(serializer.data, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='PUT',
    request_body=UserUpdateProfileSerializer,
    responses={
        status.HTTP_200_OK: openapi.Response(
            schema=UserUpdateProfileSerializer,
            description=""
        )
    }
)
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_user(request):
    user = identity_user(request)

    serializer = UserUpdateProfileSerializer(user, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response(serializer.data)
