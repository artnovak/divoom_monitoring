# Divoom DitooMic PC Monitor

Небольшой монитор для Divoom DitooMic на Windows.

Он показывает на экране:

- CPU
- GPU
- RAM
- Steam игру, если она запущена
- League of Legends, если идёт матч
- для LoL: режим, чемпион, время и счёт K/D/A

Работает через Bluetooth Serial Port. На моём ПК это `COM7`.

## Что нужно

- Windows
- Python 3.12 или новее
- Divoom DitooMic, уже подключённый к Windows
- Bluetooth-порт `DitooMic-Light`

## Установка

Открой PowerShell в папке проекта:

```powershell
cd C:\path\to\divoom-ditoomic-monitor
```

Создай окружение:

```powershell
python -m venv .venv
```

Поставь зависимости:

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
```

## Проверка экрана

Если у тебя DitooMic на `COM7`:

```powershell
.\.venv\Scripts\python -m divoom_pc_monitor.app test --port COM7
```

Если порт другой, поменяй `COM7` на свой.

Порт можно посмотреть в Windows:

`Диспетчер устройств -> Порты COM и LPT`

Нужен Bluetooth serial port, который относится к DitooMic.

## Запуск

```powershell
.\start_monitor.ps1
```

Остановка:

```powershell
.\stop_monitor.ps1
```

Логи:

```powershell
Get-Content .\logs\monitor.log -Tail 40
Get-Content .\logs\monitor.err.log -Tail 40
```

## Автозапуск

Добавить запуск при входе в Windows:

```powershell
.\install_autostart.ps1
```

Убрать автозапуск:

```powershell
.\uninstall_autostart.ps1
```

## League of Legends

Во время матча монитор сам переключается на LoL.

Он берёт данные из локального LoL API:

```text
https://127.0.0.1:2999/liveclientdata/allgamedata
```

Никакие логины и токены Riot не нужны.

Проверить, видит ли скрипт игру:

```powershell
.\.venv\Scripts\python -m divoom_pc_monitor.app game-status
```

## Steam

Если запущена Steam-игра, монитор показывает игровой экран.

Steam API ключ не нужен. Скрипт смотрит на процессы и файлы Steam library.

## Если не работает

1. Закрой приложение Divoom на телефоне.
2. Проверь, что DitooMic подключён к Windows.
3. Проверь COM-порт.
4. Запусти тест:

```powershell
.\.venv\Scripts\python -m divoom_pc_monitor.app test --port COM7
```

5. Если порт не `COM7`, поменяй его в `start_monitor.ps1`.
