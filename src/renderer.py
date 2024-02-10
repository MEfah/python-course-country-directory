"""
Функции для формирования выходной информации.
"""

import textwrap

from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from collectors.models import LocationInfoDTO


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
        
        tb = TableBuilder()
        await tb.add_header('СТРАНА')
        await tb.add_section(
            f"Название: {self.location_info.location.name}",
            f"Столица: {self.location_info.location.capital} ({self.location_info.location.latitude}, {self.location_info.location.longitude})",
            f"Время в столице: {await self._format_time()}",
            f"Население страны: {await self._format_population()} чел.",
            f"Регион: {self.location_info.location.subregion}",
            f"Площадь: {str(self.location_info.location.area) + ' км2' if self.location_info.location.area is not None else '-'}"
        )
        await tb.add_header('ЯЗЫКИ')
        await tb.add_section(
            *[f"{language.name} ({language.native_name})" for language in self.location_info.location.languages]
        )
        await tb.add_header('ВАЛЮТЫ')
        await tb.add_section(
            *[f"{currency} = {Decimal(rates).quantize(exp=Decimal('.01'), rounding=ROUND_HALF_UP)} руб." 
              for currency, rates in self.location_info.currency_rates.items()]
        )
        await tb.add_header('ПОГОДА')
        await tb.add_section(
            f"Температура: {self.location_info.weather.temp} °C",
            f"Скорость ветра: {self.location_info.weather.wind_speed} м/с",
            f"Видимость: {self.location_info.weather.visibility} м",
            f"Описание: {self.location_info.weather.description}"
        )

        if len(self.location_info.news) > 0:
            tb.add_header('НОВОСТИ')
            await tb.add_section(
                *[news.title for news in self.location_info.news]
            )
        
        return await tb.get_table()


    async def _format_time(self) -> str:
        """
        Форматирование времени и часового пояса

        :return:
        """

        zone_location_string = (
            self.location_info.location.region
            + "/"
            + self.location_info.location.capital
        )
        zone_utc_string = ""
        zone_info = None

        try:
            zone_info = ZoneInfo(zone_location_string)
            zone_time = datetime.now(tz=zone_info)
            zone_offset = zone_info.utcoffset(datetime.now())

            seconds = zone_offset.days * 86400 + zone_offset.seconds
            hours = seconds // 3600
            minutes = seconds // 60 - hours * 60

            zone_utc_string = f'UTC{"-" if hours < 0 else "+"}{"%02d" % abs(hours)}:{"%02d" % abs(minutes)}'

        except ZoneInfoNotFoundError:
            zone_utc_string = self.location_info.location.timezones[0]
            hours = int(zone_utc_string[3:6])
            minutes = int(zone_utc_string[7:9])
            zone_info = timezone(
                timedelta(hours=hours, minutes=minutes if hours > 0 else -minutes)
            )
            zone_time = datetime.now(tz=zone_info)

        return f'{zone_time.strftime("%d.%m.%Y %H:%M")} ({zone_utc_string})'

    async def _format_population(self) -> str:
        """
        Форматирование информации о населении.

        :return:
        """

        # pylint: disable=C0209
        return "{:,}".format(self.location_info.location.population).replace(",", ".")


class TableBuilder:
    
    """
    Построение таблицы.
    """
    
    def __init__(self, table_size: int = 120):
        """
        Конструктор
        
        :param table_size: Размер таблицы.
        """
        
        self.table_size = table_size
        self.table_lines = []
        
    
    async def add_section(self, *lines):
        """
        Добавить сегмент с текстом
        
        :param *args: Список строк сегмента
        """
        
        if len(self.table_lines) == 0:
            await self._add_border_tline()
            
        for line in lines:
            await self._add_content_tline(line)
            
        await self._add_border_tline()
        
        
    async def add_header(self, text):
        """
        Добавить центрированный заголовок сегмента
        
        :param text: Заголовок сегмента
        """
        
        if len(self.table_lines) == 0:
            await self._add_border_tline()
            
        await self._add_content_tline(text, True)
        await self._add_border_tline()
        
        
    async def _add_border_tline(self):
        """
        Добавить горизонтальную строку таблицы
        """
        self.table_lines.append('╠' + '═' * (self.table_size - 2) + '╣')
        
    
    async def _add_content_tline(self, content: str, center: bool = False):
        """
        Добавить строку, ограниченную линиями по бокам. Если строка не вмещается в таблицу,
        то она разбивается на несколько строк
        :param content: Содержимое строки
        :param center: Нужно ли размещать строку посередине
        """
        content_lines = textwrap.wrap(content, self.table_size - 4)
        
        if center:
            for line in content_lines:
                remaining_size = self.table_size - len(line) - 2
                self.table_lines.append('║' + 
                                        (' ' * (remaining_size // 2)) + 
                                        line + 
                                        (' ' * (remaining_size // 2 + remaining_size % 2)) + 
                                        '║')
        else:
            for line in content_lines:
                self.table_lines.append('║ ' 
                                        + line 
                                        + ' ' * (self.table_size - 4 - len(line))
                                        + ' ║')
        
    async def get_table(self) -> tuple[str, ...]:
        """
        Возвращает таблицу
        """
        self.table_lines[0] = self.table_lines[0].replace('╠', '╔').replace('╣', '╗')
        self.table_lines[-1] = self.table_lines[-1].replace('╠', '╚').replace('╣', '╝')
        return tuple(self.table_lines)