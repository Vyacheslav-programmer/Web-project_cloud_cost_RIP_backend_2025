from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers

from .models import *


class TariffsSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=True)
    image = serializers.ImageField(required=True)
    price = serializers.IntegerField(required=True)

    class Meta:
        model = Tariff
        fields = ("id", "name", "status", "price", "ram", "cpu", "ssd", "image")


class TariffSerializer(TariffsSerializer):
    class Meta(TariffsSerializer.Meta):
        fields = "__all__"


class TariffAddSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tariff
        fields = ("name", "description", "price", "ram", "cpu", "ssd", "image")


class ForecastBaseSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=True)
    owner = serializers.StringRelatedField(read_only=True)
    moderator = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Forecast
        fields = "__all__"


class ForecastsSerializer(ForecastBaseSerializer):
    tariffs_count = serializers.SerializerMethodField()

    def get_tariffs_count(self, forecast):
        items = forecast.tariffforecast_set.all()
        return items.count()


class TariffItemSerializer(TariffSerializer):
    count = serializers.SerializerMethodField()

    @swagger_serializer_method(serializer_or_field=serializers.IntegerField(required=True))
    def get_count(self, _):
        return self.context.get("count", 0)

    class Meta:
        model = Tariff
        fields = ("id", "name", "status", "price", "ram", "cpu", "ssd", "image", "count")


class ForecastSerializer(ForecastBaseSerializer):
    tariffs = serializers.SerializerMethodField()

    @swagger_serializer_method(serializer_or_field=TariffItemSerializer(many=True))
    def get_tariffs(self, forecast):
        items = forecast.tariffforecast_set.all()
        return [TariffItemSerializer(item.tariff, context={"count": item.count}).data for item in items]


class TariffForecastSerializer(serializers.ModelSerializer):
    class Meta:
        model = TariffForecast
        fields = "__all__"


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', "is_superuser")


class UserRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'username')
        write_only_fields = ('password',)
        read_only_fields = ('id',)

    def create(self, validated_data):
        user = User.objects.create(
            email=validated_data['email'],
            username=validated_data['username']
        )

        user.set_password(validated_data['password'])
        user.save()

        return user


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)


class UserUpdateProfileSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    username = serializers.CharField(write_only=True, required=False, allow_blank=True)
    email = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password')

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)

        instance = super().update(instance, validated_data)

        if password and password.strip() and not self.instance.check_password(password):
            instance.set_password(password)
            instance.save()

        return instance
