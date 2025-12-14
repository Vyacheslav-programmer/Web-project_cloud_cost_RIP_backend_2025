from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

from app.models import Tariff


@receiver([post_save, post_delete], sender=Tariff)
def clear_tariffs_cache(sender, **kwargs):
    # Удаляем все кэшированные данные по тарифам
    keys = cache.keys('tariffs_list_*')
    if keys:
        cache.delete_many(keys)