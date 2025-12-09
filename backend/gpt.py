import requests
from openai import OpenAI

from config.settings import settings

client = OpenAI(api_key=settings.openai_api_key)


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


async def ask_gpt(text: str) -> str:
    """
    Общая функция для Telegram и (потом) ESP32.
    Если вопрос про погоду в Ташкенте — сначала берём реальные данные,
    потом даём их ChatGPT, чтобы он ОЧЕНЬ коротко ответил.
    """
    if not settings.openai_api_key:
        return "GPT не настроен: нет OPENAI_API_KEY"

    user_text = (text or "").strip()
    lower = user_text.lower()

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
