#!/bin/sh
# Установка AI Team Kit в проект: sh install.sh /путь/к/проекту
set -e
KIT="$(cd "$(dirname "$0")" && pwd)"
[ -n "$1" ] || { echo "Использование: sh install.sh /путь/к/проекту"; exit 1; }
[ -d "$1" ] || { echo "Нет папки $1 — создайте проект и запустите снова"; exit 1; }
DST="$(cd "$1" && pwd)"
[ "$DST" != "$KIT" ] || { echo "Укажите папку своего проекта, а не папку набора"; exit 1; }

# Навыки и агенты: существующие с тем же именем не трогаем
mkdir -p "$DST/.claude/skills" "$DST/.claude/agents"
for src in "$KIT"/claude/skills/* "$KIT"/claude/agents/*; do
  kind="$(basename "$(dirname "$src")")"
  name="$(basename "$src")"
  if [ -e "$DST/.claude/$kind/$name" ]; then
    echo "есть .claude/$kind/$name — не перезаписываю"
  else
    cp -R "$src" "$DST/.claude/$kind/$name"
  fi
done

# Папки команды
for d in team prompts tools; do
  if [ -e "$DST/$d" ]; then
    echo "есть $DST/$d — не перезаписываю, скопируйте вручную"
  else
    cp -R "$KIT/$d" "$DST/$d"
  fi
done

# История разговоров и памятки — локальные, в git проекта не нужны
GI="$DST/.gitignore"
for p in "team/history/" ".env"; do
  grep -qxF "$p" "$GI" 2>/dev/null || echo "$p" >> "$GI"
done

echo
echo "Готово. Дальше:"
echo "  1. В приложении Claude (вкладка Code) откройте новую сессию в папке $DST,"
echo "     модель Opus, усилие high."
echo "  2. Отправьте в неё текст из prompts/bootstrap-general-manager.md —"
echo "     она станет General Manager и сама создаст сессии остальных ролей."
