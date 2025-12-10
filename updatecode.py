import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> None:
    print(">", " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"Команда завершилась с ошибкой: {result.returncode}")
        sys.exit(result.returncode)


def main():
    # Директория проекта (там, где лежит этот файл)
    project_dir = Path(__file__).resolve().parent
    print(f"Рабочая папка: {project_dir}")
    os_cwd = str(project_dir)

    # git add .
    run(["git", "-C", os_cwd, "add", "."])

    # сообщение коммита
    if len(sys.argv) > 1:
        msg = " ".join(sys.argv[1:])
    else:
        msg = "update code"

    # git commit
    run(["git", "-C", os_cwd, "commit", "-m", msg])

    # git push
    run(["git", "-C", os_cwd, "push", "origin", "main"])


if __name__ == "__main__":
    main()
