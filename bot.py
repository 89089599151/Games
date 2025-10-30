
"""
Truth-or-Dare Telegram Bot — SINGLE FILE (aiogram 3.x)

⚙️ Возможности (всё в одном файле):
- Лобби с /newgame: хост, Join/Leave, старт с инлайн-кнопок
- Игра в группах и личке, несколько чатов одновременно
- Инлайн-управление: Правда/Действие/Пропуск/Завершить
- Таймер хода (0/20/30/45 сек.), автопропуск/штраф
- Очки, /score, голосование «Засчитать?» 👍/👎 (или решение хоста)
- Категории (Лёгкое, Друзья, Романтика, Жесть), возрастные уровни (0+/12+/16+)
- Настройки: /settings или кнопка — выбор категорий, возраста, таймера, очков, штрафа
- Мини-"спиннер" для выбора следующего игрока
- Импорт пользовательской колоды одной командой: /import_deck {JSON}
  (формат см. ниже)

🔐 Безопасность:
- Токен берётся из ENV-переменной BOT_TOKEN. НИКОГДА не хардкодьте токен в код.
  Запуск:  BOT_TOKEN=123:ABC python bot.py

🧩 Формат пользовательской колоды (для команды /import_deck):
{
  "meta": {"lang": "ru", "version": 1},
  "items": [
    {
      "id": "rom-001",
      "type": "truth",           // "truth" или "dare"
      "category": "Романтика",
      "age": "12+",              // "0+" | "12+" | "16+"
      "tags": ["соц","креатив"], // произвольные теги
      "text": "Какое свидание ты считаешь идеальным?"
    }
  ]
}

📦 Зависимости: aiogram>=3
pip install -U aiogram

© 2025. Этот файл предназначен как компактный, готовый к запуску пример.
"""

import os
from dotenv import load_dotenv

load_dotenv()
import asyncio
import json
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
)

# ===========================
# CONFIG
# ===========================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise SystemExit(
        "❌ BOT_TOKEN не найден. Установите переменную окружения, например:\n"
        "BOT_TOKEN=123:ABC python bot.py"
    )

# Тайминги анимации спиннера
SPINNER_STEPS = 10
SPINNER_DELAY = 0.12

# ===========================
# БАЗОВАЯ КОЛОДА (можно расширять)
# ===========================

DEFAULT_DECK = [
    # Лёгкое — правда
    {"id":"light-t-01","type":"truth","category":"Лёгкое","age":"0+","tags":["смех"],"text":"Какой мем у тебя сейчас любимый?"},
    {"id":"light-t-02","type":"truth","category":"Лёгкое","age":"0+","tags":["соц"],"text":"Какой навык тебе хотелось бы мгновенно выучить?"},
    {"id":"light-t-03","type":"truth","category":"Лёгкое","age":"0+","tags":["смех"],"text":"Самая странная еда, которую ты пробовал(-а)?"},
    {"id":"light-t-04","type":"truth","category":"Лёгкое","age":"0+","tags":["креатив"],"text":"Если бы у тебя был слоган, как бы он звучал?"},
    {"id":"light-t-05","type":"truth","category":"Лёгкое","age":"0+","tags":["соц"],"text":"Что из последнего тебя по‑настоящему удивило?"},
    {"id":"light-t-06","type":"truth","category":"Лёгкое","age":"0+","tags":["соц"],"text":"В чём ты явно хорош(-а), но редко об этом говоришь?"},
    {"id":"light-t-07","type":"truth","category":"Лёгкое","age":"0+","tags":["смех"],"text":"Какой у тебя рингтон/звук уведомления?"},
    {"id":"light-t-08","type":"truth","category":"Лёгкое","age":"0+","tags":["соц"],"text":"Чей совет в этой компании ты чаще всего слушаешь?"},
    {"id":"light-t-09","type":"truth","category":"Лёгкое","age":"0+","tags":["креатив"],"text":"Назови три слова, которые описывают твой день."},
    {"id":"light-t-10","type":"truth","category":"Лёгкое","age":"0+","tags":["соц"],"text":"Какой у тебя «тихий» guilty pleasure?"},

    # Лёгкое — действие
    {"id":"light-d-01","type":"dare","category":"Лёгкое","age":"0+","tags":["смех"],"text":"Изобрази смех трёх разных злодеев."},
    {"id":"light-d-02","type":"dare","category":"Лёгкое","age":"0+","tags":["актив"],"text":"Сделай 10 мини‑приседаний, считая на выдуманном языке."},
    {"id":"light-d-03","type":"dare","category":"Лёгкое","age":"0+","tags":["креатив"],"text":"Озвучь на 15 секунд любой предмет в комнате."},
    {"id":"light-d-04","type":"dare","category":"Лёгкое","age":"0+","tags":["соц"],"text":"Скажи неожиданно тёплый комплимент двум игрокам."},
    {"id":"light-d-05","type":"dare","category":"Лёгкое","age":"0+","tags":["смех"],"text":"Покажи своё «самое серьёзное» лицо и не смейся 10 секунд."},
    {"id":"light-d-06","type":"dare","category":"Лёгкое","age":"0+","tags":["креатив"],"text":"Описывай всё вокруг будто ты спортивный комментатор, 20 секунд."},
    {"id":"light-d-07","type":"dare","category":"Лёгкое","age":"0+","tags":["актив"],"text":"Сделай 5 необычных поз йоги (безопасных)."},
    {"id":"light-d-08","type":"dare","category":"Лёгкое","age":"0+","tags":["соц"],"text":"Придумай каждому игроку смешной ник."},
    {"id":"light-d-09","type":"dare","category":"Лёгкое","age":"0+","tags":["смех"],"text":"Проговори скороговорку без ошибок: «Карл у Клары...»"},
    {"id":"light-d-10","type":"dare","category":"Лёгкое","age":"0+","tags":["креатив"],"text":"Сочини и прочитай двустишие о чём угодно."},

    # Друзья — правда
    {"id":"friends-t-01","type":"truth","category":"Друзья","age":"0+","tags":["соц"],"text":"Кто из нас чаще всего тебя смешит и почему?"},
    {"id":"friends-t-02","type":"truth","category":"Друзья","age":"0+","tags":["соц"],"text":"Какой общий ритуал нашей компании ты любишь?"},
    {"id":"friends-t-03","type":"truth","category":"Друзья","age":"0+","tags":["соц"],"text":"Как ты обычно решаешь конфликты с друзьями?"},
    {"id":"friends-t-04","type":"truth","category":"Друзья","age":"0+","tags":["соц"],"text":"Чем ты гордишься в одном из игроков?"},
    {"id":"friends-t-05","type":"truth","category":"Друзья","age":"0+","tags":["соц"],"text":"Что бы ты добавил(-а) к нашему следующему совместному плану?"},
    {"id":"friends-t-06","type":"truth","category":"Друзья","age":"0+","tags":["соц"],"text":"Какой совет ты бы дал(-а) себе год назад?"},
    {"id":"friends-t-07","type":"truth","category":"Друзья","age":"0+","tags":["соц"],"text":"Назови привычку, которую хочешь прокачать."},
    {"id":"friends-t-08","type":"truth","category":"Друзья","age":"0+","tags":["смех"],"text":"Самая нелепая совместная история?"},
    {"id":"friends-t-09","type":"truth","category":"Друзья","age":"0+","tags":["соц"],"text":"Кому из нас ты бы доверил(-а) важную задачу и почему?"},
    {"id":"friends-t-10","type":"truth","category":"Друзья","age":"0+","tags":["соц"],"text":"Какая «фишка» у каждого из нас?"},

    # Друзья — действие
    {"id":"friends-d-01","type":"dare","category":"Друзья","age":"0+","tags":["соц"],"text":"Сделай групповое фото с забавной темой (если офлайн)."},
    {"id":"friends-d-02","type":"dare","category":"Друзья","age":"0+","tags":["креатив"],"text":"Сыграй мини‑сценку «мы потеряли ключи», распределив роли."},
    {"id":"friends-d-03","type":"dare","category":"Друзья","age":"0+","tags":["смех"],"text":"Изобрази одного из друзей так, чтобы он узнал себя."},
    {"id":"friends-d-04","type":"dare","category":"Друзья","age":"0+","tags":["соц"],"text":"Каждому скажи, за что ты его ценишь."},
    {"id":"friends-d-05","type":"dare","category":"Друзья","age":"0+","tags":["креатив"],"text":"Придумай и объяви наш общий девиз."},
    {"id":"friends-d-06","type":"dare","category":"Друзья","age":"0+","tags":["актив"],"text":"Сделайте синхронный жест/танец втроём."},
    {"id":"friends-d-07","type":"dare","category":"Друзья","age":"0+","tags":["смех"],"text":"Изобрази видеоблогера, рекламирующего стакан воды."},
    {"id":"friends-d-08","type":"dare","category":"Друзья","age":"0+","tags":["соц"],"text":"Сделай голосовое на 10 секунд с неожиданным вдохновляющим тостом."},
    {"id":"friends-d-09","type":"dare","category":"Друзья","age":"0+","tags":["креатив"],"text":"Придумай каждому эмодзи‑геральдику."},
    {"id":"friends-d-10","type":"dare","category":"Друзья","age":"0+","tags":["смех"],"text":"Расскажи мини‑анекдот без смеха."},

    # Романтика — правда
    {"id":"romance-t-01","type":"truth","category":"Романтика","age":"12+","tags":["соц"],"text":"Какая мелочь делает свидание классным?"},
    {"id":"romance-t-02","type":"truth","category":"Романтика","age":"12+","tags":["соц"],"text":"Как ты показываешь заботу о людях?"},
    {"id":"romance-t-03","type":"truth","category":"Романтика","age":"12+","tags":["креатив"],"text":"Идея самого милого сюрприза?"},
    {"id":"romance-t-04","type":"truth","category":"Романтика","age":"12+","tags":["соц"],"text":"Фильм/песня, с которым у тебя связаны тёплые чувства?"},
    {"id":"romance-t-05","type":"truth","category":"Романтика","age":"12+","tags":["соц"],"text":"Твой язык любви (внимание, время, подарки, слова, помощь)?"},
    {"id":"romance-t-06","type":"truth","category":"Романтика","age":"12+","tags":["соц"],"text":"Что для тебя «идеальный вечер»?"},
    {"id":"romance-t-07","type":"truth","category":"Романтика","age":"12+","tags":["соц"],"text":"Какая граница в общении для тебя важна?"},
    {"id":"romance-t-08","type":"truth","category":"Романтика","age":"12+","tags":["соц"],"text":"Самая милая фраза, которую ты слышал(-а)?"},
    {"id":"romance-t-09","type":"truth","category":"Романтика","age":"12+","tags":["соц"],"text":"Какое качество ты ценишь в партнёре больше всего?"},
    {"id":"romance-t-10","type":"truth","category":"Романтика","age":"12+","tags":["соц"],"text":"Какая «маленькая забота» тебя трогает?"},

    # Романтика — действие
    {"id":"romance-d-01","type":"dare","category":"Романтика","age":"12+","tags":["соц"],"text":"Скажи тёплый комплимент любому игроку."},
    {"id":"romance-d-02","type":"dare","category":"Романтика","age":"12+","tags":["креатив"],"text":"Прочитай короткое «письмо благодарности» вслух (2–3 фразы)."},
    {"id":"romance-d-03","type":"dare","category":"Романтика","age":"12+","tags":["соц"],"text":"Поделись рекомендацией фильма/песни для уютного вечера."},
    {"id":"romance-d-04","type":"dare","category":"Романтика","age":"12+","tags":["креатив"],"text":"Сочини милую подпись к фото друга."},
    {"id":"romance-d-05","type":"dare","category":"Романтика","age":"12+","tags":["соц"],"text":"Назови 3 вещи, за которые благодарен(-на) сегодняшнему дню."},
    {"id":"romance-d-06","type":"dare","category":"Романтика","age":"12+","tags":["соц"],"text":"Поделись приятным воспоминанием (1 мин.)."},
    {"id":"romance-d-07","type":"dare","category":"Романтика","age":"12+","tags":["креатив"],"text":"Придумай добрый «слоган поддержки» для соседа слева."},
    {"id":"romance-d-08","type":"dare","category":"Романтика","age":"12+","tags":["соц"],"text":"Устрой мини‑челлендж «улыбнись и передай дальше»."},
    {"id":"romance-d-09","type":"dare","category":"Романтика","age":"12+","tags":["соц"],"text":"Скажи «спасибо» человеку, кому давно хотел(-а)."},
    {"id":"romance-d-10","type":"dare","category":"Романтика","age":"12+","tags":["соц"],"text":"Сделай короткий тост за хорошую компанию."},

    # Жесть — правда
    {"id":"extreme-t-01","type":"truth","category":"Жесть","age":"16+","tags":["соц"],"text":"Какой вызов себе ты откладываешь уже давно?"},
    {"id":"extreme-t-02","type":"truth","category":"Жесть","age":"16+","tags":["соц"],"text":"Самая смелая вещь, которую ты делал(-а)?"},
    {"id":"extreme-t-03","type":"truth","category":"Жесть","age":"16+","tags":["соц"],"text":"Какой свой страх ты готов(-а) «прощупать» сегодня?"},
    {"id":"extreme-t-04","type":"truth","category":"Жесть","age":"16+","tags":["соц"],"text":"О чём ты мечтаешь, но никому не говорил(-а)?"},
    {"id":"extreme-t-05","type":"truth","category":"Жесть","age":"16+","tags":["соц"],"text":"Что сложнее: попросить помощь или предложить её?"},
    {"id":"extreme-t-06","type":"truth","category":"Жесть","age":"16+","tags":["соц"],"text":"Какой риск ты принял(-а) и не жалеешь?"},
    {"id":"extreme-t-07","type":"truth","category":"Жесть","age":"16+","tags":["соц"],"text":"Где твоя «зона комфорта» сегодня?"},
    {"id":"extreme-t-08","type":"truth","category":"Жесть","age":"16+","tags":["соц"],"text":"Что бы ты сделал(-а), если б сегодня был последний день каникул?"},
    {"id":"extreme-t-09","type":"truth","category":"Жесть","age":"16+","tags":["соц"],"text":"Самая неловкая ситуация, которую ты превратил(-а) в шутку?"},
    {"id":"extreme-t-10","type":"truth","category":"Жесть","age":"16+","tags":["соц"],"text":"Какая твоя «грань», о которой знают немногие?"},

    # Жесть — действие
    {"id":"extreme-d-01","type":"dare","category":"Жесть","age":"16+","tags":["актив"],"text":"Сделай 20 приседаний или 10 отжиманий (безопасно)."},
    {"id":"extreme-d-02","type":"dare","category":"Жесть","age":"16+","tags":["смех"],"text":"Прочитай «скороговорку х3» быстро и без ошибок."},
    {"id":"extreme-d-03","type":"dare","category":"Жесть","age":"16+","tags":["креатив"],"text":"Сыграй мини‑монолог «если бы я оказался(-ась) в кино»."},
    {"id":"extreme-d-04","type":"dare","category":"Жесть","age":"16+","tags":["актив"],"text":"Сделай планку 30 секунд (по самочувствию)."},
    {"id":"extreme-d-05","type":"dare","category":"Жесть","age":"16+","tags":["соц"],"text":"Расскажи историю, где ты превозмог(-ла) себя."},
    {"id":"extreme-d-06","type":"dare","category":"Жесть","age":"16+","tags":["смех"],"text":"Покажи «злой взгляд» из кино и удерживай 10 сек."},
    {"id":"extreme-d-07","type":"dare","category":"Жесть","age":"16+","tags":["креатив"],"text":"Сочини рекламный слоган для предмета на столе."},
    {"id":"extreme-d-08","type":"dare","category":"Жесть","age":"16+","tags":["актив"],"text":"Сделай 15 медленных приседаний под счёт компании."},
    {"id":"extreme-d-09","type":"dare","category":"Жесть","age":"16+","tags":["соц"],"text":"Назови свою цель на неделю и как проверим результат."},
    {"id":"extreme-d-10","type":"dare","category":"Жесть","age":"16+","tags":["креатив"],"text":"Придумай «жёсткое» название нашему следующему челленджу."},

    # 18+ дополнения
    {"id":"romance18-t-01","type":"truth","category":"Романтика","age":"18+","tags":["соц"],"text":"Расскажи про романтический момент, который оставил в тебе «🔥 искру»?"},
    {"id":"romance18-d-01","type":"dare","category":"Романтика","age":"18+","tags":["креатив"],"text":"Сочини смелый тост, от которого всем станет жарко."},
    {"id":"extreme18-t-01","type":"truth","category":"Жесть","age":"18+","tags":["смех"],"text":"Какой самый дерзкий поступок ты сделал(-а) ради веселья?"},
    {"id":"extreme18-d-01","type":"dare","category":"Жесть","age":"18+","tags":["актив"],"text":"Придумай и изобрази «🔥 танец победы» длительностью 15 секунд."}
]

AGE_LEVELS: Dict[str, Dict[str, object]] = {
    "0+": {"emoji": "🌱", "title": "0+", "rank": 0},
    "12+": {"emoji": "🌟", "title": "12+", "rank": 1},
    "16+": {"emoji": "⚡", "title": "16+", "rank": 2},
    "18+": {"emoji": "🔥", "title": "18+", "rank": 3},
}

CATEGORY_INFO: Dict[str, Dict[str, object]] = {
    "Лёгкое": {"emoji": "✨", "title": "Лёгкое"},
    "Друзья": {"emoji": "🤝", "title": "Дружба"},
    "Романтика": {"emoji": "💞", "title": "Романтика"},
    "Жесть": {"emoji": "💥", "title": "Жесть"},
}

TIMER_OPTIONS: Sequence[int] = (0, 20, 30, 45, 60)
DEFAULT_TIMER_SECONDS = 30
DEFAULT_AGE_LEVEL = "16+"
DEFAULT_CATEGORY_KEY = "Лёгкое"
SELECTED_MARK = "✅"
UNSELECTED_MARK = "▫️"

# ===========================
# ИГРОВЫЕ СТРУКТУРЫ
# ===========================

@dataclass
class Player:
    user_id: int
    name: str

@dataclass
class Turn:
    player_id: int
    type: Optional[str] = None            # "truth" | "dare"
    card_id: Optional[str] = None
    message_id: Optional[int] = None      # сообщение с выбором/заданием

@dataclass
class VoteState:
    yes: Set[int] = field(default_factory=set)
    no: Set[int] = field(default_factory=set)
    message_id: Optional[int] = None

@dataclass
class ChatGame:
    chat_id: int
    host_id: int
    players: List[Player] = field(default_factory=list)
    current_idx: int = -1
    in_progress: bool = False
    scores: Dict[int, int] = field(default_factory=dict)
    used_ids: Set[str] = field(default_factory=set)
    settings: Dict = field(
        default_factory=lambda: {
            "timer": DEFAULT_TIMER_SECONDS,
            "points": True,
            "skip_penalty": 0,
            "age_level": DEFAULT_AGE_LEVEL,
            "category": DEFAULT_CATEGORY_KEY,
        }
    )
    current_turn: Optional[Turn] = None
    timer_task: Optional[asyncio.Task] = None
    vote: Optional[VoteState] = None
    extra_deck: List[Dict] = field(default_factory=list)  # пользовательские элементы
    lobby_message_id: Optional[int] = None
    settings_message_id: Optional[int] = None
    rounds_played: int = 0

    def current_player(self) -> Optional[Player]:
        if not self.players: return None
        if self.current_idx < 0: return None
        return self.players[self.current_idx % len(self.players)]

# Все игры по чатам
GAMES: Dict[int, ChatGame] = {}

# ===========================
# AIROGRAM SETUP
# ===========================

from aiogram.client.default import DefaultBotProperties

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

dp = Dispatcher()

# ===========================
# УТИЛИТЫ
# ===========================

def mention_html(user_id: int, name: str) -> str:
    safe = name.replace("<", "").replace(">", "")
    return f'<a href="tg://user?id={user_id}">{safe}</a>'

def is_host(game: ChatGame, user_id: int) -> bool:
    return game.host_id == user_id


def get_player(game: ChatGame, user_id: int) -> Optional[Player]:
    return next((p for p in game.players if p.user_id == user_id), None)


def format_player_name(game: ChatGame, player: Player) -> str:
    prefix = "👑" if player.user_id == game.host_id else "🎮"
    return f"{prefix} {mention_html(player.user_id, player.name)}"


def cleanup_scores(game: ChatGame):
    player_ids = {p.user_id for p in game.players}
    game.scores = {uid: score for uid, score in game.scores.items() if uid in player_ids}


def format_scores(game: ChatGame) -> str:
    cleanup_scores(game)
    if not game.scores:
        return "Пока никто не получил очки."
    ordered: List[Tuple[int, int]] = sorted(
        game.scores.items(), key=lambda kv: kv[1], reverse=True
    )
    lines = []
    for position, (uid, score) in enumerate(ordered, start=1):
        player = get_player(game, uid)
        name = player.name if player else f"Игрок {uid}"
        medal = "🥇" if position == 1 else "🥈" if position == 2 else "🥉" if position == 3 else "🎯"
        prefix = "👑" if uid == game.host_id else medal
        lines.append(f"{prefix} {mention_html(uid, name)} — <b>{score}</b>")
    return "\n".join(lines)


def describe_timer(seconds: int) -> str:
    return "Без таймера" if seconds <= 0 else f"{seconds} с"


def describe_age(level: str) -> str:
    data = AGE_LEVELS.get(level, AGE_LEVELS[DEFAULT_AGE_LEVEL])
    return f"{data['emoji']} {data['title']}"


def describe_category(category_key: str) -> str:
    if category_key not in CATEGORY_INFO:
        category_key = DEFAULT_CATEGORY_KEY
    info = CATEGORY_INFO.get(category_key, {"emoji": "❓", "title": category_key})
    title = info.get("title", category_key)
    return f"{info.get('emoji', '❓')} {title}"


def describe_penalty(game: ChatGame) -> str:
    return "-1" if game.settings.get("skip_penalty", 0) == -1 else "0"


def describe_points(game: ChatGame) -> str:
    return "Включены" if game.settings.get("points", True) else "Отключены"


def register_player(game: ChatGame, user_id: int, full_name: str) -> bool:
    if get_player(game, user_id):
        return False
    game.players.append(Player(user_id, full_name))
    game.scores.setdefault(user_id, 0)
    return True


def drop_player(game: ChatGame, user_id: int) -> bool:
    before = len(game.players)
    game.players = [p for p in game.players if p.user_id != user_id]
    removed = len(game.players) != before
    if removed:
        game.scores.pop(user_id, None)
    return removed


async def refresh_lobby(game: ChatGame, *, message: Optional[Message] = None):
    host_player = get_player(game, game.host_id)
    host_name = host_player.name if host_player else "Хост"
    players_lines = [format_player_name(game, p) for p in game.players]
    players_block = "\n".join(players_lines) if players_lines else "—"
    text = (
        "🧩 <b>Лобби игры</b>\n"
        f"👑 Хост: {mention_html(game.host_id, host_name)}\n"
        f"👥 Игроки ({len(game.players)}):\n{players_block}\n\n"
        "Жмите <b>Войти</b>, чтобы участвовать. Хост запускает игру кнопкой «Старт»."
    )
    keyboard = lobby_keyboard(game)
    target_chat = game.chat_id

    if message:
        try:
            await message.edit_text(text, reply_markup=keyboard)
            game.lobby_message_id = message.message_id
            return
        except Exception:
            pass

    if game.lobby_message_id:
        try:
            await bot.edit_message_text(
                text,
                chat_id=target_chat,
                message_id=game.lobby_message_id,
                reply_markup=keyboard,
            )
            return
        except Exception:
            pass

    sent = await bot.send_message(target_chat, text, reply_markup=keyboard)
    game.lobby_message_id = sent.message_id


def settings_summary(game: ChatGame) -> str:
    return (
        f"⏱️ Таймер: <b>{describe_timer(game.settings.get('timer', 0))}</b>\n"
        f"🎚 Возраст: <b>{describe_age(game.settings.get('age_level', DEFAULT_AGE_LEVEL))}</b>\n"
        f"🎭 Категория: <b>{describe_category(game.settings.get('category', DEFAULT_CATEGORY_KEY))}</b>\n"
        f"⭐ Очки: <b>{describe_points(game)}</b>\n"
        f"⚖️ Штраф за пропуск: <b>{describe_penalty(game)}</b>"
    )


def settings_text(game: ChatGame, menu: str) -> str:
    header = "⚙️ <b>Настройки игры</b>"
    summary = settings_summary(game)
    host_player = get_player(game, game.host_id)
    host_name = host_player.name if host_player else "Хост"
    if menu == "root":
        return (
            f"{header}\n"
            f"👑 Хост: {mention_html(game.host_id, host_name)}\n\n"
            f"{summary}\n\n"
            "Выбери раздел, чтобы изменить параметры.\n🔒 Менять значения может только хост."
        )
    if menu == "timer":
        return f"{header}\n\nВыбери длительность хода:"
    if menu == "age":
        return f"{header}\n\nВыбери возрастной уровень колоды:"
    if menu == "category":
        return f"{header}\n\nВыбери активную категорию вопросов:"
    if menu == "other":
        return f"{header}\n\nДополнительные настройки:" \
            f"\n\n{summary}"
    return header


def build_settings_keyboard(game: ChatGame, menu: str = "root") -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    if menu == "root":
        rows = [
            [
                InlineKeyboardButton(text="⏱️ Время", callback_data="st:menu:timer"),
                InlineKeyboardButton(text="🎚 Возраст", callback_data="st:menu:age"),
            ],
            [
                InlineKeyboardButton(text="🎭 Категория", callback_data="st:menu:category"),
                InlineKeyboardButton(text="🧩 Другое", callback_data="st:menu:other"),
            ],
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="st:close")],
        ]
    elif menu == "timer":
        current_timer = game.settings.get("timer", 0)
        rows = [
            [
                InlineKeyboardButton(
                    text=(
                        (f"{SELECTED_MARK} " if t == current_timer else f"{UNSELECTED_MARK} ")
                        + ("Без таймера" if t == 0 else f"{t} с")
                    ),
                    callback_data=f"st:set:timer:{t}",
                )
            ]
            for t in TIMER_OPTIONS
        ]
        rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="st:menu:root")])
    elif menu == "age":
        buttons = []
        current = game.settings.get("age_level", DEFAULT_AGE_LEVEL)
        for key, data in sorted(AGE_LEVELS.items(), key=lambda item: item[1]["rank"]):
            prefix = SELECTED_MARK if key == current else UNSELECTED_MARK
            buttons.append(
                InlineKeyboardButton(
                    text=f"{prefix} {data['emoji']} {data['title']}",
                    callback_data=f"st:set:age:{key}",
                )
            )
        rows = [[btn] for btn in buttons]
        rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="st:menu:root")])
    elif menu == "category":
        current = game.settings.get("category", DEFAULT_CATEGORY_KEY)
        if current not in CATEGORY_INFO:
            current = DEFAULT_CATEGORY_KEY
            game.settings["category"] = current
        rows = []
        for key, info in CATEGORY_INFO.items():
            prefix = SELECTED_MARK if key == current else UNSELECTED_MARK
            title = info.get("title", key)
            rows.append([
                InlineKeyboardButton(
                    text=f"{prefix} {info['emoji']} {title}",
                    callback_data=f"st:set:category:{key}",
                )
            ])
        rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="st:menu:root")])
    elif menu == "other":
        points_text = (
            "⭐ Очки: " + ("Вкл" if game.settings.get("points", True) else "Выкл")
        )
        penalty_text = (
            "⚖️ Штраф: "
            + ("-1" if game.settings.get("skip_penalty", 0) == -1 else "0")
        )
        rows = [
            [InlineKeyboardButton(text=points_text, callback_data="st:toggle:points")],
            [InlineKeyboardButton(text=penalty_text, callback_data="st:toggle:penalty")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="st:menu:root")],
        ]
    else:
        rows = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="st:menu:root")]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def show_settings_menu(
    game: ChatGame, menu: str = "root", *, message: Optional[Message] = None
):
    text = settings_text(game, menu)
    keyboard = build_settings_keyboard(game, menu)
    target_chat = game.chat_id

    if message:
        try:
            await message.edit_text(text, reply_markup=keyboard)
            game.settings_message_id = message.message_id
            return
        except Exception:
            pass

    if game.settings_message_id:
        try:
            await bot.edit_message_text(
                text,
                chat_id=target_chat,
                message_id=game.settings_message_id,
                reply_markup=keyboard,
            )
            return
        except Exception:
            pass

    sent = await bot.send_message(target_chat, text, reply_markup=keyboard)
    game.settings_message_id = sent.message_id


async def close_settings_menu(game: ChatGame):
    if not game.settings_message_id:
        return
    try:
        await bot.delete_message(game.chat_id, game.settings_message_id)
    except Exception:
        pass
    game.settings_message_id = None


async def join_game(game: ChatGame, user_id: int, full_name: str) -> Tuple[bool, str]:
    if not register_player(game, user_id, full_name):
        return False, "Ты уже в игре 😉"
    await refresh_lobby(game)
    return True, f"{mention_html(user_id, full_name)} вошёл(ла) в игру!"


async def leave_game(game: ChatGame, user_id: int) -> Tuple[bool, str]:
    if is_host(game, user_id):
        return False, "Хост управляет игрой и не может выйти. Используй /end."
    if not drop_player(game, user_id):
        return False, "Тебя нет в списке игроков."
    await refresh_lobby(game)
    if game.in_progress and game.current_turn and game.current_turn.player_id == user_id:
        await handle_skip(game.chat_id, reason="🚪 Игрок покинул игру. Ход передан далее.")
    return True, "Ты вышел из игры."


async def end_game_session(game: ChatGame, reason: str):
    await cancel_timer(game)
    await close_settings_menu(game)
    game.in_progress = False

    if game.vote and game.vote.message_id:
        try:
            await bot.edit_message_text(
                "Голосование закрыто.",
                chat_id=game.chat_id,
                message_id=game.vote.message_id,
            )
        except Exception:
            pass
    game.vote = None

    cleanup_scores(game)
    summary = format_scores(game)
    scoreboard_text = ""
    if game.settings.get("points", True) and game.rounds_played > 0 and game.scores:
        scoreboard_text = f"\n\n🏆 <b>Финальный счёт</b>:\n{summary}"
    elif game.scores:
        scoreboard_text = f"\n\n📊 Итоги:\n{summary}"

    await bot.send_message(game.chat_id, f"{reason}{scoreboard_text}")
    GAMES.pop(game.chat_id, None)

def get_deck_for_game(game: ChatGame) -> List[Dict]:
    # фильтр по возрасту/категориям
    selected_age = game.settings.get("age_level", DEFAULT_AGE_LEVEL)
    if selected_age not in AGE_LEVELS:
        selected_age = DEFAULT_AGE_LEVEL
        game.settings["age_level"] = selected_age
    age_rank = AGE_LEVELS[selected_age]["rank"]
    allowed_age = {
        age for age, data in AGE_LEVELS.items() if data["rank"] <= age_rank
    }

    selected_category = game.settings.get("category", DEFAULT_CATEGORY_KEY)
    if selected_category not in CATEGORY_INFO:
        selected_category = DEFAULT_CATEGORY_KEY
        game.settings["category"] = selected_category
    allowed_categories = {selected_category}

    deck = [
        c
        for c in (DEFAULT_DECK + game.extra_deck)
        if c.get("age") in allowed_age and c.get("category") in allowed_categories
    ]
    return deck

def pick_card(game: ChatGame, kind: str) -> Tuple[Optional[Dict], bool]:
    deck = [
        c
        for c in get_deck_for_game(game)
        if c.get("type") == kind and c.get("id") not in game.used_ids
    ]
    restarted = False
    if not deck:
        # сбрасываем использованные
        game.used_ids.clear()
        deck = [c for c in get_deck_for_game(game) if c.get("type") == kind]
        restarted = bool(deck)
    if not deck:
        return None, False
    return random.choice(deck), restarted

def lobby_keyboard(game: ChatGame) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="➕ Войти", callback_data="join"),
            InlineKeyboardButton(text="➖ Выйти", callback_data="leave"),
        ],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton(text="▶️ Старт", callback_data="start")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def turn_choice_keyboard(game: ChatGame, show_end: bool) -> InlineKeyboardMarkup:
    row1 = [
        InlineKeyboardButton(text="🟦 Правда", callback_data="truth"),
        InlineKeyboardButton(text="🟥 Действие", callback_data="dare"),
    ]
    row2 = [InlineKeyboardButton(text="🔁 Пропуск", callback_data="skip")]
    row3 = [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")]
    rows = [row1, row2, row3]
    if show_end:
        rows.append([InlineKeyboardButton(text="🏁 Завершить", callback_data="end")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def task_keyboard(game: ChatGame, for_host: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="✅ Выполнено", callback_data="done"),
         InlineKeyboardButton(text="🔁 Пропуск", callback_data="skip")]
    ]
    if for_host:
        rows.append([InlineKeyboardButton(text="🏁 Завершить", callback_data="end")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def vote_keyboard(for_host: bool) -> InlineKeyboardMarkup:
    rows = [[
        InlineKeyboardButton(text="👍 Зачесть", callback_data="vote:yes"),
        InlineKeyboardButton(text="👎 Не зачесть", callback_data="vote:no"),
    ]]
    if for_host:
        rows.append([
            InlineKeyboardButton(text="✅ Хост: зачесть", callback_data="host:accept"),
            InlineKeyboardButton(text="❌ Хост: отклонить", callback_data="host:reject"),
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def ensure_game(chat_id: int) -> Optional[ChatGame]:
    return GAMES.get(chat_id)

async def cancel_timer(game: ChatGame):
    if game and game.timer_task and not game.timer_task.done():
        game.timer_task.cancel()
        try:
            await game.timer_task
        except asyncio.CancelledError:
            pass
        game.timer_task = None

async def start_timer(game: ChatGame, seconds: int, on_expire):
    await cancel_timer(game)
    if seconds <= 0:
        return
    async def _job():
        try:
            await asyncio.sleep(seconds)
            await on_expire()
        except asyncio.CancelledError:
            return
    game.timer_task = asyncio.create_task(_job())

def next_index(game: ChatGame) -> int:
    if not game.players:
        return -1
    # не повторять одного и того же подряд
    game.current_idx = (game.current_idx + 1) % len(game.players)
    return game.current_idx

# ===========================
# ХЕНДЛЕРЫ
# ===========================

@dp.message(CommandStart())
async def on_start(m: Message):
    await m.answer(
        "👋 Привет! Это игра <b>Правда или Действие</b>.\n\n"
        "Создай лобби командой /newgame — ты автоматически станешь хостом."
        " Пригласи друзей кнопкой «Войти», а затем жми «Старт», когда все готовы.\n\n"
        "<b>Команды</b>:\n"
        "• /newgame — создать лобби\n"
        "• /join и /leave — войти или выйти\n"
        "• /score — посмотреть счёт\n"
        "• /settings — открыть настройки (только хост)\n"
        "• /end — завершить игру\n"
        "• /help — подсказки и правила\n"
    )

@dp.message(Command("newgame"))
async def cmd_newgame(m: Message):
    chat_id = m.chat.id
    user_id = m.from_user.id

    existing = GAMES.get(chat_id)
    if existing:
        await end_game_session(existing, "🔁 Лобби перезапущено новым хостом.")

    game = ChatGame(chat_id=chat_id, host_id=user_id)
    register_player(game, user_id, m.from_user.full_name)
    GAMES[chat_id] = game

    placeholder = await m.answer("🆕 Создаём лобби...", reply_markup=lobby_keyboard(game))
    await refresh_lobby(game, message=placeholder)

@dp.message(Command("join"))
async def cmd_join(m: Message):
    chat_id = m.chat.id
    game = ensure_game(chat_id)
    if not game:
        await m.answer("Лобби ещё не создано. Используйте /newgame")
        return
    ok, text = await join_game(game, m.from_user.id, m.from_user.full_name)
    await m.answer(f"{'✅ ' if ok else ''}{text}")

@dp.message(Command("leave"))
async def cmd_leave(m: Message):
    chat_id = m.chat.id
    game = ensure_game(chat_id)
    if not game:
        await m.answer("Игра не найдена.")
        return
    ok, text = await leave_game(game, m.from_user.id)
    await m.answer(f"{'✅ ' if ok else ''}{text}")

@dp.message(Command("score"))
async def cmd_score(m: Message):
    chat_id = m.chat.id
    game = ensure_game(chat_id)
    if not game or not game.scores:
        await m.answer("Пока нет очков.")
        return
    await m.answer("📊 <b>Текущий счёт</b>:\n" + format_scores(game))

@dp.message(Command("settings"))
async def cmd_settings(m: Message):
    chat_id = m.chat.id
    game = ensure_game(chat_id)
    if not game:
        await m.answer("Игра не найдена. Сначала /newgame")
        return
    await show_settings_menu(game)

@dp.message(Command("end"))
async def cmd_end(m: Message):
    chat_id = m.chat.id
    game = ensure_game(chat_id)
    if not game:
        await m.answer("Игра не найдена.")
        return
    if not is_host(game, m.from_user.id):
        await m.answer("Только хост может завершить игру.")
        return
    await end_game_session(game, "🏁 Игра завершена. Спасибо за игру!")


@dp.message(Command("help"))
async def cmd_help(m: Message):
    await m.answer(
        "ℹ️ <b>Правила и команды</b>\n\n"
        "Создай лобби командой /newgame. Хост автоматически попадает в список игроков и может пригласить остальных.\n"
        "Игроки присоединяются через /join или кнопку «Войти», выходят через /leave.\n\n"
        "Когда готовы — хост жмёт «Старт». Каждый ход игрок выбирает <b>Правда</b> или <b>Действие</b>.\n"
        "Выполнил? Голосуйте 👍/👎 или пусть хост решит.\n\n"
        "Команды: /score — счёт, /settings — настройки (доступно хосту), /end — завершить игру, /import_deck — добавить свои вопросы."
    )

@dp.message(Command("import_deck"))
async def cmd_import_deck(m: Message):
    chat_id = m.chat.id
    game = ensure_game(chat_id)
    if not game:
        await m.answer("Игра не найдена. Сначала /newgame")
        return
    if not is_host(game, m.from_user.id):
        await m.answer("Только хост может импортировать колоду.")
        return
    # Ожидаем JSON прямо в тексте сообщения после команды
    # Пример: /import_deck { "meta":..., "items":[...] }
    args_text = m.text.partition(" ")[2].strip()
    if not args_text:
        await m.answer("Пришли JSON после команды. Пример:\n"
                       "/import_deck {\"meta\":{\"lang\":\"ru\",\"version\":1},\"items\":[{...}]}")
        return
    try:
        payload = json.loads(args_text)
        items = payload.get("items", [])
        added = 0
        for it in items:
            if all(k in it for k in ("id","type","category","age","text")) and it["type"] in ("truth","dare"):
                game.extra_deck.append(it)
                added += 1
        await m.answer(f"✅ Импортировано карточек: <b>{added}</b>")
    except Exception as e:
        await m.answer(f"❌ Ошибка парсинга JSON: {e}")

# ===========================
# CALLBACKS (Inline)
# ===========================

@dp.callback_query(F.data == "join")
async def cb_join(c: CallbackQuery):
    chat_id = c.message.chat.id
    game = ensure_game(chat_id)
    if not game:
        await c.answer("Сначала /newgame", show_alert=True); return
    ok, text = await join_game(game, c.from_user.id, c.from_user.full_name)
    if ok:
        await c.message.answer(f"✅ {text}")
        await c.answer("Готово!")
    else:
        await c.answer(text, show_alert=True)

@dp.callback_query(F.data == "leave")
async def cb_leave(c: CallbackQuery):
    chat_id = c.message.chat.id
    game = ensure_game(chat_id)
    if not game:
        await c.answer("Игра не найдена.", show_alert=True); return
    ok, text = await leave_game(game, c.from_user.id)
    if ok:
        await c.message.answer(f"ℹ️ {text}")
        await c.answer("Готово!")
    else:
        await c.answer(text, show_alert=True)

@dp.callback_query(F.data == "start")
async def cb_start(c: CallbackQuery):
    chat_id = c.message.chat.id
    game = ensure_game(chat_id)
    if not game:
        await c.answer("Игра не найдена.", show_alert=True); return
    if not is_host(game, c.from_user.id):
        await c.answer("Только хост может начать.", show_alert=True); return
    if len(game.players) < 2:
        await c.answer("Нужно минимум 2 игрока.", show_alert=True); return

    game.in_progress = True
    game.current_idx = -1
    game.used_ids.clear()
    game.rounds_played = 0
    cleanup_scores(game)
    await close_settings_menu(game)

    await c.message.edit_text("🎲 Игра началась! Готовьтесь к первому вопросу.")
    await next_turn(c.message, game)

async def next_turn(msg: Message, game: ChatGame):
    # отменяем предыдущий таймер
    await cancel_timer(game)
    # выбор следующего игрока
    if next_index(game) == -1:
        await msg.answer("Нет игроков. /newgame")
        return
    pl = game.current_player()
    # мини-спиннер
    tmp = await msg.answer("🎯 Выбираем следующего игрока...")
    names = [p.name for p in game.players]
    for _ in range(SPINNER_STEPS):
        nm = random.choice(names)
        await asyncio.sleep(SPINNER_DELAY)
        try:
            await tmp.edit_text(f"🎯 Выбираем... <b>{nm}</b>")
        except Exception:
            pass
    await tmp.edit_text(
        f"👉 Ход игрока: <b>{pl.name}</b> ({len(game.players)} игроков)\n"
        f"Категория: {describe_category(game.settings.get('category', DEFAULT_CATEGORY_KEY))} | "
        f"Таймер: {describe_timer(game.settings.get('timer', 0))}"
    )

    # сообщение с выбором
    keyboard = turn_choice_keyboard(game, show_end=True)
    sent = await msg.answer(
        f"{mention_html(pl.user_id, pl.name)}, выбери <b>Правда</b> или <b>Действие</b>.",
        reply_markup=keyboard
    )
    game.current_turn = Turn(player_id=pl.user_id, message_id=sent.message_id)
    game.vote = None

@dp.callback_query(F.data.in_({"truth","dare"}))
async def cb_pick_type(c: CallbackQuery):
    chat_id = c.message.chat.id
    game = ensure_game(chat_id)
    if not game or not game.in_progress:
        await c.answer("Игра не идёт.", show_alert=True); return
    # только текущий игрок может выбирать
    turn = game.current_turn
    if not turn or c.from_user.id != turn.player_id:
        await c.answer("Сейчас ход другого игрока.", show_alert=True); return

    kind = "truth" if c.data == "truth" else "dare"
    card, restarted = pick_card(game, kind)
    if not card:
        await end_game_session(game, "📦 Карточки закончились. Игра завершена.")
        await c.answer("Карточки закончились.", show_alert=True)
        return

    if restarted:
        await bot.send_message(chat_id, "📦 Колода исчерпана — перемешиваем и продолжаем!")

    game.used_ids.add(card["id"])
    turn.type = kind
    turn.card_id = card["id"]

    # Показ задания
    try:
        await c.message.edit_text(
            f"👉 <b>Ход:</b> {mention_html(turn.player_id, 'Игрок')}\n"
            f"{'🟦 Правда' if kind=='truth' else '🟥 Действие'}:\n"
            f"{card['text']}",
            reply_markup=task_keyboard(game, for_host=True)
        )
    except Exception:
        pass

    # Запускаем таймер на выполнение
    async def on_expire():
        # если к этому моменту голосование/завершение не произошло — автопропуск
        await handle_skip(chat_id, reason="⏱️ Время вышло — пропуск.")
    await start_timer(game, game.settings["timer"], on_expire)
    await c.answer()

@dp.callback_query(F.data == "skip")
async def cb_skip(c: CallbackQuery):
    await c.answer()
    await handle_skip(c.message.chat.id, reason="🔁 Пропуск.")

async def handle_skip(chat_id: int, reason: str):
    game = ensure_game(chat_id)
    if not game: return
    await cancel_timer(game)
    # штраф при настройке
    penalty_note = ""
    if game.settings["skip_penalty"] == -1 and game.settings["points"] and game.current_turn:
        uid = game.current_turn.player_id
        game.scores[uid] = game.scores.get(uid, 0) - 1
        penalty_note = " (−1 очко)"
    if game.vote and game.vote.message_id:
        try:
            await bot.edit_message_text(
                "Голосование прекращено.",
                chat_id=chat_id,
                message_id=game.vote.message_id,
            )
        except Exception:
            pass
        game.vote = None
    game.rounds_played += 1
    await bot.send_message(chat_id, f"{reason}{penalty_note}")
    await proceed_next(chat_id)

@dp.callback_query(F.data == "done")
async def cb_done(c: CallbackQuery):
    chat_id = c.message.chat.id
    game = ensure_game(chat_id)
    if not game or not game.current_turn:
        await c.answer("Нет активного задания.", show_alert=True); return
    if game.vote:
        await c.answer("Голосование уже идёт.", show_alert=True)
        return
    # Любой игрок может инициировать голосование
    await cancel_timer(game)
    game.vote = VoteState(yes=set(), no=set())
    text = "🗳️ Засчитываем выполнение? 👍/👎"
    vk = vote_keyboard(for_host=True)
    poll = await c.message.answer(text, reply_markup=vk)
    game.vote.message_id = poll.message_id
    await c.answer()

@dp.callback_query(F.data.in_({"vote:yes", "vote:no", "host:accept", "host:reject"}))
async def cb_vote(c: CallbackQuery):
    chat_id = c.message.chat.id
    game = ensure_game(chat_id)
    if not game or not game.vote or not game.current_turn:
        await c.answer(); return

    # Хост решает мгновенно
    if c.data == "host:accept" and is_host(game, c.from_user.id):
        await finalize_task(chat_id, success=True, by="Хост зачёл ✅")
        await c.answer("Засчитано хостом.")
        return
    if c.data == "host:reject" and is_host(game, c.from_user.id):
        await finalize_task(chat_id, success=False, by="Хост отклонил ❌")
        await c.answer("Не засчитано хостом.")
        return

    # Обычное голосование
    uid = c.from_user.id
    if c.data == "vote:yes":
        game.vote.no.discard(uid)
        game.vote.yes.add(uid)
    else:
        game.vote.yes.discard(uid)
        game.vote.no.add(uid)

    total_players = max(1, len(game.players))
    yes_count, no_count = len(game.vote.yes), len(game.vote.no)
    try:
        await c.message.edit_text(f"🗳️ Голоса: 👍 {yes_count} | 👎 {no_count}", reply_markup=vote_keyboard(for_host=True))
    except Exception:
        pass

    # Простая логика: если 👍 > 50% игроков — успех; если 👎 > 50% — провал
    if yes_count > total_players / 2:
        await finalize_task(chat_id, success=True, by="✅ Большинство ЗА")
    elif no_count > total_players / 2:
        await finalize_task(chat_id, success=False, by="❌ Большинство ПРОТИВ")

    await c.answer()

async def finalize_task(chat_id: int, success: bool, by: str):
    game = ensure_game(chat_id)
    if not game or not game.current_turn: return
    await cancel_timer(game)
    turn = game.current_turn

    # Очки
    if game.settings["points"] and turn.player_id:
        game.scores.setdefault(turn.player_id, 0)
        if success:
            game.scores[turn.player_id] += 1

    if not game.settings["points"]:
        points_text = "Очки отключены."
    else:
        points_text = "Очко начислено!" if success else "Очки без изменений."

    result_text = f"{by}. {points_text}"

    edited = False
    if game.vote and game.vote.message_id:
        try:
            await bot.edit_message_text(
                result_text,
                chat_id=chat_id,
                message_id=game.vote.message_id,
            )
            edited = True
        except Exception:
            pass

    if not edited:
        await bot.send_message(chat_id, result_text)
    game.vote = None
    game.rounds_played += 1
    await proceed_next(chat_id)

async def proceed_next(chat_id: int):
    game = ensure_game(chat_id)
    if not game: return
    if not game.in_progress:
        return
    game.current_turn = None
    await next_turn(await bot.send_message(chat_id, "▶️ Следующий ход..."), game)

@dp.callback_query(F.data == "end")
async def cb_end(c: CallbackQuery):
    chat_id = c.message.chat.id
    game = ensure_game(chat_id)
    if not game:
        await c.answer("Игра не найдена.", show_alert=True); return
    if not is_host(game, c.from_user.id):
        await c.answer("Только хост может завершить.", show_alert=True); return
    await end_game_session(game, "🏁 Игра завершена. Спасибо за игру!")
    await c.answer()

# ====== SETTINGS ======

@dp.callback_query(F.data == "settings")
async def cb_settings(c: CallbackQuery):
    game = ensure_game(c.message.chat.id)
    if not game:
        await c.answer("Игра не найдена.", show_alert=True); return
    await show_settings_menu(game)
    await c.answer()

@dp.callback_query(F.data.startswith("st:"))
async def cb_settings_router(c: CallbackQuery):
    game = ensure_game(c.message.chat.id)
    if not game:
        await c.answer("Игра не найдена.", show_alert=True)
        return

    parts = c.data.split(":")
    action = parts[1]

    if action == "menu":
        menu = parts[2] if len(parts) > 2 else "root"
        await show_settings_menu(game, menu=menu, message=c.message)
        await c.answer()
        return

    if action == "close":
        await close_settings_menu(game)
        await c.answer("Меню закрыто")
        return

    if not is_host(game, c.from_user.id):
        await c.answer("Только хост может менять настройки.", show_alert=True)
        return

    if action == "set" and len(parts) >= 4:
        target, value = parts[2], parts[3]
        if target == "timer":
            val = int(value)
            if val not in TIMER_OPTIONS:
                await c.answer("Такой таймер недоступен", show_alert=True)
                return
            game.settings["timer"] = val
            await c.answer("Таймер обновлён")
            await show_settings_menu(game, menu="timer", message=c.message)
            return
        if target == "age" and value in AGE_LEVELS:
            game.settings["age_level"] = value
            await c.answer("Возрастной уровень изменён")
            await show_settings_menu(game, menu="age", message=c.message)
            return
        if target == "category" and value in CATEGORY_INFO:
            game.settings["category"] = value
            await c.answer("Категория обновлена")
            await show_settings_menu(game, menu="category", message=c.message)
            return

    if action == "toggle" and len(parts) >= 3:
        toggle_target = parts[2]
        if toggle_target == "points":
            game.settings["points"] = not game.settings.get("points", True)
            await c.answer("Настройка очков изменена")
        elif toggle_target == "penalty":
            game.settings["skip_penalty"] = -1 if game.settings.get("skip_penalty", 0) == 0 else 0
            await c.answer("Штраф обновлён")
        await show_settings_menu(game, menu="other", message=c.message)
        return

    await c.answer()

# ===========================
# MAIN
# ===========================

async def main():
    print("✅ Bot is running...")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    asyncio.run(main())
