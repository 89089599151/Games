import asyncio
import random
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# ==== ВСТАВЬ СВОЙ ТОКЕН ====
TOKEN = "8415157646:AAFdYFNTBAqCWkDbA2Vp14NuxKO78RHJRdw"

# ==== СОЗДАЁМ БОТА И ДИСПЕТЧЕР ====
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ==== СОСТОЯНИЯ ====
class Game(StatesGroup):
    choose_category = State()
    set_player_count = State()
    get_player_names = State()
    in_game = State()

# ==== БАЗА ВОПРОСОВ ====
QUESTIONS = {
    "Лайт": {
        "truth": [
            "Какое твоё любимое блюдо?",
            "Какая у тебя самая странная привычка?",
            "Что ты делаешь, когда никто не видит?",
            "Какой у тебя был самый неловкий момент?"
        ],
        "dare": [
            "Сделай смешное лицо 😂",
            "Прочитай последнее сообщение из своих чатов 📱",
            "Покажи свою самую неловкую фотографию 📸",
            "Скажи комплимент игроку справа 💬"
        ]
    },
    "Друзья": {
        "truth": [
            "Кто из этой компании тебя лучше всего понимает?",
            "Кому бы ты доверил свой секрет?",
            "Что бы ты изменил в одном из друзей?",
            "Кто чаще всех тебя бесит, но ты всё равно его любишь?"
        ],
        "dare": [
            "Позвони другу и скажи, что скучаешь ☎️",
            "Отправь случайный эмодзи в любой чат 💌",
            "Придумай всем игрокам новые имена 😄",
            "Изобрази любого из игроков 🤪"
        ]
    },
    "Романтика": {
        "truth": [
            "Кого из присутствующих ты считаешь самым симпатичным? 😉",
            "Кому ты последний раз говорил «люблю»?",
            "Какое твоё идеальное свидание?",
            "Ты когда-нибудь влюблялся(ась) в друга?"
        ],
        "dare": [
            "Отправь сердечко ❤️ кому-то из игроков",
            "Скажи комплимент каждому по очереди 💘",
            "Посмотри в глаза соседу слева 10 секунд 😳",
            "Скажи что-то милое любому игроку 🥰"
        ]
    },
    "Жесть": {
        "truth": [
            "Какой твой самый большой страх?",
            "Что ты сделал бы, если бы завтра был конец света?",
            "Кому бы ты не доверил свой телефон?",
            "Какая твоя самая позорная тайна?"
        ],
        "dare": [
            "Сделай 10 приседаний перед всеми 💪",
            "Покажи последнее фото в галерее 📷",
            "Произнеси скороговорку без ошибок 😜",
            "Скажи «Я гений» громко три раза 😎"
        ]
    }
}

# ==== СЛУЖЕБНЫЕ КЛАВИАТУРЫ ====
def category_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Лайт"), KeyboardButton(text="Друзья")],
            [KeyboardButton(text="Романтика"), KeyboardButton(text="Жесть")]
        ],
        resize_keyboard=True
    )

def choice_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Правда 🔵"), KeyboardButton(text="Действие 🔴")],
            [KeyboardButton(text="Пропустить 🔁"), KeyboardButton(text="Завершить 🏁")]
        ],
        resize_keyboard=True
    )

# ==== СТАРТ ====
@dp.message(Command("start"))
async def start_game(message: Message, state: FSMContext):
    await message.answer(
        "👋 Привет! Это игра 'Правда или Действие'.\nВыбери категорию вопросов:",
        reply_markup=category_keyboard()
    )
    await state.set_state(Game.choose_category)

# ==== ВЫБОР КАТЕГОРИИ ====
@dp.message(Game.choose_category)
async def choose_category(message: Message, state: FSMContext):
    if message.text not in QUESTIONS:
        await message.answer("Выбери категорию с клавиатуры.")
        return
    await state.update_data(category=message.text)
    await message.answer("Сколько человек будет играть?")
    await state.set_state(Game.set_player_count)

# ==== ВВОД КОЛИЧЕСТВА ====
@dp.message(Game.set_player_count)
async def set_count(message: Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) < 1:
        await message.answer("Введи корректное число игроков (1 или больше).")
        return
    count = int(message.text)
    await state.update_data(player_count=count, players=[], current=0)
    await message.answer("Введите имя игрока №1:")
    await state.set_state(Game.get_player_names)

# ==== ВВОД ИМЁН ====
@dp.message(Game.get_player_names)
async def get_names(message: Message, state: FSMContext):
    data = await state.get_data()
    players = data["players"]
    players.append(message.text)
    await state.update_data(players=players)
    if len(players) < data["player_count"]:
        await message.answer(f"Введите имя игрока №{len(players)+1}:")
    else:
        await message.answer("Все игроки добавлены! 🎉\nНачинаем игру!")
        await next_turn(message, state)

# ==== СЛЕДУЮЩИЙ ХОД ====
async def next_turn(message: Message, state: FSMContext):
    data = await state.get_data()
    players = data["players"]
    current = data["current"]

    player = players[current % len(players)]
    await state.update_data(current=current + 1)

    await message.answer(
        f"👉 Ход игрока: *{player}*\nВыбери:",
        parse_mode="Markdown",
        reply_markup=choice_keyboard()
    )
    await state.set_state(Game.in_game)

# ==== ОСНОВНОЙ ИГРОВОЙ ПРОЦЕСС ====
@dp.message(Game.in_game)
async def in_game(message: Message, state: FSMContext):
    text = message.text
    data = await state.get_data()
    category = data["category"]

    if text == "Завершить 🏁":
        await message.answer("Игра окончена! 🎊 Спасибо за участие!")
        await state.clear()
        return

    if text == "Пропустить 🔁":
        await message.answer("Пропускаем ход 🔄")
        await next_turn(message, state)
        return

    if text.startswith("Правда"):
        question = random.choice(QUESTIONS[category]["truth"])
        await message.answer(f"🟦 *Правда:*\n{question}", parse_mode="Markdown")
        await asyncio.sleep(2)
        await next_turn(message, state)

    elif text.startswith("Действие"):
        question = random.choice(QUESTIONS[category]["dare"])
        await message.answer(f"🟥 *Действие:*\n{question}", parse_mode="Markdown")
        await asyncio.sleep(2)
        await next_turn(message, state)
    else:
        await message.answer("Выбери действие с клавиатуры!")

# ==== ЗАПУСК ====
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
