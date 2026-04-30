from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import psutil


STEAM_EXCLUDED_PROCESSES = {
    "steam.exe",
    "steamservice.exe",
    "steamwebhelper.exe",
    "gameoverlayui.exe",
    "crashhandler.exe",
}


@dataclass(slots=True)
class GameStatus:
    kind: str
    title: str
    subtitle: str = ""
    elapsed_seconds: int | None = None
    mode: str = ""
    champion: str = ""
    kills: int | None = None
    deaths: int | None = None
    assists: int | None = None


class GameDetector:
    def __init__(self) -> None:
        self._steam_games = _load_steam_games()

    def current(self) -> GameStatus | None:
        league = _detect_league_game()
        if league:
            return league
        return _detect_steam_game(self._steam_games)


def _detect_league_game() -> GameStatus | None:
    live_data = _fetch_lol_live_data()
    if live_data:
        game_data = live_data.get("gameData", {}) or {}
        game_time = int(float(game_data.get("gameTime", 0)))
        mode = _lol_mode_code(game_data)
        player = live_data.get("activePlayer", {}) or {}
        summoner_name = player.get("summonerName", "")
        active_player = _active_lol_player(live_data, summoner_name)
        champion = _lol_champion_name(active_player)
        scores = active_player.get("scores", {}) if active_player else {}
        return GameStatus(
            kind="lol",
            title="LOL",
            subtitle=champion or summoner_name or "LIVE",
            elapsed_seconds=game_time,
            mode=mode,
            champion=champion or summoner_name,
            kills=_int_or_none(scores.get("kills")),
            deaths=_int_or_none(scores.get("deaths")),
            assists=_int_or_none(scores.get("assists")),
        )

    for proc in psutil.process_iter(["name"]):
        name = (proc.info.get("name") or "").lower()
        if name == "league of legends.exe":
            return GameStatus(kind="lol", title="LOL", subtitle="LIVE", mode="LIVE")
    return None


def _active_lol_player(live_data: dict, summoner_name: str) -> dict:
    if not summoner_name:
        return {}
    for player in live_data.get("allPlayers", []) or []:
        if player.get("summonerName") == summoner_name:
            return player
    return {}


def _lol_champion_name(player: dict) -> str:
    raw = str(player.get("rawChampionName", "") or "")
    if raw.startswith("game_character_displayname_"):
        return raw.removeprefix("game_character_displayname_")
    return str(player.get("championName", "") or "")


def _lol_mode_code(game_data: dict) -> str:
    mode = str(game_data.get("gameMode", "") or "").upper()
    map_name = str(game_data.get("mapName", "") or "").lower()
    map_number = _int_or_none(game_data.get("mapNumber"))
    if mode == "ARAM" or map_number == 12 or "howling" in map_name:
        return "ARAM"
    if mode == "CLASSIC" or map_number == 11 or "summoner" in map_name:
        return "RIFT"
    if mode in {"CHERRY", "STRAWBERRY"} or map_number == 30:
        return "ARE"
    if "URF" in mode:
        return "URF"
    if "TUTORIAL" in mode:
        return "TUT"
    if "PRACTICE" in mode:
        return "PRAC"
    if not mode:
        return "LIVE"
    return mode[:4]


def _int_or_none(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _fetch_lol_live_data() -> dict | None:
    request = urllib.request.Request(
        "https://127.0.0.1:2999/liveclientdata/allgamedata",
        headers={"Accept": "application/json"},
    )
    context = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(request, context=context, timeout=0.35) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return None


def _load_steam_games() -> list[tuple[Path, str]]:
    steam_root = Path("C:/Program Files (x86)/Steam")
    library_file = steam_root / "steamapps" / "libraryfolders.vdf"
    if not library_file.exists():
        return []

    text = library_file.read_text(encoding="utf-8", errors="ignore")
    library_paths = [
        Path(match.replace("\\\\", "\\"))
        for match in re.findall(r'"path"\s+"([^"]+)"', text)
    ]

    games: list[tuple[Path, str]] = []
    for library in library_paths:
        steamapps = library / "steamapps"
        common = steamapps / "common"
        for manifest in steamapps.glob("appmanifest_*.acf"):
            data = manifest.read_text(encoding="utf-8", errors="ignore")
            name = _acf_value(data, "name")
            install_dir = _acf_value(data, "installdir")
            if not name or not install_dir:
                continue
            path = (common / install_dir).resolve()
            if path.exists():
                games.append((path, name))

    return sorted(games, key=lambda item: len(str(item[0])), reverse=True)


def _acf_value(text: str, key: str) -> str:
    match = re.search(rf'"{re.escape(key)}"\s+"([^"]*)"', text)
    return match.group(1) if match else ""


def _detect_steam_game(games: list[tuple[Path, str]]) -> GameStatus | None:
    if not games:
        return None

    for proc in psutil.process_iter(["name", "exe"]):
        name = (proc.info.get("name") or "").lower()
        if name in STEAM_EXCLUDED_PROCESSES:
            continue
        exe = proc.info.get("exe")
        if not exe:
            continue
        try:
            exe_path = Path(exe).resolve()
        except OSError:
            continue

        for game_path, title in games:
            if _is_relative_to(exe_path, game_path):
                return GameStatus(kind="steam", title="STM", subtitle=title)
    return None


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
