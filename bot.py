"""Truth or Dare offline host bot."""

import asyncio
import os
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from aiogram import Bot, Dispatcher, F
# Aiogram 3.7+ предоставляет DefaultBotProperties, но в 3.2 его нет,
# поэтому импортируем с запасным вариантом для обратной совместимости.
try:
    from aiogram.client.default import DefaultBotProperties
except ImportError:  # aiogram<=3.6
    DefaultBotProperties = None  # type: ignore[assignment]
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise SystemExit(
        "❌ BOT_TOKEN не найден. Установите переменную окружения, например:\n"
        "BOT_TOKEN=123:ABC python bot.py"
    )

AGE_LEVELS = ["0+", "12+", "16+", "18+"]
AGE_ICONS = {
    "0+": "🧒",
    "12+": "🧑",
    "16+": "⚠️",
    "18+": "🔥",
}
AGE_ORDER = {age: index for index, age in enumerate(AGE_LEVELS)}

CATEGORIES = {
    "Лёгкое": "🎈",
    "Друзья": "🤝",
    "Романтика": "💘",
    "Жесть": "💥",
}

DEFAULT_DECK: List[Dict[str, str]] = [
    {"id": "light-truth-01", "type": "truth", "category": "Лёгкое", "age": "0+", "text": "Какой мем последнее время смешит тебя больше всего?"},
    {"id": "light-truth-02", "type": "truth", "category": "Лёгкое", "age": "0+", "text": "Назови занятие, которое всегда поднимает тебе настроение."},
    {"id": "light-truth-03", "type": "truth", "category": "Лёгкое", "age": "12+", "text": "Если бы ты мог моментально выучить любой навык, что бы это было?"},
    {"id": "light-dare-01", "type": "dare", "category": "Лёгкое", "age": "0+", "text": "Изобрази на 10 секунд героя любимого мультфильма."},
    {"id": "light-dare-02", "type": "dare", "category": "Лёгкое", "age": "0+", "text": "Скажи три комплимента людям рядом, не повторяясь."},
    {"id": "light-dare-03", "type": "dare", "category": "Лёгкое", "age": "12+", "text": "Придумай смешную подпись для ближайшего предмета."},
    {"id": "friends-truth-01", "type": "truth", "category": "Друзья", "age": "0+", "text": "Кто из этой компании умудряется тебя удивлять чаще всего?"},
    {"id": "friends-truth-02", "type": "truth", "category": "Друзья", "age": "12+", "text": "Какой общий момент из прошлого ты бы повторил прямо сейчас?"},
    {"id": "friends-truth-03", "type": "truth", "category": "Друзья", "age": "16+", "text": "Что тебе легче – попросить помощь или предложить её первым?"},
    {"id": "friends-dare-01", "type": "dare", "category": "Друзья", "age": "0+", "text": "Сочини смешной командный девиз и произнеси его вслух."},
    {"id": "friends-dare-02", "type": "dare", "category": "Друзья", "age": "12+", "text": "Сделай мини-тост за дружбу на 15 секунд."},
    {"id": "friends-dare-03", "type": "dare", "category": "Друзья", "age": "16+", "text": "Придумай новый общий ритуал для всей компании."},
    {"id": "romance-truth-01", "type": "truth", "category": "Романтика", "age": "12+", "text": "Какой милый жест всегда вызывает у тебя улыбку?"},
    {"id": "romance-truth-02", "type": "truth", "category": "Романтика", "age": "16+", "text": "Что ты ценишь в романтических моментах больше всего?"},
    {"id": "romance-truth-03", "type": "truth", "category": "Романтика", "age": "18+", "text": "🔥 Расскажи о самом смелом свидании, которое ты хотел бы устроить."},
    {"id": "romance-dare-01", "type": "dare", "category": "Романтика", "age": "12+", "text": "Скажи нежный комплимент человеку слева."},
    {"id": "romance-dare-02", "type": "dare", "category": "Романтика", "age": "16+", "text": "Опиши идеальный вечер на двоих в трёх фразах."},
    {"id": "romance-dare-03", "type": "dare", "category": "Романтика", "age": "18+", "text": "🔥 Придумай пикантное, но уважительное послание для любого игрока."},
    {"id": "extreme-truth-01", "type": "truth", "category": "Жесть", "age": "16+", "text": "Расскажи о моменте, когда пришлось выйти из зоны комфорта."},
    {"id": "extreme-truth-02", "type": "truth", "category": "Жесть", "age": "18+", "text": "🔥 Какой рискованный поступок ты до сих пор вспоминаешь с улыбкой?"},
    {"id": "extreme-truth-03", "type": "truth", "category": "Жесть", "age": "18+", "text": "🔥 Есть ли мечта, на которую ты пока не решаешься?"},
    {"id": "extreme-dare-01", "type": "dare", "category": "Жесть", "age": "16+", "text": "Сделай решительный тост за приключения."},
    {"id": "extreme-dare-02", "type": "dare", "category": "Жесть", "age": "16+", "text": "Придумай экстремальное название для следующего выхода компании."},
    {"id": "extreme-dare-03", "type": "dare", "category": "Жесть", "age": "18+", "text": "🔥 Поделись забавной взрослой историей, сохраняя приличия."},
]

HELP_TEXT = (
    "ℹ️ <b>Как играть офлайн</b>\n"
    "1. Создайте новую игру и добавьте игроков командой <code>/addplayer Имя</code> или просто отправляя имена текстом.\n"
    "2. Когда список готов, нажмите «▶️ Старт» — бот выберет случайного игрока.\n"
    "3. Участник выбирает «Правда» или «Действие» и выполняет задание в реальности.\n"
    "4. Нажмите «➡️ Далее», чтобы перейти к следующему игроку, или «🛑 Завершить», чтобы закончить игру.\n"
    "5. В настройках можно менять возрастной уровень, категории и очки.\n"
)

WELCOME_TEXT = (
    "👋 <b>Привет! Я ведущий игры «Правда или Действие» для вашей компании.</b>\n\n"
    "Создайте новую игру, добавьте игроков и позвольте мне вести раунды без лишнего спама.\n"
)


@dataclass
class GameState:
    chat_id: int
    host_id: int
    host_name: str
    players: List[str] = field(default_factory=list)
    scores: Dict[str, int] = field(default_factory=dict)
    is_running: bool = False
    awaiting_choice: bool = False
    current_player: Optional[str] = None
    current_card: Optional[Dict[str, str]] = None
    round_index: int = 0
    used_cards: Set[str] = field(default_factory=set)
    age_level: str = "0+"
    categories: Set[str] = field(default_factory=lambda: set(CATEGORIES))
    scoring_enabled: bool = False
    panel_message_id: Optional[int] = None

    def reset_for_round(self) -> None:
        self.current_card = None
        self.awaiting_choice = False

    def ensure_player_entry(self, name: str) -> None:
        if self.scoring_enabled and name not in self.scores:
            self.scores[name] = 0

    def remove_player(self, name: str) -> bool:
        normalized = name.lower()
        for stored in list(self.players):
            if stored.lower() == normalized:
                self.players.remove(stored)
                self.scores.pop(stored, None)
                if self.current_player == stored:
                    self.current_player = None
                return True
        return False


GAMES: Dict[int, GameState] = {}


def get_or_create_game(chat_id: int, host_id: int, host_name: str) -> GameState:
    game = GAMES.get(chat_id)
    if game is None:
        game = GameState(chat_id=chat_id, host_id=host_id, host_name=host_name)
        game.players.append(host_name)
        game.ensure_player_entry(host_name)
        GAMES[chat_id] = game
    return game


def reset_game(chat_id: int) -> Optional[GameState]:
    return GAMES.pop(chat_id, None)


def build_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎮 Создать игру", callback_data="menu:create")],
            [InlineKeyboardButton(text="ℹ️ Правила", callback_data="menu:help")],
        ]
    )


def build_lobby_markup(game: GameState) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="▶️ Старт", callback_data="game:start")],
        [InlineKeyboardButton(text="➕ Добавить игрока", callback_data="game:add")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings:open")],
        [InlineKeyboardButton(text="🛑 Завершить", callback_data="game:end")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_settings_menu(game: GameState) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"Возраст: {AGE_ICONS[game.age_level]} {game.age_level}", callback_data="settings:age")],
        [InlineKeyboardButton(text="Категории", callback_data="settings:categories")],
        [
            InlineKeyboardButton(
                text="Очки: включены" if game.scoring_enabled else "Очки: выключены",
                callback_data="settings:score_toggle",
            )
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="settings:back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_age_menu(game: GameState) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for age in AGE_LEVELS:
        prefix = "✅" if age == game.age_level else "▫️"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{prefix} {AGE_ICONS[age]} {age}",
                    callback_data=f"settings:set_age:{age}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="settings:open")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_categories_menu(game: GameState) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for name, emoji in CATEGORIES.items():
        active = "✅" if name in game.categories else "▫️"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{active} {emoji} {name}", callback_data=f"settings:toggle_category:{name}"
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="settings:open")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_choice_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧠 Правда", callback_data="round:truth"), InlineKeyboardButton(text="🎬 Действие", callback_data="round:dare")],
            [InlineKeyboardButton(text="🛑 Завершить", callback_data="game:end")],
        ]
    )


def build_post_card_markup(game: GameState) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    if game.scoring_enabled:
        rows.append([InlineKeyboardButton(text="✅ Засчитать очко", callback_data="round:score")])
    rows.append([InlineKeyboardButton(text="➡️ Далее", callback_data="round:next")])
    rows.append([InlineKeyboardButton(text="🛑 Завершить", callback_data="game:end")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def render_players(game: GameState) -> str:
    if not game.players:
        return "Пока никого нет. Добавьте игроков, отправив их имена."
    lines = ["👥 <b>Список игроков:</b>"]
    for index, name in enumerate(game.players, start=1):
        crown = " 👑" if name == game.host_name else ""
        score = f" — {game.scores.get(name, 0)} очк." if game.scoring_enabled else ""
        lines.append(f"{index}. {name}{crown}{score}")
    return "\n".join(lines)


def render_lobby(game: GameState) -> str:
    parts = [
        "🎮 <b>Лобби игры</b>",
        f"Хост: {game.host_name} 👑",
        render_players(game),
        "\nДобавьте игроков через /addplayer Имя или просто отправив имя в чат.",
    ]
    return "\n".join(parts)


def render_settings_summary(game: GameState) -> str:
    categories = ", ".join(f"{CATEGORIES[name]} {name}" for name in sorted(game.categories))
    return (
        "⚙️ <b>Текущие настройки</b>\n"
        f"Возраст: {AGE_ICONS[game.age_level]} {game.age_level}\n"
        f"Категории: {categories}\n"
        f"Очки: {'включены' if game.scoring_enabled else 'выключены'}"
    )


def choose_next_player(game: GameState) -> Optional[str]:
    if not game.players:
        return None
    candidates = game.players.copy()
    if game.current_player and len(candidates) > 1:
        candidates = [name for name in candidates if name != game.current_player]
    player = random.choice(candidates)
    game.current_player = player
    game.awaiting_choice = True
    return player


def filtered_cards(game: GameState, card_type: str) -> List[Dict[str, str]]:
    allowed_ages = {
        card_age for card_age in AGE_LEVELS if AGE_ORDER[card_age] <= AGE_ORDER[game.age_level]
    }
    result: List[Dict[str, str]] = []
    for card in DEFAULT_DECK:
        if card["type"] != card_type:
            continue
        if card["category"] not in game.categories:
            continue
        if card["age"] not in allowed_ages:
            continue
        result.append(card)
    return result


def pick_card(game: GameState, card_type: str) -> Tuple[Optional[Dict[str, str]], bool]:
    cards = filtered_cards(game, card_type)
    if not cards:
        return None, False
    fresh_cards = [card for card in cards if card["id"] not in game.used_cards]
    recycled = False
    if not fresh_cards:
        game.used_cards.clear()
        fresh_cards = cards
        recycled = True
    card = random.choice(fresh_cards)
    game.used_cards.add(card["id"])
    return card, recycled


def lobby_needs_update(game: GameState) -> bool:
    return game.panel_message_id is not None


def scoreboard_text(game: GameState) -> str:
    if not game.scoring_enabled or not game.scores:
        return "Игра завершена. Очки не вели или никто их не заработал."
    ordered = sorted(game.scores.items(), key=lambda item: item[1], reverse=True)
    lines = ["🏆 <b>Финальный счёт</b>"]
    for position, (name, score) in enumerate(ordered, start=1):
        crown = " 👑" if position == 1 else ""
        lines.append(f"{position}. {name}{crown} — {score}")
    return "\n".join(lines)


def welcome_text_with_menu() -> Dict[str, object]:
    return {"text": WELCOME_TEXT, "reply_markup": build_main_menu()}


def ensure_host(callback: CallbackQuery, game: GameState) -> bool:
    if callback.from_user and callback.from_user.id == game.host_id:
        return True
    asyncio.create_task(
        callback.answer("Только хост может использовать эту кнопку.", show_alert=False)
    )
    return False


bot_defaults: Dict[str, object] = {}
if DefaultBotProperties is not None:
    bot_defaults["default"] = DefaultBotProperties(parse_mode="HTML")
else:
    bot_defaults["parse_mode"] = "HTML"

bot = Bot(token=BOT_TOKEN, **bot_defaults)
dp = Dispatcher()


@dp.message(CommandStart())
async def handle_start(message: Message) -> None:
    game = GAMES.get(message.chat.id)
    if game and game.is_running:
        await message.answer("Игра уже запущена. Используйте кнопки, чтобы продолжить.")
        return
    await message.answer(**welcome_text_with_menu())


@dp.message(Command("help"))
async def handle_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


@dp.message(Command("newgame"))
async def handle_new_game(message: Message) -> None:
    await create_or_reset_game(message)


async def create_or_reset_game(message: Message) -> None:
    chat_id = message.chat.id
    host_id = message.from_user.id if message.from_user else 0
    host_name = message.from_user.full_name if message.from_user else "Хост"
    game = get_or_create_game(chat_id, host_id, host_name)
    game.host_id = host_id
    game.host_name = host_name
    game.is_running = False
    game.awaiting_choice = False
    game.current_player = None
    game.current_card = None
    game.round_index = 0
    game.used_cards.clear()
    game.panel_message_id = None
    if host_name not in game.players:
        game.players.insert(0, host_name)
    game.ensure_player_entry(host_name)
    await message.answer("🎲 Новая игра создана! Я уже добавил хоста в список игроков.")
    text = render_lobby(game)
    sent = await message.answer(text, reply_markup=build_lobby_markup(game))
    game.panel_message_id = sent.message_id


@dp.message(Command("addplayer"))
async def handle_add_player_command(message: Message) -> None:
    name = message.text.split(maxsplit=1)
    if len(name) < 2:
        await message.answer("Используйте формат: /addplayer Имя")
        return
    await add_player(message, name[1].strip())


async def add_player(message: Message, raw_name: str) -> None:
    chat_id = message.chat.id
    game = GAMES.get(chat_id)
    if not game:
        await message.answer("Сначала создайте игру командой /newgame или через меню.")
        return
    if message.from_user and message.from_user.id != game.host_id:
        await message.answer("Добавлять игроков может только хост.")
        return
    name = raw_name.strip()
    if not name:
        await message.answer("Имя не должно быть пустым.")
        return
    if any(existing.lower() == name.lower() for existing in game.players):
        await message.answer("Такой игрок уже есть в списке.")
        return
    game.players.append(name)
    game.ensure_player_entry(name)
    await message.answer(f"✅ Добавлен игрок: {name}")
    if lobby_needs_update(game):
        await update_lobby_panel(message.chat.id, game)


async def update_lobby_panel(chat_id: int, game: GameState) -> None:
    if game.panel_message_id is None:
        return
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=game.panel_message_id,
            text=render_lobby(game),
            reply_markup=build_lobby_markup(game),
        )
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise


@dp.message()
async def handle_plain_text(message: Message) -> None:
    if not message.text or message.text.startswith("/"):
        return
    game = GAMES.get(message.chat.id)
    if not game or game.is_running:
        return
    await add_player(message, message.text.strip())


@dp.callback_query(F.data == "menu:create")
async def handle_menu_create(callback: CallbackQuery) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    chat_id = message.chat.id
    from_user = callback.from_user
    game = get_or_create_game(chat_id, from_user.id if from_user else 0, from_user.full_name if from_user else "Хост")
    game.host_id = from_user.id if from_user else 0
    game.host_name = from_user.full_name if from_user else "Хост"
    game.players = [game.host_name]
    game.scores = {game.host_name: 0} if game.scoring_enabled else {}
    game.is_running = False
    game.awaiting_choice = False
    game.current_player = None
    game.current_card = None
    game.round_index = 0
    game.used_cards.clear()
    game.panel_message_id = message.message_id
    await callback.answer("Игра создана. Добавьте игроков!")
    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=message.message_id,
        text=render_lobby(game),
        reply_markup=build_lobby_markup(game),
    )


@dp.callback_query(F.data == "menu:help")
async def handle_menu_help(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message:
        await callback.message.answer(HELP_TEXT)


@dp.callback_query(F.data == "game:add")
async def handle_game_add(callback: CallbackQuery) -> None:
    game = GAMES.get(callback.message.chat.id) if callback.message else None
    if not game:
        await callback.answer("Сначала создайте игру.")
        return
    if not ensure_host(callback, game):
        return
    await callback.answer("Просто отправьте имя новым сообщением или используйте /addplayer Имя.")


@dp.callback_query(F.data == "game:start")
async def handle_game_start(callback: CallbackQuery) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    game = GAMES.get(message.chat.id)
    if not game:
        await callback.answer("Создайте игру заново.")
        return
    if not ensure_host(callback, game):
        return
    if len(game.players) < 2:
        await callback.answer("Добавьте минимум двух игроков.", show_alert=True)
        return
    game.is_running = True
    game.round_index = 0
    game.used_cards.clear()
    game.scores = {name: 0 for name in game.players} if game.scoring_enabled else {}
    await callback.answer()
    await send_next_player_prompt(message.chat.id, game)


async def send_next_player_prompt(chat_id: int, game: GameState) -> None:
    player = choose_next_player(game)
    if not player:
        await bot.send_message(chat_id, "Нет игроков. Добавьте участников, чтобы начать.")
        return
    game.round_index += 1
    await bot.send_message(
        chat_id,
        (
            f"🎯 <b>Раунд {game.round_index}</b>\n"
            f"Случайный выбор пал на: <b>{player}</b>.\n"
            "Выбирай режим!"
        ),
        reply_markup=build_choice_markup(),
    )


@dp.callback_query(F.data.in_({"round:truth", "round:dare"}))
async def handle_round_choice(callback: CallbackQuery) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    game = GAMES.get(message.chat.id)
    if not game:
        await callback.answer("Игра не найдена.")
        return
    if not ensure_host(callback, game):
        return
    if not game.awaiting_choice or not game.current_player:
        await callback.answer("Сначала запустите раунд.")
        return
    card_type = "truth" if callback.data == "round:truth" else "dare"
    card, recycled = pick_card(game, card_type)
    if card is None:
        await callback.answer("Нет заданий для выбранных настроек. Измените категории или возраст.", show_alert=True)
        return
    game.current_card = card
    game.awaiting_choice = False
    await callback.answer()
    if recycled:
        await bot.send_message(
            message.chat.id,
            "Колода для выбранных фильтров закончилась — перетасовал задания и начинаем заново!",
        )
    text = (
        f"{('🧠 Правда' if card_type == 'truth' else '🎬 Действие')} для <b>{game.current_player}</b>:\n"
        f"{card['text']}"
    )
    await bot.send_message(message.chat.id, text, reply_markup=build_post_card_markup(game))


@dp.callback_query(F.data == "round:score")
async def handle_round_score(callback: CallbackQuery) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    game = GAMES.get(message.chat.id)
    if not game or not game.scoring_enabled:
        await callback.answer()
        return
    if not ensure_host(callback, game):
        return
    if not game.current_player:
        await callback.answer("Очко не к кому применить.")
        return
    game.scores[game.current_player] = game.scores.get(game.current_player, 0) + 1
    await callback.answer("Очко добавлено!")
    await bot.send_message(message.chat.id, f"🔢 У {game.current_player} теперь {game.scores[game.current_player]} очко(ов).")
    if lobby_needs_update(game):
        await update_lobby_panel(message.chat.id, game)


@dp.callback_query(F.data == "round:next")
async def handle_round_next(callback: CallbackQuery) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    game = GAMES.get(message.chat.id)
    if not game:
        await callback.answer()
        return
    if not ensure_host(callback, game):
        return
    game.reset_for_round()
    await callback.answer("Следующий игрок!")
    await send_next_player_prompt(message.chat.id, game)


@dp.callback_query(F.data == "game:end")
async def handle_game_end(callback: CallbackQuery) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    game = GAMES.get(message.chat.id)
    if not game:
        await callback.answer("Игра уже завершена.")
        return
    if not ensure_host(callback, game):
        return
    summary = scoreboard_text(game)
    reset_game(message.chat.id)
    await callback.answer("Игра завершена.")
    await bot.send_message(message.chat.id, summary)
    await bot.send_message(message.chat.id, **welcome_text_with_menu())


@dp.callback_query(F.data == "settings:open")
async def handle_settings_open(callback: CallbackQuery) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    game = GAMES.get(message.chat.id)
    if not game:
        await callback.answer("Сначала создайте игру.")
        return
    if not ensure_host(callback, game):
        return
    await callback.answer()
    await bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text=render_settings_summary(game),
        reply_markup=build_settings_menu(game),
    )


@dp.callback_query(F.data == "settings:back")
async def handle_settings_back(callback: CallbackQuery) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    game = GAMES.get(message.chat.id)
    if not game:
        await callback.answer()
        return
    if not ensure_host(callback, game):
        return
    await callback.answer()
    await bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text=render_lobby(game),
        reply_markup=build_lobby_markup(game),
    )


@dp.callback_query(F.data == "settings:categories")
async def handle_settings_categories(callback: CallbackQuery) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    game = GAMES.get(message.chat.id)
    if not game:
        await callback.answer()
        return
    if not ensure_host(callback, game):
        return
    await callback.answer()
    await bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text="Выберите категории для заданий:",
        reply_markup=build_categories_menu(game),
    )


@dp.callback_query(F.data == "settings:age")
async def handle_settings_age(callback: CallbackQuery) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    game = GAMES.get(message.chat.id)
    if not game:
        await callback.answer()
        return
    if not ensure_host(callback, game):
        return
    await callback.answer()
    await bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text="Выберите возрастной уровень:",
        reply_markup=build_age_menu(game),
    )


@dp.callback_query(F.data.startswith("settings:set_age:"))
async def handle_set_age(callback: CallbackQuery) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    game = GAMES.get(message.chat.id)
    if not game:
        await callback.answer()
        return
    if not ensure_host(callback, game):
        return
    age = callback.data.split(":")[-1]
    if age not in AGE_LEVELS:
        await callback.answer("Неизвестный возраст.")
        return
    game.age_level = age
    await callback.answer(f"Выбрано: {age}")
    await bot.edit_message_reply_markup(
        chat_id=message.chat.id,
        message_id=message.message_id,
        reply_markup=build_age_menu(game),
    )


@dp.callback_query(F.data.startswith("settings:toggle_category:"))
async def handle_toggle_category(callback: CallbackQuery) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    game = GAMES.get(message.chat.id)
    if not game:
        await callback.answer()
        return
    if not ensure_host(callback, game):
        return
    category = callback.data.split(":")[-1]
    if category not in CATEGORIES:
        await callback.answer("Категория не найдена.")
        return
    if category in game.categories and len(game.categories) == 1:
        await callback.answer("Нельзя отключить все категории.", show_alert=True)
        return
    if category in game.categories:
        game.categories.remove(category)
        await callback.answer(f"Убрали категорию {category}.")
    else:
        game.categories.add(category)
        await callback.answer(f"Добавили категорию {category}.")
    await bot.edit_message_reply_markup(
        chat_id=message.chat.id,
        message_id=message.message_id,
        reply_markup=build_categories_menu(game),
    )


@dp.callback_query(F.data == "settings:score_toggle")
async def handle_score_toggle(callback: CallbackQuery) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    game = GAMES.get(message.chat.id)
    if not game:
        await callback.answer()
        return
    if not ensure_host(callback, game):
        return
    game.scoring_enabled = not game.scoring_enabled
    if not game.scoring_enabled:
        game.scores.clear()
    else:
        for name in game.players:
            game.scores.setdefault(name, 0)
    await callback.answer("Очки обновлены.")
    await bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text=render_settings_summary(game),
        reply_markup=build_settings_menu(game),
    )
    if lobby_needs_update(game):
        await update_lobby_panel(message.chat.id, game)


async def main() -> None:
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
