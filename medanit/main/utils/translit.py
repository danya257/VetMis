"""
Утилита для транслитерации кириллических имен файлов в латиницу.
Предотвращает проблемы с 404 ошибками при загрузке файлов с кириллическими именами.
"""
import os
import re
from django.core.files.storage import FileSystemStorage
from django.utils.text import get_valid_filename


def translit_rus_to_lat(text):
    """
    Транслитерирует кириллический текст в латиницу.
    """
    converter = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
        'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i',
        'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
        'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
        'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch',
        'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '',
        'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D',
        'Е': 'E', 'Ё': 'Yo', 'Ж': 'Zh', 'З': 'Z', 'И': 'I',
        'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',
        'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T',
        'У': 'U', 'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch',
        'Ш': 'Sh', 'Щ': 'Sch', 'Ъ': '', 'Ы': 'Y', 'Ь': '',
        'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
    }
    
    result = ''
    for char in text:
        result += converter.get(char, char)
    
    return result


class TranslitFileSystemStorage(FileSystemStorage):
    """
    Кастомный класс хранения файлов с автоматической транслитерацией имен.
    """
    
    def get_valid_name(self, name):
        """
        Возвращает корректное имя файла с транслитерацией кириллицы.
        """
        # Разделяем имя и расширение
        base, ext = os.path.splitext(name)
        
        # Транслитерируем базовое имя
        base = translit_rus_to_lat(base)
        
        # Очищаем имя от недопустимых символов
        base = get_valid_filename(base)
        
        # Заменяем пробелы на подчеркивания
        base = re.sub(r'\s+', '_', base)
        
        # Ограничиваем длину имени (оставляем место для уникального суффикса)
        max_length = 100
        if len(base) > max_length:
            base = base[:max_length]
        
        return f"{base}{ext}"
