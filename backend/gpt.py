import re
import requests
from openai import OpenAI
from bs4 import BeautifulSoup

from config.settings import settings

client = OpenAI(api_key=settings.openai_api_key)

# Регулярка для ссылок orginfo.uz/organization/...
ORGINFO_URL_RE = re.compile(
    r"https?://orginfo\.uz/organization/[0-9a-f]+/?",
    re.IGNORECASE,
)


# ---------- ORGINFO: парсер страницы организации ----------

def parse_orginfo_html(html: str) -> dict:
    """
    Достаём из HTML orginfo.uz основные поля:
    название, ИНН, статус, дата регистрации, адрес, руководитель, уставной фонд.
    """
    soup = BeautifulSoup(html, "html.parser")

    def get_label_value(label: str) -> str | None:
        # Ищем текстовый узел с подписью ("ИНН", "Статус", "Адрес", "Руководитель", "Уставной фонд" и т.д.)
        node = soup.find(string=lambda s: s and s.strip() == label)
        if not node:
            return None
        parent = node.parent
        if not parent:
            return None
        val_el = parent.find_next_sibling()
        if not val_el:
            return None
        return val_el.get_text(strip=True)

    # Заголовок страницы (обычно название компании)
    name_el = soup.find("h1")
    name = name_el.get_text(strip=True) if name_el else None

    inn = get_label_value("ИНН")
    status = get_label_value("Статус")
    reg_date = get_label_value("Дата регистрации")
    address = get_label_value("Адрес")
    director = get_label_value("Руководитель")

    # Название поля может отличаться — проверяем несколько вариантов
    charter = (
        get_label_value("Уставной фонд")
        or get_label_value("Уставный фонд")
        or get_label_value("Уставной капитал")
    )

    return {
        "name": name,
        "inn": inn,
        "status": status,
        "reg_date": reg_date,
        "address": address,
        "director": director,
        "charter": charter,
    }


def format_orginfo(info: dict) -> str:
    """Форматируем карточку компании в человеко-читаемый вид."""
    parts: list[str] = []

    name = info.get("name")
    inn = info.get("inn")
    status = info.get("status")
    reg_date = info.get("reg_date")
    address = info.get("address")
    director = info.get("director")
    charter = info.get("charter")

    if name:
        parts.append(f"🏢 {name}")
    if inn:
        parts.append(f"ИНН: {inn}")
    if status:
        parts.append(f"Статус: {status}")
    if reg_date:
        parts.append(f"Дата регистрации: {reg_date}")
    if director:
        parts.append(f"Руководитель: {director}")
    if address:
        parts.append(f"Адрес: {address}")
    if charter:
        parts.append(f"Уставной фонд: {charter}")

    if not parts:
        return "Не удалось распознать данные организации на странице orginfo.uz."

    parts.append("\nИсточник: orginfo.uz (информация не является официальной).")
    return "\n".join(parts)


def get_orginfo_from_url(url: str) -> str:
    """
    Скачиваем страницу orginfo.uz/organization/... и возвращаем
    аккуратную текстовую карточку компании.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; RobotBot/1.0; +https://robot-bot)"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        info = parse_orginfo_html(resp.text)
        return format_orginfo(info)
    except Exception as e:
        print("Orginfo error:", e)
        return "Не удалось получить или разобрать данные с orginfo.uz по указанной ссылке."


# ---------- Погода в Ташкенте ----------

def get_weather_tashkent() -> str:
    """
    Получаем текущую погоду в Ташкенте через Open-Meteo (без API ключа).
    Возвращаем короткую строку-факт для GPT.
    """
    try:
        lat = 41.31
        lon = 69.28

        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code"
            "&timezone=Asia/Tashkent"
        )

        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        current = data.get("current", {})
        temp = current.get("temperature_2m")
        code = current.get("weather_code")

        if temp is None:
            return "Нет актуальных данных о температуре."

        description = "ясно"
        if code is not None:
            if code in (0,):
                description = "ясно"
            elif code in (1, 2, 3):
                description = "переменная облачность"
            elif 51 <= code <= 67:
                description = "морось или небольшой дождь"
            elif 71 <= code <= 77:
                description = "снег"
            elif 80 <= code <= 82:
                description = "дождь"
            elif 95 <= code <= 99:
                description = "гроза"

        return f"Ташкент: сейчас около {temp:.0f} °C, {description}."
    except Exception as e:
        print("Weather error:", e)
        return "Не удалось получить погоду для Ташкента (ошибка запроса)."


# ---------- Основная функция GPT для /ask ----------

async def ask_gpt(text: str) -> str:
    """
    Общая функция для Telegram и (потом) ESP32.
    - Если в тексте есть ссылка orginfo.uz/organization/... — парсим её и возвращаем карточку.
    - Если вопрос про погоду в Ташкенте — берём реальные данные, потом GPT формулирует короткий ответ.
    - Иначе обычный короткий ответ GPT.
    """
    if not settings.openai_api_key:
        return "GPT не настроен: нет OPENAI_API_KEY"

    user_text = (text or "").strip()
    lower = user_text.lower()

    # 1) Если пользователь прислал ссылку orginfo.uz/organization/...
    url_match = ORGINFO_URL_RE.search(user_text)
    if url_match:
        url = url_match.group(0)
        return get_orginfo_from_url(url)

    # 2) Погода в Ташкенте
    is_tashkent_weather = ("погода" in lower) and ("ташкент" in lower)

    if is_tashkent_weather:
        raw_weather = get_weather_tashkent()

        system_prompt = (
            "Ты ассистент настольного робота. "
            "Тебе дали актуальные данные о погоде из внешнего источника. "
            "Используй ИХ как истину и не придумывай свои числа. "
            "Ответь ОЧЕНЬ коротко (одно предложение) на русском, "
            "обязательно укажи температуру в градусах и состояние погоды."
        )

        user_prompt = (
            f"Пользователь спросил: {user_text}\n\n"
            f"Данные внешнего источника:\n{raw_weather}\n\n"
            "Сформулируй один короткий ответ."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    else:
        # 3) Обычный режим GPT
        messages = [
            {
                "role": "system",
                "content": (
                    "Ты кратко и понятно отвечаешь для настольного робота "
                    "с маленьким дисплеем 128x64. Не пиши слишком длинные тексты."
                ),
            },
            {"role": "user", "content": user_text},
        ]

    try:
        completion = client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            max_tokens=180,
        )
        answer = completion.choices[0].message.content.strip()
        return answer[:600]
    except Exception as e:
        print("OpenAI error:", e)
        return "Ошибка при обращении к OpenAI API."


# ---------- Google поиск для ORGINFO (опционально) ----------

def google_search_orginfo(query: str, max_results: int = 5) -> list[str]:
    """
    Ищем компании на orginfo.uz через Google Custom Search (если настроены ключи).
    Возвращаем список URL вида https://orginfo.uz/organization/....
    """
    if not getattr(settings, "google_api_key", None) or not getattr(settings, "google_cse_id", None):
        return []

    try:
        params = {
            "key": settings.google_api_key,
            "cx": settings.google_cse_id,
            "q": f"site:orginfo.uz {query}",
        }
        resp = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        urls: list[str] = []
        for item in data.get("items", []):
            link = item.get("link", "")
            if "orginfo.uz/organization/" in link:
                urls.append(link)
                if len(urls) >= max_results:
                    break
        return urls
    except Exception as e:
        print("Google search error:", e)
        return []


# ---------- SerpAPI поиск для ORGINFO ----------

def serpapi_search_orginfo(query: str, max_results: int = 5) -> list[str]:
    """
    Ищем компании на orginfo.uz через SerpAPI (Google Search).
    Возвращаем список URL вида https://orginfo.uz/organization/... .
    """
    if not getattr(settings, "serpapi_key", None):
        print("SerpAPI KEY отсутствует")
        return []

    try:
        params = {
            "engine": "google",
            "q": f"site:orginfo.uz {query}",
            "api_key": settings.serpapi_key,
            "num": max_results,
        }
        resp = requests.get("https://serpapi.com/search", params=params, timeout=10)
        resp.raise_for_status()

        data = resp.json()

        urls: list[str] = []
        for item in data.get("organic_results", []):
            link = item.get("link", "")
            if "orginfo.uz/organization/" in link:
                urls.append(link)
                if len(urls) >= max_results:
                    break

        return urls

    except Exception as e:
        print("SerpAPI search error:", e)
        return []


# ---------- Обработка свободного текста для ORGINFO ----------

async def handle_orginfo_query(user_text: str) -> str:
    """
    Обработка свободного текста пользователя для режима ORGINFO:
    - Текст может содержать ИНН, название, ФИО директора и т.д.
    - GPT помогает сделать нормальный поисковый запрос.
    - СНАЧАЛА ищем через SerpAPI, при отсутствии результатов можно упасть на Google CSE.
    - По каждому URL парсим карточку.
    - Если несколько – отдаём несколько карточек подряд.
    """
    user_text = (user_text or "").strip()
    if not user_text:
        return "Отправьте текст с ИНН, названием компании или ФИО директора."

    # Если пользователь сам прислал ссылку orginfo — используем её напрямую
    url_match = ORGINFO_URL_RE.search(user_text)
    if url_match:
        url = url_match.group(0)
        return get_orginfo_from_url(url)

    # 1) Просим GPT сформировать поисковую фразу
    try:
        sys_prompt = (
            "Ты помогаешь искать юридические лица Узбекистана на сайте orginfo.uz. "
            "Пользователь прислал произвольный текст: там может быть ИНН, "
            "название компании, ФИО директора, город и т.п. "
            "Твоя задача — вернуть КРАТКУЮ поисковую фразу для поиска, "
            "которую можно подставить в Google: site:orginfo.uz <фраза>. "
            "Не объясняй, не добавляй лишнего, просто выдай одну строку поиска."
        )
        completion = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_text},
            ],
            max_tokens=40,
        )
        search_query = completion.choices[0].message.content.strip()
    except Exception as e:
        print("OpenAI error (orginfo_query build):", e)
        search_query = user_text

    # 2) Сначала пробуем найти компании через SerpAPI
    urls = serpapi_search_orginfo(search_query, max_results=5)

    # 3) Если SerpAPI ничего не нашёл, пробуем Google CSE (если настроен)
    if not urls:
        urls = google_search_orginfo(search_query, max_results=5)

    if not urls:
        return (
            "Не удалось найти организации по вашему запросу через orginfo.uz. "
            "Уточните ИНН или название компании."
        )

    # 4) Парсим каждую найденную организацию
    cards: list[str] = []
    for url in urls:
        card = get_orginfo_from_url(url)
        cards.append(card)

    return "\n\n--------------------\n\n".join(cards)
