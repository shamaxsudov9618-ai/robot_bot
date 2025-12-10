import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> int:
    print(">", " ".join(cmd))
    result = subprocess.run(cmd)
    return result.returncode


def main():
    project_dir = Path(__file__).resolve().parent
    print(f"Рабочая папка: {project_dir}")
    os_cwd = str(project_dir)

    # Проверяем, есть ли изменения
    status_code = subprocess.run(
        ["git", "-C", os_cwd, "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    has_changes = bool(status_code.stdout.strip())

    if has_changes:
        # git add .
        if run(["git", "-C", os_cwd, "add", "."]) != 0:
            sys.exit(1)

        # сообщение коммита
        if len(sys.argv) > 1:
            msg = " ".join(sys.argv[1:])
        else:
            msg = "update code"

        # git commit
        commit_code = run(["git", "-C", os_cwd, "commit", "-m", msg])
        if commit_code != 0:
            print("Не удалось сделать commit.")
            sys.exit(commit_code)
    else:
        print("Нет изменений в файлах, пропускаю commit.")

    # git push во всех случаях (вдруг что-то запушили с другого места)
    push_code = run(["git", "-C", os_cwd, "push", "origin", "main"])
    if push_code != 0:
        print("Не удалось выполнить push.")
        sys.exit(push_code)

    print("Готово: код в GitHub, Render сам подхватит деплой (если подключен).")


if __name__ == "__main__":
    main()
