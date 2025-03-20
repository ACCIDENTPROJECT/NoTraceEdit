import re
import json
import os
import time
from typing import Dict, Tuple, Optional, Any, Union

import pyperclip
import requests


def clear_console() -> None:
    """Очищает консоль в зависимости от операционной системы."""
    os.system('cls' if os.name == 'nt' else 'clear')


def get_clipboard_content() -> str:
    """Получает содержимое буфера обмена."""
    return pyperclip.paste()


def extract_fetch_data(fetch_text: str) -> Optional[Dict[str, Any]]:
    """
    Извлекает данные из fetch-запроса.
    
    Args:
        fetch_text: Текст с fetch-запросом из буфера обмена
        
    Returns:
        Словарь с извлеченными данными или None в случае ошибки
    """
    try:
        # Извлекаем URL
        url_match = re.search(r'fetch\("(https://discord\.com/api/v\d+/channels/\d+/messages)"', fetch_text)
        if not url_match:
            return None
        url = url_match.group(1)
        
        # Извлекаем заголовки
        headers_match = re.search(r'"headers":\s*({[^}]+})', fetch_text)
        if not headers_match:
            return None
        
        headers_text = headers_match.group(1).replace("'", '"')
        headers = json.loads(headers_text)
        
        # Извлекаем тело запроса
        body_match = re.search(r'"body":\s*"({[^}]+})"', fetch_text)
        if not body_match:
            return None
        
        body_text = body_match.group(1).replace('\\"', '"')
        body = json.loads(body_text)
        
        # Проверяем наличие nonce в теле запроса
        if "nonce" not in body:
            return None
        
        return {
            "url": url,
            "headers": headers,
            "body": body,
            "original_nonce": body["nonce"],
            "original_content": body.get("content", "")
        }
    except Exception as e:
        print(f"❌ Ошибка при извлечении данных: {e}")
        return None


def edit_message_without_mark(
    fetch_data: Dict[str, Any], 
    new_content: str, 
    new_nonce: str
) -> Tuple[str, Dict[str, Any]]:
    """
    Создает запрос для редактирования сообщения без пометки.
    
    Args:
        fetch_data: Данные, извлеченные из fetch-запроса
        new_content: Новый текст сообщения
        new_nonce: Новый nonce/ID сообщения
        
    Returns:
        Кортеж (fetch_request, request_data):
        - fetch_request: готовый fetch-запрос для вставки в консоль браузера
        - request_data: данные для прямого запроса через библиотеку requests
    """
    # Создаем новое тело запроса с обновленными данными
    new_body = fetch_data["body"].copy()
    new_body["content"] = new_content
    new_body["nonce"] = new_nonce
    
    # Подготавливаем данные для запроса
    body_json = json.dumps(new_body)
    body_escaped = body_json.replace('"', '\\"')
    headers_json = json.dumps(fetch_data["headers"], indent=2)
    url = fetch_data["url"]
    referrer = fetch_data.get('referrer', 'https://discord.com/channels/@me')
    
    # Формируем fetch-запрос для браузера
    fetch_request = f'''fetch("{url}", {{
  "headers": {headers_json},
  "referrer": "{referrer}",
  "referrerPolicy": "strict-origin-when-cross-origin",
  "body": "{body_escaped}",
  "method": "POST",
  "mode": "cors",
  "credentials": "include"
}});'''
    
    # Данные для прямого запроса через requests
    request_data = {
        "url": url,
        "headers": fetch_data["headers"],
        "json": new_body
    }
    
    return fetch_request, request_data


def send_request_directly(request_data: Dict[str, Any]) -> Tuple[bool, Union[Dict[str, Any], str]]:
    """
    Отправляет запрос напрямую через библиотеку requests.
    
    Args:
        request_data: Данные для запроса
        
    Returns:
        Кортеж (success, response_data):
        - success: флаг успешности операции (True/False)
        - response_data: в случае успеха - данные ответа, иначе - текст ошибки
    """
    try:
        response = requests.post(
            request_data["url"],
            headers=request_data["headers"],
            json=request_data["json"],
            timeout=10  # Устанавливаем таймаут
        )
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"Код ответа: {response.status_code}, Сообщение: {response.text}"
    
    except requests.RequestException as e:
        return False, f"Ошибка сети при отправке запроса: {str(e)}"
    except Exception as e:
        return False, f"Непредвиденная ошибка: {str(e)}"


def show_welcome_message() -> None:
    """Отображает приветственное сообщение и инструкции."""
    clear_console()
    print("NoTraceEdit v1.0.0 - Редактирование сообщений Discord без следа")
    print("=" * 60)
    print("Инструкция:")
    print("1. Откройте DevTools (ctrl + shift + i) в Discord'e имея Vencord/BetterDiscord или в браузере.")
    print("2. Найдите запрос к messages при отправке сообщения")
    print("3. Скопируйте fetch-запрос в буфер обмена (правой кнопкой -> Copy as fetch)")
    print("=" * 60)


def get_fetch_request() -> Optional[Dict[str, Any]]:
    """
    Получает и обрабатывает fetch-запрос из буфера обмена.
    
    Returns:
        Извлеченные данные запроса или None в случае ошибки
    """
    input("Когда fetch-запрос скопирован в буфер обмена, нажмите Enter... ")
    
    # Получаем данные из буфера обмена
    clipboard_content = get_clipboard_content()
    
    # Проверяем данные из буфера обмена и даем пользователю несколько попыток
    attempts = 0
    max_attempts = 3
    
    while not clipboard_content.strip().startswith("fetch(") and attempts < max_attempts:
        attempts += 1
        print("❌ В буфере обмена не найден fetch-запрос!")
        print(f"Попытка {attempts}/{max_attempts}. Скопируйте запрос из DevTools и повторите.")
        input("Нажмите Enter, когда fetch-запрос будет скопирован... ")
        clipboard_content = get_clipboard_content()
    
    if not clipboard_content.strip().startswith("fetch("):
        print("❌ В буфере обмена не найден fetch-запрос после нескольких попыток.")
        print("Убедитесь, что вы копируете правильный запрос. Программа завершает работу.")
        return None
    
    # Извлекаем данные из fetch-запроса
    fetch_data = extract_fetch_data(clipboard_content)
    
    if not fetch_data:
        print("❌ Не удалось разобрать fetch-запрос из буфера обмена!")
        print("Убедитесь, что запрос скопирован полностью и в правильном формате.")
        return None
    
    # Выводим информацию о полученном запросе
    print(f"✅ Fetch-запрос успешно прочитан!")
    print(f"URL: {fetch_data['url']}")
    print(f"Текущий текст: {fetch_data['original_content']}")
    print(f"Текущий ID: {fetch_data['original_nonce']}")
    print("=" * 60)
    
    return fetch_data


def get_new_content_and_nonce(fetch_data: Dict[str, Any]) -> Tuple[str, str]:
    """
    Запрашивает у пользователя новый текст и nonce.
    
    Args:
        fetch_data: Данные из fetch-запроса
        
    Returns:
        Кортеж (new_content, new_nonce) с новым текстом и nonce
    """
    # Запрашиваем новый текст
    print("Введите новый текст сообщения (поддерживаются кавычки, слэши и переносы строк):")
    new_content = input("> ")
    
    # Показываем предпросмотр текста
    print(f"\nПредпросмотр текста: \"{new_content}\"")
    
    # Запрашиваем nonce/ID сообщения
    print("\n!!! ВАЖНО !!!")
    print("Для успешного редактирования без пометки ОБЯЗАТЕЛЬНО нужно скопировать ТОЧНЫЙ ID сообщения.")
    print("Правый клик по сообщению -> Copy ID")
    print("Без правильного ID сообщение НЕ БУДЕТ отредактировано, а будет отправлено как новое!")
    new_nonce = input("Введите ID сообщения: ")
    
    if not new_nonce:
        print("❌ ОШИБКА: ID сообщения не может быть пустым!")
        print("Редактирование невозможно без точного ID сообщения.")
        return "", ""
    
    return new_content, new_nonce


def process_user_choice(fetch_request: str, request_data: Dict[str, Any]) -> bool:
    """
    Обрабатывает выбор пользователя по способу отправки запроса.
    
    Args:
        fetch_request: Подготовленный fetch-запрос для вставки в консоль
        request_data: Данные для прямого запроса через requests
        
    Returns:
        Булево значение:
        - True: продолжить работу с новым сообщением
        - False: завершить программу
    """
    print("\nВыберите метод отправки сообщения:")
    print("1. Отправить запрос напрямую из скрипта (рекомендуется)")
    print("2. Только скопировать fetch-запрос в буфер обмена")
    print("3. Выйти без отправки")
    choice = input("> ")
    
    if choice == "1":
        # Отправка запроса напрямую
        return handle_direct_request(request_data)
    
    elif choice == "2":
        # Копирование запроса в буфер обмена
        print("✅ Fetch-запрос скопирован в буфер обмена!")
        print("Вы можете вставить его в консоль DevTools (F12) на странице Discord.")
        
        # Спрашиваем о продолжении работы
        restart_choice = input("\nПродолжить работу с другим сообщением? (да/нет): ")
        return restart_choice.lower() in ["да", "д", "yes", "y", "1"]
    
    elif choice == "3":
        print("Выход без отправки. Программа завершена!")
        return False
    
    else:
        print("Некорректный выбор.")
        restart_choice = input("\nПродолжить работу с другим сообщением? (да/нет): ")
        return restart_choice.lower() in ["да", "д", "yes", "y", "1"]


def handle_direct_request(request_data: Dict[str, Any]) -> bool:
    """
    Обрабатывает прямую отправку запроса через requests.
    
    Args:
        request_data: Данные для запроса
        
    Returns:
        Булево значение:
        - True: продолжить работу с новым сообщением
        - False: завершить программу
    """
    print("Отправка запроса напрямую...")
    success, response = send_request_directly(request_data)
    
    if success:
        # Успешная отправка
        print("✅ Сообщение успешно отправлено!")
        message_id = response.get("id", "неизвестно")
        channel_id = request_data["url"].split("/")[-2]
        print(f"ID сообщения: {message_id}")
        print(f"Ссылка на сообщение: https://discord.com/channels/@me/{channel_id}/{message_id}")
        
        # Спрашиваем о продолжении работы
        print("\nХотите редактировать следующее сообщение?")
        print("1. Да, продолжить")
        print("2. Нет, выйти")
        next_choice = input("> ")
        
        return next_choice == "1"
    else:
        # Ошибка при отправке
        print(f"❌ Ошибка при отправке запроса: {response}")
        print("Вы всё ещё можете использовать скопированный fetch-запрос в консоли браузера.")
        
        # Предлагаем повторить попытку
        retry_choice = input("\nХотите попробовать снова с другим сообщением? (да/нет): ")
        return retry_choice.lower() in ["да", "д", "yes", "y", "1"]


def process_message() -> bool:
    """
    Обрабатывает одно сообщение - от получения fetch-запроса до выбора пользователя.
    
    Returns:
        Булево значение:
        - True: продолжить работу с новым сообщением
        - False: завершить программу
    """
    # Получаем данные из fetch-запроса
    fetch_data = get_fetch_request()
    if not fetch_data:
        # Если произошла ошибка при получении fetch-запроса, спрашиваем о продолжении
        retry_choice = input("\nХотите попробовать снова? (да/нет): ")
        return retry_choice.lower() in ["да", "д", "yes", "y", "1"]
    
    # Получаем новый текст и nonce
    new_content, new_nonce = get_new_content_and_nonce(fetch_data)
    
    # Проверяем, был ли введен ID сообщения
    if not new_nonce:
        print("\nРедактирование отменено из-за отсутствия ID сообщения.")
        retry_choice = input("\nХотите попробовать снова? (да/нет): ")
        return retry_choice.lower() in ["да", "д", "yes", "y", "1"]
    
    # Формируем новый запрос
    fetch_request, request_data = edit_message_without_mark(fetch_data, new_content, new_nonce)
    
    # Копируем fetch-запрос в буфер обмена
    pyperclip.copy(fetch_request)
    
    print("=" * 60)
    print("✅ Новый fetch-запрос скопирован в буфер обмена!")
    
    # Обрабатываем выбор пользователя и возвращаем результат
    return process_user_choice(fetch_request, request_data)


def main() -> None:
    """Основная функция программы."""
    try:
        # Цикл обработки сообщений
        continue_running = True
        
        while continue_running:
            # Показываем приветственное сообщение
            show_welcome_message()
            
            # Обрабатываем одно сообщение и получаем решение о продолжении
            continue_running = process_message()
            
            # Если пользователь решил продолжить, делаем небольшую паузу перед следующей итерацией
            if continue_running:
                print("\nПодготовка к обработке следующего сообщения...")
                time.sleep(1.5)
                clear_console()
    
    except KeyboardInterrupt:
        print("\nПрограмма прервана пользователем.")
    except Exception as e:
        print(f"\nПроизошла непредвиденная ошибка: {e}")
        input("Нажмите Enter для выхода...")


if __name__ == "__main__":
    main()
