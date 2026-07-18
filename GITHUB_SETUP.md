# Вариант 24/7 через GitHub Actions

Тот же `check.py` крутится на серверах GitHub каждые ~5 минут — работает,
даже когда твой Mac спит или выключен. Бесплатно.

> ⚠️ **Делай репозиторий ПУБЛИЧНЫМ.** У публичных репозиториев минуты Actions
> безлимитны и бесплатны. У приватных — только 2000 мин/мес, а проверка каждые
> 5 минут их превысит. Секретов в коде нет (токен и chat_id лежат в Secrets),
> поэтому публичный репозиторий безопасен.

## Что понадобится сначала
Те же токен бота и chat_id'ы, что и для локального варианта:
1. **@BotFather** → `/newbot` → получить токен.
2. Оба получателя жмут **Start** у бота.
3. Локально один раз узнать chat_id'ы:
   ```bash
   TELEGRAM_TOKEN="ТВОЙ_ТОКЕН" /Users/maksymkogua/miniconda3/bin/python3 get_chat_ids.py
   ```
   Запиши оба числа — понадобятся в шаге 3.

## Шаг 1. Создать репозиторий
1. Зайди на https://github.com → **New repository**.
2. Имя любое (например `cavozoe-monitor`), тип **Public**, → **Create**.

## Шаг 2. Залить файлы
Проще всего через веб: на странице репозитория **Add file → Upload files** и
перетащи содержимое папки `hotel_monitor`:
```
check.py
config.json
get_chat_ids.py
.gitignore
.github/workflows/monitor.yml
```
(папку `.github` тоже, с сохранением структуры) → **Commit changes**.

Или через терминал:
```bash
cd /Users/maksymkogua/Vibecoding/hotel_monitor
git init && git add . && git commit -m "cavozoe monitor"
git branch -M main
git remote add origin https://github.com/ТВОЙ_ЛОГИН/cavozoe-monitor.git
git push -u origin main
```

## Шаг 3. Добавить секреты
В репозитории: **Settings → Secrets and variables → Actions → New repository secret**.
Создай два секрета:

| Name | Value |
|------|-------|
| `TELEGRAM_TOKEN` | токен от BotFather, напр. `123456789:AAE...` |
| `CHAT_IDS` | оба id через запятую, напр. `111111111,222222222` |

## Шаг 4. Включить и проверить
1. Вкладка **Actions** → если просит — нажми «I understand… enable workflows».
2. Слева выбери **Cavo Zoe availability monitor** → **Run workflow** (ручной запуск).
3. Открой запуск: в логе шага *Run availability check* должно быть `Sold out`
   (сейчас 22–25 июля занято). Значит всё подключено верно.
4. Дальше робот сам запускается каждые ~5 минут. Как освободится номер —
   обоим прилетит уведомление.

## Проверить, что Telegram доходит
Временно поменяй в `config.json` дату на свободную, например
`"checkin": "2026-09-15"`, закоммить, запусти workflow вручную — должно прийти
сообщение. Потом верни `2026-07-22`.

## Остановить
Вкладка **Actions → … → Disable workflow**, либо просто удали репозиторий,
когда номер будет забронирован.

## Нюансы
- Cron в GitHub Actions — «не раньше чем», под нагрузкой возможна задержка на
  несколько минут. Для ловли номера это некритично.
- `state.json` GitHub коммитит сам между запусками — поэтому уведомление не
  спамит: приходит при появлении номера и повторяется не чаще раза в 30 минут.
