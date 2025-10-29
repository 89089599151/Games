
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
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
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

    # 18+ — только для взрослых компаний
    {"id":"adult-t-01","type":"truth","category":"Романтика","age":"18+","tags":["романтика"],"text":"🔥 Какая смелая мечта у тебя для идеального свидания?"},
    {"id":"adult-t-02","type":"truth","category":"Жесть","age":"18+","tags":["откровенно"],"text":"🔥 Назови поступок, которым гордишься, хотя он был безумным."},
    {"id":"adult-d-01","type":"dare","category":"Романтика","age":"18+","tags":["игра"],"text":"🔥 Сочини пикантный, но уважительный комплимент для любого игрока."},
    {"id":"adult-d-02","type":"dare","category":"Жесть","age":"18+","tags":["вызов"],"text":"🔥 Расскажи забавную взрослую историю без лишних подробностей."}
]

TIMER_OPTIONS = [0, 20, 30, 45]

AGE_LEVELS = ["0+", "12+", "16+", "18+"]
AGE_ICONS = {
    "0+": "🧒",
    "12+": "🧑",
    "16+": "⚠️",
    "18+": "🔥",
}

CATEGORIES = ["Лёгкое", "Друзья", "Романтика", "Жесть"]

HELP_TEXT = (
    "ℹ️ <b>Правила</b>\n"
    "Создай лобби через /newgame — ты станешь 👑 хостом и автоматически попадёшь в список игроков.\n"
    "Пригласи друзей: они жмут кнопку «Присоединиться» или команду /join. Выйти — /leave.\n"
    "Как только готовы, нажми «Старт» — бот покажет, кому ходить и выдаст карточку.\n\n"
    "<b>Панель управления</b>\n"
    "• ⏱️ Настрой таймер (0 = выкл.).\n"
    "• 👶 Выбери возрастной уровень (добавлена категория 🔥 18+).\n"
    "• 🗂️ Ограничь категории вопросов.\n"
    "• ⚙️ В разделе «Другое» включи очки и штраф за пропуск.\n\n"
    "<b>Команды</b>\n"
    "/newgame — создать новое лобби\n"
    "/join — присоединиться к текущей игре\n"
    "/leave — покинуть игру\n"
    "/score — показать счёт (если очки включены)\n"
    "/settings — открыть панель настроек\n"
    "/end — завершить игру\n"
    "/help — эта справка\n\n"
    "Побеждает тот, кто соберёт больше очков — удачи!"
)

DEFAULT_SETTINGS = {
    "timer": 30,
    "points": True,
    "skip_penalty": 0,
    "age": {AGE_LEVELS[0]},
    "categories": {CATEGORIES[0]},
}

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
    settings: Dict = field(default_factory=lambda: deepcopy(DEFAULT_SETTINGS))
    current_turn: Optional[Turn] = None
    timer_task: Optional[asyncio.Task] = None
    vote: Optional[VoteState] = None
    extra_deck: List[Dict] = field(default_factory=list)  # пользовательские элементы
    settings_message_id: Optional[int] = None
    rounds_played: int = 0
    lobby_message_id: Optional[int] = None

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


def player_prefix(game: ChatGame, user_id: int) -> str:
    return HOST_ICON if is_host(game, user_id) else PLAYER_ICON


def format_player_mention(game: ChatGame, player: Player) -> str:
    return f"{player_prefix(game, player.user_id)} {mention_html(player.user_id, player.name)}"


def ensure_score_cleanup(game: ChatGame) -> None:
    active_ids = {p.user_id for p in game.players}
    for uid in list(game.scores.keys()):
        if uid not in active_ids:
            game.scores.pop(uid, None)


def add_player(game: ChatGame, user_id: int, name: str) -> bool:
    if any(p.user_id == user_id for p in game.players):
        return False
    game.players.append(Player(user_id, name))
    game.scores.setdefault(user_id, 0)
    return True


def remove_player(game: ChatGame, user_id: int) -> bool:
    initial = len(game.players)
    game.players = [p for p in game.players if p.user_id != user_id]
    removed = len(game.players) != initial
    if removed:
        game.scores.pop(user_id, None)
        ensure_score_cleanup(game)
    return removed


def is_host(game: ChatGame, user_id: int) -> bool:
    return game.host_id == user_id


def apply_membership_change(game: ChatGame, user_id: int, name: str, join: bool) -> Tuple[bool, str]:
    if join:
        if not add_player(game, user_id, name):
            return False, "Ты уже в списке игроков."
        return True, f"{PLAYER_ICON} {mention_html(user_id, name)} присоединился к игре."

    if is_host(game, user_id):
        return False, "Хост не может выйти — заверши игру командой /end."

    if not remove_player(game, user_id):
        return False, "Тебя и так нет в списке игроков."

    return True, "Ты покинул игру. До встречи!"


def prepare_scoreboard(game: ChatGame, title: str = "📊 Счёт") -> Tuple[bool, str]:
    if not game.settings.get("points"):
        return False, "🏅 Подсчёт очков отключён в настройках."

    ensure_score_cleanup(game)
    if not game.scores:
        return False, "Пока никто не заработал очков — сыграйте раунд!"

    ordered = sorted(game.scores.items(), key=lambda kv: kv[1], reverse=True)
    lines = []
    for idx, (uid, score) in enumerate(ordered, start=1):
        player = next((p for p in game.players if p.user_id == uid), Player(uid, f"Игрок {uid}"))
        lines.append(f"{idx}. {format_player_mention(game, player)} — <b>{score}</b>")

    return True, f"{title}:\n" + "\n".join(lines)


async def conclude_game(game: ChatGame, reason: str) -> None:
    await cancel_timer(game)

    if game.vote and game.vote.message_id:
        try:
            await bot.edit_message_reply_markup(
                chat_id=game.chat_id,
                message_id=game.vote.message_id,
                reply_markup=None,
            )
        except TelegramBadRequest:
            pass
    game.vote = None
    game.current_turn = None

    await close_settings_panel(game.chat_id, game)

    parts = [f"🏁 {reason}"]
    if game.settings.get("points"):
        if game.rounds_played > 0:
            ok, score_text = prepare_scoreboard(game, title="🏅 Итоговый счёт")
            if ok:
                parts.append(score_text)
            else:
                parts.append("🏅 Очков пока нет — сыграйте ещё раз!")
        else:
            parts.append("Раунды так и не начались — очков нет.")
    else:
        parts.append("🏅 Подсчёт очков был отключён.")

    GAMES.pop(game.chat_id, None)
    game.in_progress = False
    game.lobby_message_id = None
    await bot.send_message(game.chat_id, "\n\n".join(parts))


async def request_game_end(chat_id: int, user_id: int) -> Tuple[bool, str]:
    game = ensure_game(chat_id)
    if not game:
        return False, "Игра не найдена."
    if not is_host(game, user_id):
        return False, "Только хост может завершить игру."

    await conclude_game(game, "Игра завершена по решению хоста.")
    return True, "Игра завершена."

def get_deck_for_game(game: ChatGame) -> List[Dict]:
    # фильтр по возрасту/категориям
    allowed_age = game.settings["age"]
    allowed_cat = game.settings["categories"]
    deck = [c for c in (DEFAULT_DECK + game.extra_deck)
            if c.get("age") in allowed_age and c.get("category") in allowed_cat]
    return deck


def lobby_summary(game: ChatGame) -> str:
    host_player = next((p for p in game.players if p.user_id == game.host_id), None)
    host_name = host_player.name if host_player else "Неизвестно"
    host_line = f"{HOST_ICON} Хост: {mention_html(game.host_id, host_name)}"

    if game.players:
        players_lines = "\n".join(
            f"• {format_player_mention(game, p)}" for p in game.players
        )
    else:
        players_lines = "• Пока нет игроков."

    return (
        "🧩 <b>Лобби игры</b>\n"
        f"{host_line}\n\n"
        "<b>Участники</b>:\n"
        f"{players_lines}\n\n"
        "Хост может нажать «Старт», когда все готовы."
    )


def pick_card(game: ChatGame, kind: str) -> Tuple[Optional[Dict], bool]:
    deck = [
        c
        for c in get_deck_for_game(game)
        if c.get("type") == kind and c.get("id") not in game.used_ids
    ]
    if deck:
        return random.choice(deck), False

    # Сбрасываем использованные и пытаемся снова
    game.used_ids.clear()
    refreshed = [c for c in get_deck_for_game(game) if c.get("type") == kind]
    if not refreshed:
        return None, False
    return random.choice(refreshed), True

def lobby_keyboard(game: ChatGame) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="➕ Присоединиться", callback_data="join"),
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

CATEGORY_ICONS = {
    "Лёгкое": "🌱",
    "Друзья": "👥",
    "Романтика": "💞",
    "Жесть": "💥",
}

HOST_ICON = "👑"
PLAYER_ICON = "🎲"


def _inline_back_button() -> InlineKeyboardButton:
    return InlineKeyboardButton(text="⬅️ Назад", callback_data="settings:menu:main")


def _mark_selected(is_selected: bool) -> str:
    return "✅" if is_selected else "▫️"


def _timer_option_text(value: int, current: int) -> str:
    label = "Выключен" if value == 0 else f"{value} сек."
    return f"{_mark_selected(current == value)} ⏱️ {label}"


def _age_option_text(value: str, current: Set[str]) -> str:
    icon = AGE_ICONS.get(value, "👶")
    return f"{_mark_selected(value in current)} {icon} {value}"


def _category_option_text(value: str, current: Set[str]) -> str:
    icon = CATEGORY_ICONS.get(value, "🗂️")
    return f"{_mark_selected(value in current)} {icon} {value}"


def _other_options(game: ChatGame) -> List[InlineKeyboardButton]:
    points_text = f"{_mark_selected(game.settings['points'])} 🏅 Очки"
    penalty_on = game.settings["skip_penalty"] == -1
    penalty_text = f"{_mark_selected(penalty_on)} ⚠️ Штраф -1"
    return [
        InlineKeyboardButton(text=points_text, callback_data="settings:toggle:points"),
        InlineKeyboardButton(text=penalty_text, callback_data="settings:toggle:penalty"),
    ]


SETTINGS_CHOICES = {
    "timer": {
        "options": TIMER_OPTIONS,
        "per_row": 2,
        "builder": lambda game, value: _timer_option_text(value, game.settings["timer"]),
    },
    "age": {
        "options": AGE_LEVELS,
        "per_row": 2,
        "builder": lambda game, value: _age_option_text(value, game.settings["age"]),
    },
    "category": {
        "options": CATEGORIES,
        "per_row": 2,
        "builder": lambda game, value: _category_option_text(value, game.settings["categories"]),
    },
}


def _build_choice_menu(key: str, game: ChatGame) -> InlineKeyboardMarkup:
    schema = SETTINGS_CHOICES[key]
    per_row = schema["per_row"]
    rows: List[List[InlineKeyboardButton]] = []
    options = schema["options"]
    for i in range(0, len(options), per_row):
        chunk = options[i : i + per_row]
        rows.append([
            InlineKeyboardButton(
                text=schema["builder"](game, value),
                callback_data=f"settings:set:{key}:{value}",
            )
            for value in chunk
        ])
    rows.append([_inline_back_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_main_menu(game: ChatGame) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="⏱️ Время", callback_data="settings:menu:timer"),
            InlineKeyboardButton(text="👶 Возраст", callback_data="settings:menu:age"),
        ],
        [InlineKeyboardButton(text="🗂️ Категории", callback_data="settings:menu:category")],
        [InlineKeyboardButton(text="⚙️ Другое", callback_data="settings:menu:other")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="settings:close")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_other_menu(game: ChatGame) -> InlineKeyboardMarkup:
    rows = [[btn] for btn in _other_options(game)]
    rows.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="settings:close")])
    rows.append([_inline_back_button()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


SETTINGS_MENU_BUILDERS = {
    "main": _build_main_menu,
    "timer": lambda game: _build_choice_menu("timer", game),
    "age": lambda game: _build_choice_menu("age", game),
    "category": lambda game: _build_choice_menu("category", game),
    "other": _build_other_menu,
}


def settings_keyboard(game: ChatGame, menu: str = "main") -> InlineKeyboardMarkup:
    builder = SETTINGS_MENU_BUILDERS.get(menu, SETTINGS_MENU_BUILDERS["main"])
    return builder(game)


def _apply_timer(game: ChatGame, raw: str) -> Tuple[bool, str, bool]:
    try:
        value = int(raw)
    except ValueError:
        return False, "Некорректное значение таймера.", True
    if value not in TIMER_OPTIONS:
        return False, "Нет такого варианта таймера.", True
    if game.settings["timer"] == value:
        label = "выключен" if value == 0 else f"{value} сек."
        return False, f"Таймер уже {label}.", False
    game.settings["timer"] = value
    label = "выключен" if value == 0 else f"{value} сек."
    return True, f"⏱️ Таймер: {label}", False


def _apply_age(game: ChatGame, raw: str) -> Tuple[bool, str, bool]:
    if raw not in AGE_LEVELS:
        return False, "Неизвестный возрастной уровень.", True
    if game.settings["age"] == {raw}:
        return False, "Этот возраст уже выбран.", False
    game.settings["age"] = {raw}
    icon = AGE_ICONS.get(raw, "👶")
    return True, f"Возраст: {icon} {raw}", False


def _apply_category(game: ChatGame, raw: str) -> Tuple[bool, str, bool]:
    if raw not in CATEGORIES:
        return False, "Неизвестная категория.", True
    if game.settings["categories"] == {raw}:
        return False, "Эта категория уже активна.", False
    game.settings["categories"] = {raw}
    icon = CATEGORY_ICONS.get(raw, "🗂️")
    return True, f"Категория: {icon} {raw}", False


SETTING_APPLIERS = {
    "timer": _apply_timer,
    "age": _apply_age,
    "category": _apply_category,
}


def _toggle_points(game: ChatGame) -> Tuple[bool, str]:
    game.settings["points"] = not game.settings["points"]
    state = "включены" if game.settings["points"] else "выключены"
    return True, f"🏅 Очки {state}"


def _toggle_penalty(game: ChatGame) -> Tuple[bool, str]:
    game.settings["skip_penalty"] = -1 if game.settings["skip_penalty"] == 0 else 0
    state = "-1" if game.settings["skip_penalty"] == -1 else "0"
    return True, f"⚠️ Штраф {state}"


SETTINGS_TOGGLES = {
    "points": _toggle_points,
    "penalty": _toggle_penalty,
}


def _settings_summary(game: ChatGame) -> str:
    timer = f"{game.settings['timer']} сек." if game.settings["timer"] > 0 else "выключен"
    points = "включены" if game.settings["points"] else "выключены"
    penalty = "-1" if game.settings["skip_penalty"] == -1 else "0"
    age = ", ".join(
        f"{AGE_ICONS.get(level, '👶')} {level}" for level in sorted(game.settings["age"])
    )
    categories = ", ".join(
        f"{CATEGORY_ICONS.get(cat, '🗂️')} {cat}" for cat in sorted(game.settings["categories"])
    )
    return (
        "⚙️ <b>Настройки</b> (только хост может менять):\n"
        f"⏱️ Таймер: <b>{timer}</b>\n"
        f"🏅 Очки: <b>{points}</b>\n"
        f"⚠️ Штраф: <b>{penalty}</b>\n"
        f"👶 Возраст: <b>{age}</b>\n"
        f"🗂️ Категории: <b>{categories}</b>"
    )


async def update_settings_panel(
    chat_id: int,
    game: ChatGame,
    menu: str = "main",
    info: Optional[str] = None,
):
    text = _settings_summary(game)
    if info:
        text = f"{info}\n\n{text}"

    markup = settings_keyboard(game, menu)

    if game.settings_message_id:
        try:
            await bot.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=game.settings_message_id,
                reply_markup=markup,
            )
            return
        except TelegramBadRequest as e:
            if "message is not modified" in str(e).lower():
                return
            try:
                await bot.delete_message(chat_id, game.settings_message_id)
            except TelegramBadRequest:
                pass

    sent = await bot.send_message(chat_id, text, reply_markup=markup)
    game.settings_message_id = sent.message_id


async def close_settings_panel(chat_id: int, game: Optional[ChatGame], info: Optional[str] = None):
    if game and game.settings_message_id:
        try:
            await bot.delete_message(chat_id, game.settings_message_id)
        except TelegramBadRequest:
            pass
        game.settings_message_id = None

    if info:
        await bot.send_message(chat_id, info)


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
        "Создай лобби через /newgame — ты сразу станешь 👑 хостом и попадёшь в список игроков.\n"
        "Пригласи друзей: они жмут кнопку «Присоединиться» или команду /join.\n\n"
        "ℹ️ Полное описание правил и команд — в /help."
    )


@dp.message(Command("help"))
@dp.message(Command("info"))
async def cmd_help(m: Message):
    await m.answer(HELP_TEXT)

@dp.message(Command("newgame"))
async def cmd_newgame(m: Message):
    chat_id = m.chat.id
    user_id = m.from_user.id

    # Прерываем предыдущую игру в чате (если была)
    if chat_id in GAMES:
        await cancel_timer(GAMES[chat_id])
        await close_settings_panel(chat_id, GAMES[chat_id])

    game = ChatGame(chat_id=chat_id, host_id=user_id)
    add_player(game, user_id, m.from_user.full_name)
    GAMES[chat_id] = game

    sent = await m.answer(lobby_summary(game), reply_markup=lobby_keyboard(game))
    game.lobby_message_id = sent.message_id

@dp.message(Command("join"))
async def cmd_join(m: Message):
    chat_id = m.chat.id
    game = ensure_game(chat_id)
    if not game:
        await m.answer("Лобби ещё не создано. Используйте /newgame")
        return
    changed, info = apply_membership_change(game, m.from_user.id, m.from_user.full_name, join=True)
    await m.answer(info)
    if changed:
        await refresh_lobby_panel(game)

@dp.message(Command("leave"))
async def cmd_leave(m: Message):
    chat_id = m.chat.id
    game = ensure_game(chat_id)
    if not game:
        await m.answer("Игра не найдена.")
        return
    changed, info = apply_membership_change(game, m.from_user.id, m.from_user.full_name, join=False)
    await m.answer(info)
    if changed:
        await refresh_lobby_panel(game)

@dp.message(Command("score"))
async def cmd_score(m: Message):
    chat_id = m.chat.id
    game = ensure_game(chat_id)
    if not game:
        await m.answer("Игра не найдена.")
        return
    _, text = prepare_scoreboard(game)
    await m.answer(text)

@dp.message(Command("settings"))
async def cmd_settings(m: Message):
    chat_id = m.chat.id
    game = ensure_game(chat_id)
    if not game:
        await m.answer("Игра не найдена. Сначала /newgame")
        return
    await update_settings_panel(chat_id, game)

@dp.message(Command("end"))
async def cmd_end(m: Message):
    chat_id = m.chat.id
    ok, info = await request_game_end(chat_id, m.from_user.id)
    if ok:
        await m.answer("🏁 Финальный отчёт отправлен.")
    else:
        await m.answer(info)

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
        await c.answer("Сначала /newgame", show_alert=True)
        return

    changed, info = apply_membership_change(game, c.from_user.id, c.from_user.full_name, join=True)
    if not changed:
        await c.answer(info, show_alert=True)
        return

    await update_lobby_message(c.message, game)
    await c.answer("Готово! 😊")

@dp.callback_query(F.data == "leave")
async def cb_leave(c: CallbackQuery):
    chat_id = c.message.chat.id
    game = ensure_game(chat_id)
    if not game:
        await c.answer("Игра не найдена.", show_alert=True)
        return

    changed, info = apply_membership_change(game, c.from_user.id, c.from_user.full_name, join=False)
    if not changed:
        await c.answer(info, show_alert=True)
        return

    await update_lobby_message(c.message, game)
    await c.answer("До встречи! 👋")

async def update_lobby_message(msg: Message, game: ChatGame):
    game.lobby_message_id = msg.message_id
    await msg.edit_text(lobby_summary(game), reply_markup=lobby_keyboard(game))


async def refresh_lobby_panel(game: ChatGame) -> None:
    if not game.lobby_message_id:
        return
    try:
        await bot.edit_message_text(
            text=lobby_summary(game),
            chat_id=game.chat_id,
            message_id=game.lobby_message_id,
            reply_markup=lobby_keyboard(game),
        )
    except TelegramBadRequest as e:
        if "message to edit not found" in str(e).lower():
            game.lobby_message_id = None

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
    game.rounds_played = 0
    await c.message.edit_text("🎲 Игра началась! Удачи всем игрокам!")
    game.lobby_message_id = None
    await next_turn(c.message, game)
    await c.answer("Поехали! 🚀")

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
    await tmp.edit_text(f"👉 Ход игрока: {format_player_mention(game, pl)} ({len(game.players)} игроков)")

    # сообщение с выбором
    keyboard = turn_choice_keyboard(game, show_end=is_host(game, game.host_id))
    sent = await msg.answer(
        f"{format_player_mention(game, pl)}, выбери <b>Правда</b> или <b>Действие</b>.",
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
    card, restarted = pick_card(game, kind)
    if card is None:
        await c.answer("Карточек не осталось.", show_alert=True)
        await conclude_game(game, "Колода заданий закончилась.")
        return

    if restarted:
        await bot.send_message(chat_id, "♻️ Колода исчерпана — перемешиваю заново!")

    game.used_ids.add(card["id"])
    turn.type = kind
    turn.card_id = card["id"]

    # Показ задания
    player_obj = next((p for p in game.players if p.user_id == turn.player_id), Player(turn.player_id, "Игрок"))
    badge_type = "🟦 Правда" if kind == "truth" else "🟥 Действие"
    badge_cat = CATEGORY_ICONS.get(card.get("category"), "🗂️")
    badge_age = AGE_ICONS.get(card.get("age"), "👶")
    try:
        await c.message.edit_text(
            "\n".join(
                [
                    f"👉 <b>Ход:</b> {format_player_mention(game, player_obj)}",
                    f"{badge_cat} Категория: <b>{card.get('category', '—')}</b> | {badge_age} Возраст: <b>{card.get('age', '—')}</b>",
                    f"{badge_type}:",
                    card.get("text", "—"),
                ]
            ),
            reply_markup=task_keyboard(game, for_host=is_host(game, c.from_user.id))
        )
    except Exception:
        pass

    # Запускаем таймер на выполнение
    async def on_expire():
        # если к этому моменту голосование/завершение не произошло — автопропуск
        await handle_skip(chat_id, reason="⏱️ Время вышло — задание не выполнено.")
    await start_timer(game, game.settings["timer"], on_expire)
    await c.answer()

@dp.callback_query(F.data == "skip")
async def cb_skip(c: CallbackQuery):
    await c.answer()
    await handle_skip(c.message.chat.id, reason="🔁 Пропуск: задание отменено.")

async def handle_skip(chat_id: int, reason: str):
    game = ensure_game(chat_id)
    if not game: return
    await cancel_timer(game)
    # штраф при настройке
    penalty_note = ""
    if game.settings["skip_penalty"] == -1 and game.settings["points"] and game.current_turn:
        uid = game.current_turn.player_id
        game.scores[uid] = game.scores.get(uid, 0) - 1
        penalty_note = " (штраф -1 очко)"
    if game.current_turn:
        game.rounds_played += 1
    await bot.send_message(chat_id, f"{reason}{penalty_note}")
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
    if not game or not game.current_turn:
        return
    turn = game.current_turn

    if game.settings["points"] and turn.player_id:
        game.scores.setdefault(turn.player_id, 0)
        if success:
            game.scores[turn.player_id] += 1

    game.rounds_played += 1

    if game.vote and game.vote.message_id:
        status = "✅ Засчитано" if success else "❌ Не засчитано"
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=game.vote.message_id,
                text=f"🗳️ Голосование завершено: {status}\n{by}",
            )
        except TelegramBadRequest:
            pass
    game.vote = None

    result_line = "✅ Задание засчитано!" if success else "❌ Задание не зачтено."
    points_line = ""
    if game.settings["points"]:
        if success:
            points_line = " Очко начислено."
        else:
            points_line = " Очки без изменений."

    await bot.send_message(chat_id, f"{result_line} {by}.{points_line}")
    await proceed_next(chat_id)

async def proceed_next(chat_id: int):
    game = ensure_game(chat_id)
    if not game: return
    game.current_turn = None
    await next_turn(await bot.send_message(chat_id, "▶️ Следующий ход..."), game)

@dp.callback_query(F.data == "end")
async def cb_end(c: CallbackQuery):
    chat_id = c.message.chat.id
    ok, info = await request_game_end(chat_id, c.from_user.id)
    if ok:
        await c.answer("Игра завершена ✅")
    else:
        await c.answer(info, show_alert=True)

# ====== SETTINGS ======

@dp.callback_query(F.data == "settings")
async def cb_settings(c: CallbackQuery):
    game = ensure_game(c.message.chat.id)
    if not game:
        await c.answer("Игра не найдена.", show_alert=True); return
    await update_settings_panel(c.message.chat.id, game)
    await c.answer()


def _callback_game(c: CallbackQuery) -> Optional[ChatGame]:
    message = c.message
    if not message:
        return None
    return ensure_game(message.chat.id)


async def _ensure_host(c: CallbackQuery, game: ChatGame) -> bool:
    if not is_host(game, c.from_user.id):
        await c.answer("Только хост может менять настройки.", show_alert=True)
        return False
    return True


@dp.callback_query(F.data.startswith("settings:menu:"))
async def cb_settings_menu(c: CallbackQuery):
    game = _callback_game(c)
    if not game:
        await c.answer("Игра не найдена.", show_alert=True)
        return
    menu = c.data.split(":", 2)[2]
    await update_settings_panel(c.message.chat.id, game, menu=menu)
    await c.answer()


@dp.callback_query(F.data == "settings:close")
async def cb_settings_close(c: CallbackQuery):
    game = _callback_game(c)
    if not game:
        await c.answer()
        return
    if not await _ensure_host(c, game):
        return
    await close_settings_panel(c.message.chat.id, game, info="⚙️ Панель настроек закрыта.")
    await c.answer()


@dp.callback_query(F.data.startswith("settings:set:"))
async def cb_settings_set(c: CallbackQuery):
    game = _callback_game(c)
    if not game:
        await c.answer("Игра не найдена.", show_alert=True)
        return
    if not await _ensure_host(c, game):
        return

    try:
        _, _, key, raw_value = c.data.split(":", 3)
    except ValueError:
        await c.answer("Некорректные данные.", show_alert=True)
        return

    handler = SETTING_APPLIERS.get(key)
    if not handler:
        await c.answer("Неизвестная настройка.", show_alert=True)
        return

    changed, message, is_error = handler(game, raw_value)
    if is_error:
        await c.answer(message, show_alert=True)
        return

    await update_settings_panel(c.message.chat.id, game, menu=key, info=message if changed else None)
    await c.answer(message)


@dp.callback_query(F.data.startswith("settings:toggle:"))
async def cb_settings_toggle(c: CallbackQuery):
    game = _callback_game(c)
    if not game:
        await c.answer("Игра не найдена.", show_alert=True)
        return
    if not await _ensure_host(c, game):
        return

    key = c.data.rsplit(":", 1)[1]
    handler = SETTINGS_TOGGLES.get(key)
    if not handler:
        await c.answer("Неизвестная настройка.", show_alert=True)
        return

    _, message = handler(game)
    await update_settings_panel(c.message.chat.id, game, menu="other", info=message)
    await c.answer(message)

# ===========================
# MAIN
# ===========================

async def main():
    print("✅ Bot is running...")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    asyncio.run(main())
