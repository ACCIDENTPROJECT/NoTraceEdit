import re
import json
import os
import time
from typing import Dict, Tuple, Optional, Any, Union
from dataclasses import dataclass

import pyperclip
import requests


@dataclass
class FetchData:
    """Класс для хранения данных fetch-запроса."""
    url: str
    headers: Dict[str, str]
    body: Dict[str, Any]
    original_nonce: str
    original_content: str


class MessageEditor:
    """Класс для редактирования сообщений Discord."""
    
    def __init__(self):
        self.fetch_data: Optional[FetchData] = None
        self.new_content: str = ""
        self.new_nonce: str = ""
    
    @staticmethod
    def clear_console() -> None:
        """Очищает консоль в зависимости от операционной системы."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    @staticmethod
    def get_clipboard_content() -> str:
        """Получает содержимое буфера обмена."""
        return pyperclip.paste()
    
    def extract_fetch_data(self, fetch_text: str) -> Optional[FetchData]:
        """
        Извлекает данные из fetch-запроса.
        
        Args:
            fetch_text: Текст с fetch-запросом из буфера обмена
            
        Returns:
            Объект FetchData с извлеченными данными или None в случае ошибки
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
            
            return FetchData(
                url=url,
                headers=headers,
                body=body,
                original_nonce=body["nonce"],
                original_content=body.get("content", "")
            )
        except Exception as e:
            print(f"❌ Ошибка при извлечении данных: {e}")
            return None
    
    def edit_message_without_mark(self) -> Tuple[str, Dict[str, Any]]:
        """
        Создает запрос для редактирования сообщения без пометки.
        
        Returns:
            Кортеж (fetch_request, request_data):
            - fetch_request: готовый fetch-запрос для вставки в консоль браузера
            - request_data: данные для прямого запроса через библиотеку requests
        """
        if not self.fetch_data:
            raise ValueError("Fetch data not initialized")
        
        # Создаем новое тело запроса с обновленными данными
        new_body = self.fetch_data.body.copy()
        new_body["content"] = self.new_content
        new_body["nonce"] = self.new_nonce
        
        # Подготавливаем данные для запроса
        body_json = json.dumps(new_body)
        body_escaped = body_json.replace('"', '\\"')
        headers_json = json.dumps(self.fetch_data.headers, indent=2)
        url = self.fetch_data.url
        referrer = self.fetch_data.headers.get('referer', 'https://discord.com/channels/@me')
        
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
            "headers": self.fetch_data.headers,
            "json": new_body
        }
        
        return fetch_request, request_data
    
    @staticmethod
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
                timeout=10
            )
            
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, f"Код ответа: {response.status_code}, Сообщение: {response.text}"
        
        except requests.RequestException as e:
            return False, f"Ошибка сети при отправке запроса: {str(e)}"
        except Exception as e:
            return False, f"Непредвиденная ошибка: {str(e)}"
    
    def show_welcome_message(self) -> None:
        """Отображает приветственное сообщение и инструкции."""
        self.clear_console()
        print("NoTraceEdit v1.0.0 - Редактирование сообщений Discord без следа")
        print("=" * 60)
        print("Инструкция:")
        print("1. Откройте DevTools (ctrl + shift + i) в Discord'e имея Vencord/BetterDiscord или в браузере.")
        print("2. Найдите запрос к messages при отправке сообщения")
        print("3. Скопируйте fetch-запрос в буфер обмена (правой кнопкой -> Copy as fetch)")
        print("=" * 60)
    
    def get_fetch_request(self) -> bool:
        """
        Получает и обрабатывает fetch-запрос из буфера обмена.
        
        Returns:
            bool: True если запрос успешно получен, False в случае ошибки
        """
        input("Когда fetch-запрос скопирован в буфер обмена, нажмите Enter... ")
        
        # Получаем данные из буфера обмена
        clipboard_content = self.get_clipboard_content()
        
        # Проверяем данные из буфера обмена и даем пользователю несколько попыток
        attempts = 0
        max_attempts = 3
        
        while not clipboard_content.strip().startswith("fetch(") and attempts < max_attempts:
            attempts += 1
            print("❌ В буфере обмена не найден fetch-запрос!")
            print(f"Попытка {attempts}/{max_attempts}. Скопируйте запрос из DevTools и повторите.")
            input("Нажмите Enter, когда fetch-запрос будет скопирован... ")
            clipboard_content = self.get_clipboard_content()
        
        if not clipboard_content.strip().startswith("fetch("):
            print("❌ В буфере обмена не найден fetch-запрос после нескольких попыток.")
            print("Убедитесь, что вы копируете правильный запрос. Программа завершает работу.")
            return False
        
        # Извлекаем данные из fetch-запроса
        self.fetch_data = self.extract_fetch_data(clipboard_content)
        
        if not self.fetch_data:
            print("❌ Не удалось разобрать fetch-запрос из буфера обмена!")
            print("Убедитесь, что запрос скопирован полностью и в правильном формате.")
            return False
        
        # Выводим информацию о полученном запросе
        print(f"✅ Fetch-запрос успешно прочитан!")
        print(f"URL: {self.fetch_data.url}")
        print(f"Текущий текст: {self.fetch_data.original_content}")
        print(f"Текущий ID: {self.fetch_data.original_nonce}")
        print("=" * 60)
        
        return True
    
    def get_new_content_and_nonce(self) -> bool:
        """
        Запрашивает у пользователя новый текст и nonce.
        
        Returns:
            bool: True если данные успешно получены, False в случае ошибки
        """
        # Запрашиваем новый текст
        print("Введите новый текст сообщения (поддерживаются кавычки, слэши и переносы строк):")
        self.new_content = input("> ")
        
        # Показываем предпросмотр текста
        print(f"\nПредпросмотр текста: \"{self.new_content}\"")
        
        # Запрашиваем nonce/ID сообщения
        print("\n!!! ВАЖНО !!!")
        print("Для успешного редактирования без пометки ОБЯЗАТЕЛЬНО нужно скопировать ТОЧНЫЙ ID сообщения.")
        print("Правый клик по сообщению -> Copy ID")
        print("Без правильного ID сообщение НЕ БУДЕТ отредактировано, а будет отправлено как новое!")
        self.new_nonce = input("Введите ID сообщения: ")
        
        if not self.new_nonce:
            print("❌ ОШИБКА: ID сообщения не может быть пустым!")
            print("Редактирование невозможно без точного ID сообщения.")
            return False
        
        return True
    
    def process_user_choice(self, fetch_request: str, request_data: Dict[str, Any]) -> bool:
        """
        Обрабатывает выбор пользователя по способу отправки запроса.
        
        Args:
            fetch_request: Подготовленный fetch-запрос для вставки в консоль
            request_data: Данные для прямого запроса через requests
            
        Returns:
            bool: True если пользователь хочет продолжить работу, False для завершения
        """
        print("\nВыберите метод отправки сообщения:")
        print("1. Отправить запрос напрямую из скрипта (рекомендуется)")
        print("2. Только скопировать fetch-запрос в буфер обмена")
        print("3. Выйти без отправки")
        choice = input("> ")
        
        if choice == "1":
            return self.handle_direct_request(request_data)
        
        elif choice == "2":
            print("✅ Fetch-запрос скопирован в буфер обмена!")
            print("Вы можете вставить его в консоль DevTools (F12) на странице Discord.")
            
            restart_choice = input("\nПродолжить работу с другим сообщением? (да/нет): ")
            return restart_choice.lower() in ["да", "д", "yes", "y", "1"]
        
        elif choice == "3":
            print("Выход без отправки. Программа завершена!")
            return False
        
        else:
            print("Некорректный выбор.")
            restart_choice = input("\nПродолжить работу с другим сообщением? (да/нет): ")
            return restart_choice.lower() in ["да", "д", "yes", "y", "1"]
    
    def handle_direct_request(self, request_data: Dict[str, Any]) -> bool:
        """
        Обрабатывает прямую отправку запроса через requests.
        
        Args:
            request_data: Данные для запроса
            
        Returns:
            bool: True если пользователь хочет продолжить работу, False для завершения
        """
        print("Отправка запроса напрямую...")
        success, response = self.send_request_directly(request_data)
        
        if success:
            print("✅ Сообщение успешно отправлено!")
            message_id = response.get("id", "неизвестно")
            channel_id = request_data["url"].split("/")[-2]
            print(f"ID сообщения: {message_id}")
            print(f"Ссылка на сообщение: https://discord.com/channels/@me/{channel_id}/{message_id}")
            
            print("\nХотите редактировать следующее сообщение?")
            print("1. Да, продолжить")
            print("2. Нет, выйти")
            next_choice = input("> ")
            
            return next_choice == "1"
        else:
            print(f"❌ Ошибка при отправке запроса: {response}")
            print("Вы всё ещё можете использовать скопированный fetch-запрос в консоли браузера.")
            
            retry_choice = input("\nХотите попробовать снова с другим сообщением? (да/нет): ")
            return retry_choice.lower() in ["да", "д", "yes", "y", "1"]
    
    def process_message(self) -> bool:
        """
        Обрабатывает одно сообщение - от получения fetch-запроса до выбора пользователя.
        
        Returns:
            bool: True если пользователь хочет продолжить работу, False для завершения
        """
        # Получаем данные из fetch-запроса
        if not self.get_fetch_request():
            retry_choice = input("\nХотите попробовать снова? (да/нет): ")
            return retry_choice.lower() in ["да", "д", "yes", "y", "1"]
        
        # Получаем новый текст и nonce
        if not self.get_new_content_and_nonce():
            retry_choice = input("\nХотите попробовать снова? (да/нет): ")
            return retry_choice.lower() in ["да", "д", "yes", "y", "1"]
        
        # Формируем новый запрос
        fetch_request, request_data = self.edit_message_without_mark()
        
        # Копируем fetch-запрос в буфер обмена
        pyperclip.copy(fetch_request)
        
        print("=" * 60)
        print("✅ Новый fetch-запрос скопирован в буфер обмена!")
        
        return self.process_user_choice(fetch_request, request_data)


def main() -> None:
    """Основная функция программы."""
    try:
        editor = MessageEditor()
        continue_running = True
        
        while continue_running:
            editor.show_welcome_message()
            continue_running = editor.process_message()
            
            if continue_running:
                print("\nПодготовка к обработке следующего сообщения...")
                time.sleep(1.5)
                editor.clear_console()
    
    except KeyboardInterrupt:
        print("\nПрограмма прервана пользователем.")
    except Exception as e:
        print(f"\nПроизошла непредвиденная ошибка: {e}")
        input("Нажмите Enter для выхода...")


if __name__ == "__main__":
    main()
