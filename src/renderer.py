"""
Функции для формирования выходной информации.
"""

from decimal import ROUND_HALF_UP, Decimal

from collectors.models import LocationInfoDTO

from datetime import datetime, timedelta, timezone
import time
from zoneinfo import ZoneInfo


class Renderer:
    """
    Генерация результата преобразования прочитанных данных.
    """

    def __init__(self, location_info: LocationInfoDTO) -> None:
        """
        Конструктор.

        :param location_info: Данные о географическом месте.
        """

        self.location_info = location_info

    async def render(self) -> tuple[str, ...]:
        """
        Форматирование прочитанных данных.

        :return: Результат форматирования
        """

        return (
            f"Страна: {self.location_info.location.name}",
            f"Столица: {self.location_info.location.capital} ({self.location_info.location.latitude}, {self.location_info.location.longitude})",
            f"Время: {await self._format_time()}",
            f"Регион: {self.location_info.location.subregion}",
            f"Площадь: {str(self.location_info.location.area) + ' км2' if self.location_info.location.area != None else '-'}",
            f"Языки: {await self._format_languages()}",
            f"Население страны: {await self._format_population()} чел.",
            f"Курсы валют: {await self._format_currency_rates()}",
            f"Погода:",
            f"\tТемпература: {self.location_info.weather.temp} °C",
            f"\tСкорость ветра: {self.location_info.weather.wind_speed} м/с",
            f"\tВидимость: {self.location_info.weather.visibility} м",
            f"\tОписание: {self.location_info.weather.description}",
        )
        
        
    async def _format_time(self) -> str:
        """
        Форматирование времени и часового пояса
        
        :return:
        """
        
        zone_location_string = self.location_info.location.region + "/" + self.location_info.location.capital
        zone_utc_string = ''
        zone_info = None
                
        try:
            zone_info = ZoneInfo(zone_location_string)
            zone_time = datetime.now(tz = zone_info)
            zone_offset = zone_info.utcoffset(datetime.now())
            
            seconds = zone_offset.days * 86400 + zone_offset.seconds
            hours = seconds // 3600
            minutes = seconds // 60 - hours * 60
            
            zone_utc_string = f'UTC{"-" if hours < 0 else "+"}{"%02d" % abs(hours)}:{"%02d" % abs(minutes)}'

        except:
            zone_utc_string = self.location_info.location.timezones[0]
            hours = int(zone_utc_string[3:6])
            minutes = int(zone_utc_string[7:9])
            zone_info = timezone(timedelta(hours=hours, minutes=minutes if hours > 0 else -minutes))
            zone_time = datetime.now(tz = zone_info)

        return f'{zone_time.strftime("%d.%m.%Y %H:%M")} ({zone_utc_string})'


    async def _format_languages(self) -> str:
        """
        Форматирование информации о языках.

        :return:
        """

        return ", ".join(
            f"{item.name} ({item.native_name})"
            for item in self.location_info.location.languages
        )

    async def _format_population(self) -> str:
        """
        Форматирование информации о населении.

        :return:
        """

        # pylint: disable=C0209
        return "{:,}".format(self.location_info.location.population).replace(",", ".")

    async def _format_currency_rates(self) -> str:
        """
        Форматирование информации о курсах валют.

        :return:
        """

        return ", ".join(
            f"{currency} = {Decimal(rates).quantize(exp=Decimal('.01'), rounding=ROUND_HALF_UP)} руб."
            for currency, rates in self.location_info.currency_rates.items()
        )
