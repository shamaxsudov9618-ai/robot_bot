import os
import sys

# --- Настройка sys.path, чтобы видеть config/, backend/ при запуске uvicorn bot.bot:app ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

import requests
import telebot  # pyTelegramBotAPI
from telebot import types

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from config.settings import settings


# --- Конфиг из settings.py (важно: там должны быть поля telegram_bot_token и backend_url) ---
TELEGRAM_BOT_TOKEN = settings.telegram_bot_token
BACKEND_URL = settings.backend_url  # например: https://robot-backend-mdkp.onrender.com/ask

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN не задан в .env/переменных окружения")

# Адрес для ORGINFO-запросов (ожидается, что backend даёт /orginfo_query)
ORGINFO_URL = BACKEND_URL.replace("/ask", "/orginfo_query")

# Инициализация Telegram-бота
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode=None)

# FastAPI-приложение для Render (webhook)
app = FastAPI()

# Режимы работы по chat_id:
# "normal"  – обычные ответы GPT
# "short"   – короткие ответы GPT (1–2 предложения)
# "orginfo" – пользователь вводит текст для поиска по orginfo.uz
chat_modes: dict[int, str] = {}


def get_mode(chat_id: int) -> str:
    return chat_modes.get(chat_id, "normal")


def set_mode(chat_id: int, mode: str) -> None:
    chat_modes[chat_id] = mode


def main_keyboard() -> types.ReplyKeyboardMarkup:
    """Кнопки под строкой ввода."""
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("Короткий режим", "Обычный режим")
    kb.row("ORGINFO")
    return kb


def ask_backend(question: str) -> str:
    """Отправка запроса на backend /ask (GPT)."""
    try:
        resp = requests.post(
            BACKEND_URL,
            json={"question": question},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        answer = (data.get("answer") or "").strip() or "Сервер вернул пустой ответ."
        return answer
    except requests.exceptions.ConnectionError:
        return "Не могу подключиться к серверу робота. Проверь backend."
    except requests.exceptions.Timeout:
        return "Сервер робота слишком долго не отвечает."
    except Exception as e:
        print("Backend error:", e)
        return "Произошла ошибка при обращении к серверу робота."


def ask_orginfo(query: str) -> str:
    """Отправка запроса на backend /orginfo_query (поиск orginfo.uz)."""
    if not ORGINFO_URL or "orginfo_query" not in ORGINFO_URL:
        return "Режим ORGINFO пока не настроен на сервере."

    try:
        resp = requests.post(
            ORGINFO_URL,
            json={"query": query},
            timeout=25,
        )
        resp.raise_for_status()
        data = resp.json()
        answer = (data.get("answer") or "").strip() or "Сервер orginfo вернул пустой ответ."
        return answer
    except requests.exceptions.ConnectionError:
        return "Не могу подключиться к серверу orginfo. Проверь backend."
    except requests.exceptions.Timeout:
        return "Сервер orginfo слишком долго не отвечает."
    except Exception as e:
        print("Orginfo backend error:", e)
        return "Произошла ошибка при обращении к серверу orginfo."


# --------- Telegram handlers --------- #

@bot.message_handler(commands=["start"])
def handle_start(message: telebot.types.Message):
    chat_id = message.chat.id
    set_mode(chat_id, "normal")

    bot.send_message(
        chat_id,
        "Привет! Я мозг настольного робота 🤖\n"
        "Пиши мне вопрос — я спрошу у ChatGPT.\n\n"
        "Режимы:\n"
        " • Короткий режим – 1–2 предложения\n"
        " • Обычный режим – нормальные ответы\n"
        " • ORGINFO – поиск и парсинг компаний с orginfo.uz\n",
        reply_markup=main_keyboard(),
    )


@bot.message_handler(commands=["help"])
def handle_help(message: telebot.types.Message):
    bot.reply_to(
        message,
        "Команды:\n"
        " /start – начать\n"
        " /help – помощь\n"
        " /ping – проверить backend\n\n"
        "Кнопки:\n"
        " • Короткий режим – включить краткие ответы\n"
        " • Обычный режим – вернуться к обычным ответам\n"
        " • ORGINFO – поиск компании по ИНН/названию/ФИО и парсинг orginfo.uz\n",
    )


@bot.message_handler(commands=["ping"])
def handle_ping(message: telebot.types.Message):
    chat_id = message.chat.id
    bot.send_chat_action(chat_id, "typing")

    try:
        status_url = BACKEND_URL.replace("/ask", "/status")
        resp = requests.get(status_url, timeout=5)
        if resp.status_code == 200:
            bot.reply_to(message, "✅ Backend онлайн и готов к работе.")
        else:
            bot.reply_to(
                message,
                f"⚠️ Backend отвечает HTTP {resp.status_code}",
            )
    except Exception:
        bot.reply_to(
            message,
            "❌ Не удалось связаться с backend.",
        )


@bot.message_handler(content_types=["text"])
def handle_text(message: telebot.types.Message):
    """Обработка текста и кнопок."""
    text = (message.text or "").strip()
    chat_id = message.chat.id

    mode = get_mode(chat_id)
    bot.send_chat_action(chat_id, "typing")

    # --- Переключение режимов кнопками ---
    if text == "Короткий режим":
        set_mode(chat_id, "short")
        bot.send_message(
            chat_id,
            "Короткий режим включён 🧠📟",
            reply_markup=main_keyboard(),
        )
        return

    if text == "Обычный режим":
        set_mode(chat_id, "normal")
        bot.send_message(
            chat_id,
            "Обычный режим включён 🙂",
            reply_markup=main_keyboard(),
        )
        return

    if text == "ORGINFO":
        set_mode(chat_id, "orginfo")
        bot.send_message(
            chat_id,
            "Режим ORGINFO.\n"
            "Отправьте текст: ИНН, название компании, ФИО директора или другую информацию.\n"
            "Я постараюсь найти подходящие организации на orginfo.uz "
            "и вернуть одну или несколько карточек.",
            reply_markup=main_keyboard(),
        )
        return

    # --- Обработка по текущему режиму ---
    if mode == "orginfo":
        # Одно сообщение обрабатываем в режиме ORGINFO.
        # После этого можно сбросить режим обратно в normal
        set_mode(chat_id, "normal")
        answer = ask_orginfo(text)
        bot.send_message(chat_id, answer, reply_markup=main_keyboard())
        return

    # Обычный GPT-режим (short/normal)
    if mode == "short":
        q = f"Ответь очень коротко (1–2 предложения): {text}"
    else:
        q = text

    answer = ask_backend(q)
    bot.send_message(chat_id, answer, reply_markup=main_keyboard())


# --------- FastAPI endpoints (для Render webhook) --------- #

@app.get("/")
async def root():
    return {"status": "ok", "service": "telegram-bot"}


@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Сюда Telegram будет слать апдейты."""
    data = await request.json()
    update = telebot.types.Update.de_json(data)
    bot.process_new_updates([update])
    return JSONResponse({"ok": True})
