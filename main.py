import subprocess
import sys
import time


def run_backend():
    """Запуск backend-сервера в отдельном процессе."""
    print("🚀 Запуск backend сервера...")
    return subprocess.Popen([sys.executable, "-m", "backend.main"])


def run_bot():
    """Запуск Telegram-бота в отдельном процессе."""
    print("🤖 Запуск Telegram-бота...")
    return subprocess.Popen([sys.executable, "-m", "bot.bot"])


if __name__ == "__main__":
    print("=== ROBOT BOT STARTER ===")

    backend = run_backend()
    time.sleep(2)  # ждём, пока backend поднимется

    bot = run_bot()

    print("\n✔ Все сервисы запущены! (бот + backend)")
    print("❗ Чтобы остановить — закрой это окно или нажмите CTRL+C\n")

    try:
        backend.wait()
        bot.wait()
    except KeyboardInterrupt:
        print("\n⛔ Остановка сервисов...")
        backend.terminate()
        bot.terminate()
        print("Готово.")
