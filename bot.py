
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
from typing import Dict, List, Optional, Set

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
    {"id":"extreme-d-10","type":"dare","category":"Жесть","age":"16+","tags":["креатив"],"text":"Придумай «жёсткое» название нашему следующему челленджу."}
]

CATEGORIES = ["Лёгкое", "Друзья", "Романтика", "Жесть"]
AGE_LEVELS = ["0+", "12+", "16+"]  # PG, без откровенного 18+

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
    settings: Dict = field(default_factory=lambda: {
        "timer": 30,            # сек., 0 отключить
        "points": True,         # начислять очки
        "skip_penalty": 0,      # -1 если нужен штраф
        "age": set(AGE_LEVELS), # доступные уровни
        "categories": set(CATEGORIES) # активные категории
    })
    current_turn: Optional[Turn] = None
    timer_task: Optional[asyncio.Task] = None
    vote: Optional[VoteState] = None
    extra_deck: List[Dict] = field(default_factory=list)  # пользовательские элементы

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

def get_deck_for_game(game: ChatGame) -> List[Dict]:
    # фильтр по возрасту/категориям
    allowed_age = game.settings["age"]
    allowed_cat = game.settings["categories"]
    deck = [c for c in (DEFAULT_DECK + game.extra_deck)
            if c.get("age") in allowed_age and c.get("category") in allowed_cat]
    return deck

def pick_card(game: ChatGame, kind: str) -> Dict:
    deck = [c for c in get_deck_for_game(game)
            if c.get("type") == kind and c.get("id") not in game.used_ids]
    if not deck:
        # сбрасываем использованные
        game.used_ids.clear()
        deck = [c for c in get_deck_for_game(game) if c.get("type") == kind]
    return random.choice(deck) if deck else {}

def lobby_keyboard(game: ChatGame) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="➕ Join", callback_data="join"),
         InlineKeyboardButton(text="➖ Leave", callback_data="leave")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton(text="▶️ Старт", callback_data="start")]
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

def settings_keyboard(game: ChatGame) -> InlineKeyboardMarkup:
    # Кнопки таймера
    timers = [0, 20, 30, 45]
    t_buttons = [InlineKeyboardButton(
        text=("⏱️ " + ("● " if game.settings["timer"]==t else "") + (str(t)+"s" if t>0 else "Off")),
        callback_data=f"timer:{t}"
    ) for t in timers]

    # Очки и штраф
    p_text = "Очки: Вкл" if game.settings["points"] else "Очки: Выкл"
    pen_text = "Штраф за пропуск: -1" if game.settings["skip_penalty"] == -1 else "Штраф: 0"
    p_buttons = [
        InlineKeyboardButton(text=p_text, callback_data="points:toggle"),
        InlineKeyboardButton(text=pen_text, callback_data="penalty:toggle")
    ]

    # Возраст
    age_buttons = []
    for a in AGE_LEVELS:
        on = "●" if a in game.settings["age"] else "○"
        age_buttons.append(InlineKeyboardButton(text=f"{on} {a}", callback_data=f"age:{a}"))

    # Категории (две в ряд)
    cat_rows = []
    cats = list(CATEGORIES)
    for i in range(0, len(cats), 2):
        row = []
        for c in cats[i:i+2]:
            on = "●" if c in game.settings["categories"] else "○"
            row.append(InlineKeyboardButton(text=f"{on} {c}", callback_data=f"cat:{c}"))
        cat_rows.append(row)

    rows: List[List[InlineKeyboardButton]] = [
        t_buttons,
        p_buttons,
        age_buttons,
        *cat_rows,
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    ]
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
        "👋 Привет! Это игра <b>Правда или Действие</b>.\n"
        "Создай лобби командой /newgame, подключайся кнопкой <i>Join</i>, "
        "затем хост запускает игру.\n\n"
        "<b>Команды</b>:\n"
        "/newgame — создать новую игру\n"
        "/join — присоединиться\n"
        "/leave — выйти\n"
        "/score — счёт\n"
        "/settings — настройки\n"
        "/end — завершить игру\n"
    )

@dp.message(Command("newgame"))
async def cmd_newgame(m: Message):
    chat_id = m.chat.id
    user_id = m.from_user.id

    # Прерываем предыдущую игру в чате (если была)
    if chat_id in GAMES:
        await cancel_timer(GAMES[chat_id])

    game = ChatGame(chat_id=chat_id, host_id=user_id)
    GAMES[chat_id] = game

    await m.answer(
        f"🧩 Создано лобби. Хост: {mention_html(user_id, m.from_user.full_name)}\n"
        f"Нажмите <b>Join</b>, затем хост может запустить игру.",
        reply_markup=lobby_keyboard(game)
    )

@dp.message(Command("join"))
async def cmd_join(m: Message):
    chat_id = m.chat.id
    game = ensure_game(chat_id)
    if not game:
        await m.answer("Лобби ещё не создано. Используйте /newgame")
        return
    if any(p.user_id == m.from_user.id for p in game.players):
        await m.answer("Ты уже в игре 😉")
        return
    game.players.append(Player(m.from_user.id, m.from_user.full_name))
    game.scores.setdefault(m.from_user.id, 0)
    await m.answer(f"Присоединился(ась): {mention_html(m.from_user.id, m.from_user.full_name)}")

@dp.message(Command("leave"))
async def cmd_leave(m: Message):
    chat_id = m.chat.id
    game = ensure_game(chat_id)
    if not game:
        await m.answer("Игра не найдена.")
        return
    game.players = [p for p in game.players if p.user_id != m.from_user.id]
    await m.answer("Готово, ты вышел(-ла) из лобби.")

@dp.message(Command("score"))
async def cmd_score(m: Message):
    chat_id = m.chat.id
    game = ensure_game(chat_id)
    if not game or not game.scores:
        await m.answer("Пока нет очков.")
        return
    lines = []
    for uid, score in sorted(game.scores.items(), key=lambda kv: kv[1], reverse=True):
        name = next((p.name for p in game.players if p.user_id == uid), f"User {uid}")
        lines.append(f"{mention_html(uid, name)} — <b>{score}</b>")
    await m.answer("📊 <b>Счёт</b>:\n" + "\n".join(lines))

@dp.message(Command("settings"))
async def cmd_settings(m: Message):
    chat_id = m.chat.id
    game = ensure_game(chat_id)
    if not game:
        await m.answer("Игра не найдена. Сначала /newgame")
        return
    await m.answer("⚙️ <b>Настройки</b> (только хост может менять):", reply_markup=settings_keyboard(game))

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
    await cancel_timer(game)
    GAMES.pop(chat_id, None)
    await m.answer("🏁 Игра завершена. Спасибо за игру!")

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
    if any(p.user_id == c.from_user.id for p in game.players):
        await c.answer("Ты уже в игре 😉", show_alert=True); return
    game.players.append(Player(c.from_user.id, c.from_user.full_name))
    game.scores.setdefault(c.from_user.id, 0)
    await update_lobby_message(c.message, game)
    await c.answer("Готово!")

@dp.callback_query(F.data == "leave")
async def cb_leave(c: CallbackQuery):
    chat_id = c.message.chat.id
    game = ensure_game(chat_id)
    if not game:
        await c.answer("Игра не найдена.", show_alert=True); return
    game.players = [p for p in game.players if p.user_id != c.from_user.id]
    await update_lobby_message(c.message, game)
    await c.answer("Пока!")

async def update_lobby_message(msg: Message, game: ChatGame):
    names = ", ".join(mention_html(p.user_id, p.name) for p in game.players) or "—"
    await msg.edit_text(
        f"🧩 Лобби. Хост: {mention_html(game.host_id, 'Host')}\n"
        f"Игроки: {names}\n\n"
        f"Хост может нажать <b>Старт</b>, когда все готовы.",
        reply_markup=lobby_keyboard(game)
    )

@dp.callback_query(F.data == "start")
async def cb_start(c: CallbackQuery):
    chat_id = c.message.chat.id
    game = ensure_game(chat_id)
    if not game:
        await c.answer("Игра не найдена.", show_alert=True); return
    if not is_host(game, c.from_user.id):
        await c.answer("Только хост может начать.", show_alert=True); return
    if len(game.players) < 1:
        await c.answer("Нужно минимум 1 игрок.", show_alert=True); return

    game.in_progress = True
    game.current_idx = -1
    await c.message.edit_text("🎲 Игра началась!")
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
    await tmp.edit_text(f"👉 Ход игрока: <b>{pl.name}</b> ({len(game.players)} игроков)")

    # сообщение с выбором
    keyboard = turn_choice_keyboard(game, show_end=is_host(game, game.host_id))
    sent = await msg.answer(
        f"{mention_html(pl.user_id, pl.name)}, выбери <b>Правда</b> или <b>Действие</b>.",
        reply_markup=keyboard
    )
    game.current_turn = Turn(player_id=pl.user_id, message_id=sent.message_id)

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
    card = pick_card(game, kind)
    if not card:
        await c.answer("Карточек не осталось.", show_alert=True); return

    game.used_ids.add(card["id"])
    turn.type = kind
    turn.card_id = card["id"]

    # Показ задания
    try:
        await c.message.edit_text(
            f"👉 <b>Ход:</b> {mention_html(turn.player_id, 'Игрок')}\n"
            f"{'🟦 Правда' if kind=='truth' else '🟥 Действие'}:\n"
            f"{card['text']}",
            reply_markup=task_keyboard(game, for_host=is_host(game, c.from_user.id))
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
    if game.settings["skip_penalty"] == -1 and game.settings["points"] and game.current_turn:
        uid = game.current_turn.player_id
        game.scores[uid] = game.scores.get(uid, 0) - 1
    await bot.send_message(chat_id, f"{reason}")
    await proceed_next(chat_id)

@dp.callback_query(F.data == "done")
async def cb_done(c: CallbackQuery):
    chat_id = c.message.chat.id
    game = ensure_game(chat_id)
    if not game or not game.current_turn:
        await c.answer("Нет активного задания.", show_alert=True); return
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
    turn = game.current_turn

    # Очки
    if game.settings["points"] and turn.player_id:
        game.scores.setdefault(turn.player_id, 0)
        if success:
            game.scores[turn.player_id] += 1

    await bot.send_message(chat_id, f"{by}. "
                                    f"{'Очко начислено.' if success and game.settings['points'] else 'Очки без изменений.'}")
    game.vote = None
    await proceed_next(chat_id)

async def proceed_next(chat_id: int):
    game = ensure_game(chat_id)
    if not game: return
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
    await cancel_timer(game)
    GAMES.pop(chat_id, None)
    await c.message.answer("🏁 Игра завершена. Спасибо за игру!")
    await c.answer()

# ====== SETTINGS ======

@dp.callback_query(F.data == "settings")
async def cb_settings(c: CallbackQuery):
    game = ensure_game(c.message.chat.id)
    if not game:
        await c.answer("Игра не найдена.", show_alert=True); return
    await c.message.answer("⚙️ <b>Настройки</b> (только хост может менять):", reply_markup=settings_keyboard(game))
    await c.answer()

@dp.callback_query(F.data.startswith("timer:"))
async def cb_timer(c: CallbackQuery):
    game = ensure_game(c.message.chat.id)
    if not game: return
    if not is_host(game, c.from_user.id):
        await c.answer("Только хост может менять настройки.", show_alert=True); return
    val = int(c.data.split(":")[1])
    game.settings["timer"] = val
    await c.message.edit_reply_markup(settings_keyboard(game))
    await c.answer(f"Таймер: {val if val>0 else 'Off'}")

@dp.callback_query(F.data == "points:toggle")
async def cb_points(c: CallbackQuery):
    game = ensure_game(c.message.chat.id)
    if not game: return
    if not is_host(game, c.from_user.id):
        await c.answer("Только хост может менять.", show_alert=True); return
    game.settings["points"] = not game.settings["points"]
    await c.message.edit_reply_markup(settings_keyboard(game))
    await c.answer("Готово.")

@dp.callback_query(F.data == "penalty:toggle")
async def cb_penalty(c: CallbackQuery):
    game = ensure_game(c.message.chat.id)
    if not game: return
    if not is_host(game, c.from_user.id):
        await c.answer("Только хост может менять.", show_alert=True); return
    game.settings["skip_penalty"] = -1 if game.settings["skip_penalty"] == 0 else 0
    await c.message.edit_reply_markup(settings_keyboard(game))
    await c.answer("Готово.")

@dp.callback_query(F.data.startswith("age:"))
async def cb_age(c: CallbackQuery):
    game = ensure_game(c.message.chat.id)
    if not game: return
    if not is_host(game, c.from_user.id):
        await c.answer("Только хост может менять.", show_alert=True); return
    a = c.data.split(":")[1]
    if a in game.settings["age"]:
        game.settings["age"].remove(a)
    else:
        game.settings["age"].add(a)
    if not game.settings["age"]:  # минимум один уровень
        game.settings["age"].add(a)
    await c.message.edit_reply_markup(settings_keyboard(game))
    await c.answer("Готово.")

@dp.callback_query(F.data.startswith("cat:"))
async def cb_cat(c: CallbackQuery):
    game = ensure_game(c.message.chat.id)
    if not game: return
    if not is_host(game, c.from_user.id):
        await c.answer("Только хост может менять.", show_alert=True); return
    cat = c.data.split(":")[1]
    if cat in game.settings["categories"]:
        game.settings["categories"].remove(cat)
    else:
        game.settings["categories"].add(cat)
    if not game.settings["categories"]:
        game.settings["categories"].add(cat)
    await c.message.edit_reply_markup(settings_keyboard(game))
    await c.answer("Готово.")

@dp.callback_query(F.data == "back")
async def cb_back(c: CallbackQuery):
    # Просто закрываем меню настроек
    try:
        await c.message.delete()
    except Exception:
        pass
    await c.answer()

# ===========================
# MAIN
# ===========================

async def main():
    print("✅ Bot is running...")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    asyncio.run(main())
