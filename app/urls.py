from django.urls import path
from .views import *

urlpatterns = [
    path('api/tariffs/', search_tariffs, name='search_tariffs'),  # GET
    path('api/tariffs/<int:tariff_id>/', get_tariff_by_id, name='get_tariff_by_id'),  # GET
    path('api/tariffs/<int:tariff_id>/update/', update_tariff),  # PUT
    path('api/tariffs/<int:tariff_id>/update_image/', update_tariff_image),  # POST
    path('api/tariffs/<int:tariff_id>/delete/', delete_tariff),  # DELETE
    path('api/tariffs/create/', create_tariff),  # POST
    path('api/tariffs/<int:tariff_id>/add_to_forecast/', add_tariff_to_forecast),  # POST

    path('api/forecasts/', search_forecasts, name="search_forecasts"),  # GET
    path('api/forecasts/cart/', get_cart_info),  # GET
    path('api/forecasts/<int:forecast_id>/', get_forecast_by_id),  # GET
    path('api/forecasts/<int:forecast_id>/update/', update_forecast),  # PUT
    path('api/forecasts/<int:forecast_id>/update_status_user/', update_status_user),  # PUT
    path('api/forecasts/<int:forecast_id>/update_status_admin/', update_status_admin),  # PUT
    path('api/forecasts/<int:forecast_id>/delete/', delete_forecast),  # DELETE

    path('api/forecasts/<int:forecast_id>/update_tariff/<int:tariff_id>/', update_tariff_in_forecast),  # PUT
    path('api/forecasts/<int:forecast_id>/delete_tariff/<int:tariff_id>/', delete_tariff_from_forecast),  # DELETE

    path('api/users/register/', register), # POST
    path('api/users/update/', update_user), # PUT
    path("api/users/info/", user_info), # GET
    path('api/users/login/', login), # POST
    path('api/users/logout/', logout), # POST
]
