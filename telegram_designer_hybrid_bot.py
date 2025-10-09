#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chloe Link — финальная стабильная версия.
Aiogram v3, SQLite (aiosqlite).

Что исправлено по сравнению с исходным кодом:
1) Стабильная логика свайпов и матчей (обе стороны получают уведомления).
2) Исключены дубликаты и падения из‑за неинициализированных переменных.
3) Лента проектов для дизайнеров и лента дизайнеров для заказчиков — без фильтра по статусу.
4) Исправлены ключевые места FSM: очистка состояния, возвраты в меню, «назад», «готово» и т.д.
5) Уведомления о лайке даже без матча (soft‑notify), чтобы человек видел интерес.
6) Мелкие UX‑улучшения и логгирование.

Перед запуском:
- pip install aiogram==3.* aiosqlite python-dotenv
- создайте .env с BOT_TOKEN=...

Запуск: python chloe_link_bot.py
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, List
import aiosqlite
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InputMediaPhoto
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# ====================== CONFIG ======================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Please set BOT_TOKEN in .env as BOT_TOKEN=...")

DB_PATH = "bot_data.db"
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ====================== FSM ======================
class DesignerOnboard(StatesGroup):
    name = State()
    skills = State()
    photos = State()
    portfolio_link = State()

class ClientOnboard(StatesGroup):
    title = State()
    description = State()
    budget = State()
    styles = State()
    refs = State()

class EditDesigner(StatesGroup):
    name = State()
    skills = State()
    portfolio_link = State()
    delete_photo = State()

class EditClientProject(StatesGroup):
    title = State()
    description = State()
    budget = State()
    styles = State()
    refs = State()

class DesignerAddPhotos(StatesGroup):
    waiting = State()

# ====================== DB ======================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            role TEXT,
            name TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS designers (
            user_id INTEGER PRIMARY KEY,
            skills TEXT,
            portfolio_link TEXT
        );
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            file_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            title TEXT,
            description TEXT,
            budget TEXT,
            styles TEXT,
            refs TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS swipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            viewer INTEGER,
            target_type TEXT,   -- 'designer' | 'project'
            target_id INTEGER,
            action TEXT,        -- 'like' | 'skip'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            designer_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS active_chat (
            user_id INTEGER PRIMARY KEY,
            match_id INTEGER
        );
        """)
        # safety migration: add status if missing
        try:
            await db.execute("SELECT status FROM users LIMIT 1")
        except Exception:
            await db.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'")
        await db.commit()
    logger.info("Database initialized")

# ---- Users / Designers / Projects
async def save_user(user_id:int, role:str, name:Optional[str]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO users(user_id, role, name) VALUES(?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET role=excluded.role, name=COALESCE(excluded.name, users.name)",
            (user_id, role, name)
        )
        await db.commit()

async def update_user_name(user_id:int, name:str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET name=? WHERE user_id=?", (name, user_id))
        await db.commit()

async def get_user_role(user_id:int) -> Optional[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT role FROM users WHERE user_id=?", (user_id,))
        r = await cur.fetchone()
        return r[0] if r else None

async def get_user_status(user_id:int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT status FROM users WHERE user_id=?", (user_id,))
        r = await cur.fetchone()
        return r[0] if r else "active"

async def get_user_name(user_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT name FROM users WHERE user_id=?", (user_id,))
        r = await cur.fetchone()
        return r[0] if r and r[0] else ""

async def save_designer(user_id:int, skills:str, link:Optional[str]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO designers(user_id, skills, portfolio_link) VALUES(?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET skills=excluded.skills, portfolio_link=excluded.portfolio_link",
            (user_id, skills, link)
        )
        await db.commit()

async def add_portfolio_item(user_id:int, file_id:str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO portfolio(user_id, file_id) VALUES(?,?)", (user_id, file_id))
        await db.commit()

async def get_last_portfolio_photos(user_id:int, limit:int=3) -> List[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT file_id FROM portfolio WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        )
        rows = await cur.fetchall()
    return [r[0] for r in rows]

async def add_project(client_id:int, title:str, description:str, budget:str, styles:str, refs:str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO projects(client_id, title, description, budget, styles, refs) VALUES(?,?,?,?,?,?)",
            (client_id, title, description, budget, styles, refs)
        )
        await db.commit()
        return cur.lastrowid

async def update_latest_project(client_id:int, title:str, description:str, budget:str, styles:str, refs:str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id FROM projects WHERE client_id=? ORDER BY created_at DESC, id DESC LIMIT 1",
            (client_id,)
        )
        row = await cur.fetchone()
        if row:
            pid = row[0]
            await db.execute(
                "UPDATE projects SET title=?, description=?, budget=?, styles=?, refs=? WHERE id=?",
                (title, description, budget, styles, refs, pid)
            )
            await db.commit()
            return pid
        else:
            cur2 = await db.execute(
                "INSERT INTO projects(client_id, title, description, budget, styles, refs) VALUES(?,?,?,?,?,?)",
                (client_id, title, description, budget, styles, refs)
            )
            await db.commit()
            return cur2.lastrowid

async def record_swipe(viewer:int, target_type:str, target_id:int, action:str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO swipes(viewer, target_type, target_id, action) VALUES(?,?,?,?)",
            (viewer, target_type, target_id, action)
        )
        await db.commit()

async def create_match(client_id:int, designer_id:int) -> Optional[int]:
    """Создаёт матч между заказчиком и дизайнером. Предотвращает самоматч и дубликаты."""
    if client_id == designer_id:
        logger.warning("Self-match prevented for user %s", client_id)
        return None

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id FROM matches WHERE client_id=? AND designer_id=?",
            (client_id, designer_id)
        )
        existing = await cur.fetchone()
        if existing:
            return existing[0]

        cur = await db.execute(
            "INSERT INTO matches(client_id, designer_id) VALUES(?,?)",
            (client_id, designer_id)
        )
        await db.commit()
        return cur.lastrowid

async def set_active_chat(user_id:int, match_id:int):
    if match_id is None:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO active_chat(user_id, match_id) VALUES(?,?)",
            (user_id, match_id)
        )
        await db.commit()

async def get_active_match_for_user(user_id:int) -> Optional[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT match_id FROM active_chat WHERE user_id=?", (user_id,))
        r = await cur.fetchone()
        return r[0] if r else None

async def get_match_partner(user_id:int) -> Optional[int]:
    match_id = await get_active_match_for_user(user_id)
    if not match_id:
        return None
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT client_id, designer_id FROM matches WHERE id=?", (match_id,))
        r = await cur.fetchone()
        if not r:
            return None
        client_id, designer_id = r
        return designer_id if client_id == user_id else client_id

# ====================== Keyboards ======================
def kb_role() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Я — Дизайнер 🎨"), KeyboardButton(text="Я — Заказчик 💼")]],
        resize_keyboard=True
    )

def kb_designer_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧭 Найти проект"), KeyboardButton(text="🧾 Мой профиль")],
            [KeyboardButton(text="🟢 Статус"), KeyboardButton(text="⚙️ Настройки")]
        ],
        resize_keyboard=True
    )

def kb_client_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Найти дизайнера"), KeyboardButton(text="🧾 Мой профиль")],
            [KeyboardButton(text="🟢 Статус"), KeyboardButton(text="⚙️ Настройки")]
        ],
        resize_keyboard=True
    )

def kb_status() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🟢 В поиске"), KeyboardButton(text="🟡 Занят")],
                  [KeyboardButton(text="🔴 Не активен"), KeyboardButton(text="◀︎ Назад")]],
        resize_keyboard=True
    )

def kb_settings() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔁 Сменить роль")],
                  [KeyboardButton(text="🚪 Завершить диалог"), KeyboardButton(text="◀︎ Назад")]],
        resize_keyboard=True
    )

def kb_done() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Готово")]], resize_keyboard=True)

def kb_skip() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Пропустить")]], resize_keyboard=True)

def kb_profile_actions() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✏️ Изменить профиль")],
                  [KeyboardButton(text="◀︎ Назад")]],
        resize_keyboard=True
    )

def kb_client_swipe() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❤️ Нравится"), KeyboardButton(text="→ Пропустить")],
                  [KeyboardButton(text="📂 Портфолио"), KeyboardButton(text="◀︎ Назад")]],
        resize_keyboard=True
    )

def kb_designer_swipe() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✋ Я готов"), KeyboardButton(text="→ Не интересно")],
                  [KeyboardButton(text="ℹ️ Подробнее"), KeyboardButton(text="◀︎ Назад")]],
        resize_keyboard=True
    )

def kb_edit_designer_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Имя"), KeyboardButton(text="Навыки")],
            [KeyboardButton(text="Портфолио (ссылка)"), KeyboardButton(text="Загрузить новые работы")],
            [KeyboardButton(text="🗑 Удалить работу")],
            [KeyboardButton(text="Всё заново"), KeyboardButton(text="◀︎ Назад")]
        ],
        resize_keyboard=True
    )

def kb_digits_choice(n: int) -> ReplyKeyboardMarkup:
    n = max(1, min(10, n))
    rows = []
    row = []
    for i in range(1, n + 1):
        row.append(KeyboardButton(text=str(i)))
        if len(row) == 5:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([KeyboardButton(text="Отмена"), KeyboardButton(text="◀︎ Назад")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

def kb_edit_client_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Название проекта"), KeyboardButton(text="Описание")],
            [KeyboardButton(text="Бюджет"), KeyboardButton(text="Стили")],
            [KeyboardButton(text="Референсы"), KeyboardButton(text="Всё заново")],
            [KeyboardButton(text="◀︎ Назад")]
        ],
        resize_keyboard=True
    )

# ====================== Helpers ======================
def _normalize(t: Optional[str]) -> str:
    return (t or "").strip().lower().replace("ё", "е")

# ====================== Start & Role ======================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    role = await get_user_role(message.from_user.id)

    if message.chat.type != "private":
        await message.reply("👋 Для работы со мной перейдите в личные сообщения.")
        return

    if role == "designer":
        await message.answer("С возвращением, дизайнер 🎨", reply_markup=kb_designer_menu())
        return
    elif role == "client":
        await message.answer("С возвращением, заказчик 💼", reply_markup=kb_client_menu())
        return

    await message.answer("Привет! Кто вы по роли?", reply_markup=kb_role())

@dp.message(F.text == "Я — Дизайнер 🎨")
async def as_designer(message: types.Message, state: FSMContext):
    await save_user(message.from_user.id, "designer", message.from_user.full_name)
    await message.answer("Введите ваше имя (или отправьте текущее):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(DesignerOnboard.name)

@dp.message(F.text == "Я — Заказчик 💼")
async def as_client(message: types.Message, state: FSMContext):
    await save_user(message.from_user.id, "client", message.from_user.full_name)
    await message.answer("Введите название проекта:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(ClientOnboard.title)

# ====================== Designer Onboarding ======================
@dp.message(DesignerOnboard.name)
async def d_name(message: types.Message, state: FSMContext):
    name = (message.text or "").strip()
    if name:
        await update_user_name(message.from_user.id, name)
    await message.answer("Перечислите ваши навыки через запятую:")
    await state.set_state(DesignerOnboard.skills)

@dp.message(DesignerOnboard.skills)
async def d_skills(message: types.Message, state: FSMContext):
    await state.update_data(skills=(message.text or "").strip())
    await message.answer("Пришлите по одному фото работ (до 10). Когда закончите — нажмите «Готово».", reply_markup=kb_done())
    await state.set_state(DesignerOnboard.photos)

@dp.message(DesignerOnboard.photos, F.content_type == types.ContentType.PHOTO)
async def d_photo(message: types.Message, state: FSMContext):
    await add_portfolio_item(message.from_user.id, message.photo[-1].file_id)
    await message.answer("Фото добавлено. Можно отправить ещё или нажать «Готово».", reply_markup=kb_done())

@dp.message(DesignerOnboard.photos, F.text == "Готово")
async def d_photos_done(message: types.Message, state: FSMContext):
    await message.answer("Пришлите ссылку на портфолио (Behance/Dribbble) или нажмите «Пропустить».", reply_markup=kb_skip())
    await state.set_state(DesignerOnboard.portfolio_link)

@dp.message(DesignerOnboard.portfolio_link)
async def d_link(message: types.Message, state: FSMContext):
    data = await state.get_data()
    skills = data.get("skills", "")
    link = None if _normalize(message.text) == "пропустить" else (message.text or "").strip()
    await save_designer(message.from_user.id, skills, link)
    await state.clear()
    await message.answer("Профиль дизайнера создан ✅", reply_markup=kb_designer_menu())

# ====================== Client Onboarding ======================
@dp.message(ClientOnboard.title)
async def c_title(message: types.Message, state: FSMContext):
    await state.update_data(title=(message.text or "").strip())
    await message.answer("Опишите задачу:")
    await state.set_state(ClientOnboard.description)

@dp.message(ClientOnboard.description)
async def c_desc(message: types.Message, state: FSMContext):
    await state.update_data(description=(message.text or "").strip())
    await message.answer("Укажите бюджет:")
    await state.set_state(ClientOnboard.budget)

@dp.message(ClientOnboard.budget)
async def c_budget(message: types.Message, state: FSMContext):
    await state.update_data(budget=(message.text or "").strip())
    await message.answer("Перечислите стили через запятую:")
    await state.set_state(ClientOnboard.styles)

@dp.message(ClientOnboard.styles)
async def c_styles(message: types.Message, state: FSMContext):
    await state.update_data(styles=(message.text or "").strip())
    await message.answer("Прикрепите референсы (ссылки) или нажмите «Пропустить».", reply_markup=kb_skip())
    await state.set_state(ClientOnboard.refs)

@dp.message(ClientOnboard.refs)
async def c_refs(message: types.Message, state: FSMContext):
    data = await state.get_data()
    refs = "" if _normalize(message.text) == "пропустить" else (message.text or "").strip()
    pid = await add_project(
        message.from_user.id,
        data.get("title",""),
        data.get("description",""),
        data.get("budget",""),
        data.get("styles",""),
        refs,
    )
    await state.clear()
    await message.answer(f"Проект создан ✅ (id={pid})", reply_markup=kb_client_menu())

# ====================== Profile ======================
async def _show_profile(message: types.Message):
    role = await get_user_role(message.from_user.id)
    status = await get_user_status(message.from_user.id)
    if not role:
        await message.answer("Профиль не найден. Нажмите /start.", reply_markup=kb_role())
        return

    if role == "designer":
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT skills, portfolio_link FROM designers WHERE user_id=?", (message.from_user.id,))
            r = await cur.fetchone()
        skills, link = r if r else ("—", "—")
        link = link or "—"
        name = await get_user_name(message.from_user.id) or message.from_user.full_name
        text = (
            f"👤 Дизайнер: {name}\n"
            f"🟢 Статус: {status}\n"
            f"🧠 Навыки: {skills}\n"
            f"🔗 Портфолио: {link}\n"
        )
        await message.answer(text, reply_markup=kb_profile_actions())
        photos = await get_last_portfolio_photos(message.from_user.id, 10)
        if photos:
            media = [InputMediaPhoto(media=fid) for fid in photos]
            try:
                await message.answer_media_group(media)
            except Exception:
                for m in media:
                    await message.answer_photo(m.media)
        else:
            await message.answer("Фото работ пока не добавлены.")
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT id, title FROM projects WHERE client_id=? ORDER BY created_at DESC, id DESC LIMIT 5",
                (message.from_user.id,)
            )
            rows = await cur.fetchall()
        if not rows:
            text = (
                f"👤 Заказчик: {message.from_user.full_name}\n"
                f"🟢 Статус: {status}\n"
                f"Проектов пока нет.\n"
            )
        else:
            lines = "\n".join([f"- {title} (id={pid})" for pid, title in rows])
            text = (
                f"👤 Заказчик: {message.from_user.full_name}\n"
                f"🟢 Статус: {status}\n"
                f"Ваши проекты:\n{lines}"
            )
        await message.answer(text, reply_markup=kb_profile_actions())

@dp.message(Command("my_profile"))
@dp.message(Command("profile"))
@dp.message(F.text == "🧾 Мой профиль")
@dp.message(F.text.func(lambda t: isinstance(t, str) and "профил" in t.lower() and "изменить" not in t.lower()))
async def my_profile_any(message: types.Message):
    await _show_profile(message)

# ===== Edit profile ENTRY
@dp.message(F.text == "✏️ Изменить профиль")
@dp.message(F.text.func(lambda t: isinstance(t, str) and "изменить профиль" in t.lower()))
async def edit_profile_entry(message: types.Message, state: FSMContext):
    role = await get_user_role(message.from_user.id)
    await state.clear()
    if role == "designer":
        await message.answer("Что вы хотите изменить?", reply_markup=kb_edit_designer_menu())
    else:
        await message.answer("Что вы хотите изменить?", reply_markup=kb_edit_client_menu())

# ---- Designer edit flow: menu picks
@dp.message(F.text == "Имя")
async def edit_pick_name(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "designer":
        return
    await state.set_state(EditDesigner.name)
    await message.answer("Введите новое имя:", reply_markup=ReplyKeyboardRemove())

@dp.message(F.text == "Навыки")
async def edit_pick_skills(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "designer":
        return
    await message.answer("Введите навыки через запятую:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(EditDesigner.skills)

@dp.message(F.text == "Портфолио (ссылка)")
async def edit_pick_portfolio_link(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "designer":
        return
    await message.answer("Пришлите ссылку на портфолио или нажмите «Пропустить».", reply_markup=kb_skip())
    await state.set_state(EditDesigner.portfolio_link)

@dp.message(F.text == "Загрузить новые работы")
async def edit_pick_add_photos(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "designer":
        return
    await message.answer("Отправляйте фото по одному. Когда закончите — нажмите «Готово».", reply_markup=kb_done())
    await state.set_state(DesignerAddPhotos.waiting)

@dp.message(F.text == "🗑 Удалить работу")
async def delete_photo_start(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "designer":
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, file_id FROM portfolio WHERE user_id=? ORDER BY id DESC LIMIT 10",
            (message.from_user.id,)
        )
        rows = await cur.fetchall()
    if not rows:
        await message.answer("У вас пока нет загруженных работ.", reply_markup=kb_edit_designer_menu())
        return
    media = [InputMediaPhoto(media=fid) for _, fid in rows]
    try:
        await message.answer_media_group(media)
    except Exception:
        for m in media:
            await message.answer_photo(m.media)
    await state.update_data(delete_list=rows)
    await state.set_state(EditDesigner.delete_photo)
    await message.answer("Выберите номер работы для удаления:", reply_markup=kb_digits_choice(len(rows)))

@dp.message(F.text == "Всё заново")
async def edit_pick_reset_all(message: types.Message, state: FSMContext):
    role = await get_user_role(message.from_user.id)
    if role == "designer":
        await message.answer("Начнём заново. Введите ваше имя:", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        await state.set_state(DesignerOnboard.name)
    elif role == "client":
        await message.answer("Начнём заново. Введите название проекта:", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        await state.set_state(ClientOnboard.title)

# ---- Designer add photos flow
@dp.message(DesignerAddPhotos.waiting, F.content_type == types.ContentType.PHOTO)
async def add_more_photos(message: types.Message, state: FSMContext):
    await add_portfolio_item(message.from_user.id, message.photo[-1].file_id)
    await message.answer("Фото добавлено. Можно отправить ещё или нажать «Готово».", reply_markup=kb_done())

@dp.message(DesignerAddPhotos.waiting, F.text == "Готово")
async def add_more_photos_done(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Готово. Профиль обновлён ✅", reply_markup=kb_designer_menu())

# ---- Designer edit states
@dp.message(EditDesigner.delete_photo)
async def confirm_delete_photo(message: types.Message, state: FSMContext):
    text = (message.text or "").strip().lower()
    if text == "отмена":
        await state.clear()
        await message.answer("Удаление отменено.", reply_markup=kb_edit_designer_menu())
        return
    if not text.isdigit():
        await message.answer("Введите номер (1–10) или 'Отмена'.")
        return
    num = int(text)
    data = await state.get_data()
    rows = data.get("delete_list", [])
    if not (1 <= num <= len(rows)):
        await message.answer("Нет работы с таким номером.")
        return
    pid, _ = rows[num - 1]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM portfolio WHERE id=?", (pid,))
        await db.commit()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, file_id FROM portfolio WHERE user_id=? ORDER BY id DESC LIMIT 10",
            (message.from_user.id,)
        )
        rows = await cur.fetchall()
    if not rows:
        await state.clear()
        await message.answer("Все работы удалены ✅", reply_markup=kb_edit_designer_menu())
        return
    await state.update_data(delete_list=rows)
    await message.answer(f"Работа №{num} удалена ✅")
    await asyncio.sleep(0.2)
    media = [InputMediaPhoto(media=fid) for _, fid in rows]
    try:
        await message.answer_media_group(media)
    except Exception:
        for m in media:
            await message.answer_photo(m.media)
    await message.answer("Выберите следующую работу для удаления:", reply_markup=kb_digits_choice(len(rows)))

@dp.message(EditDesigner.name)
async def edit_d_name(message: types.Message, state: FSMContext):
    new_name = (message.text or "").strip()
    if not new_name:
        await message.answer("Имя не может быть пустым. Введите ещё раз:")
        return
    await update_user_name(message.from_user.id, new_name)
    await state.clear()
    await message.answer(f"Имя обновлено ✅\nНовое имя: {new_name}", reply_markup=kb_designer_menu())

@dp.message(EditDesigner.skills)
async def edit_d_skills(message: types.Message, state: FSMContext):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT portfolio_link FROM designers WHERE user_id=?", (message.from_user.id,))
        row = await cur.fetchone()
    link = row[0] if row else None
    await save_designer(message.from_user.id, (message.text or "").strip(), link)
    await state.clear()
    await message.answer("Навыки обновлены ✅", reply_markup=kb_designer_menu())

@dp.message(EditDesigner.portfolio_link)
async def edit_d_link(message: types.Message, state: FSMContext):
    link = None if _normalize(message.text) == "пропустить" else (message.text or "").strip()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT skills FROM designers WHERE user_id=?", (message.from_user.id,))
        row = await cur.fetchone()
    skills = row[0] if row and row[0] else ""
    await save_designer(message.from_user.id, skills, link)
    await state.clear()
    await message.answer("Ссылка на портфолио обновлена ✅", reply_markup=kb_designer_menu())

# ---- Client edit picks & states
@dp.message(F.text == "Название проекта")
async def edit_pick_title(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "client":
        return
    await message.answer("Введите новое название проекта:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(EditClientProject.title)

@dp.message(EditClientProject.title)
async def edit_c_title(message: types.Message, state: FSMContext):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT id, description, budget, styles, refs FROM projects WHERE client_id=? "
            "ORDER BY created_at DESC, id DESC LIMIT 1",
            (message.from_user.id,)
        )
        r = await cur.fetchone()
    if r:
        _, desc, budget, styles, refs = r
        await update_latest_project(message.from_user.id, (message.text or "").strip(), desc or "", budget or "", styles or "", refs or "")
        await state.clear()
        await message.answer("Название проекта обновлено ✅", reply_markup=kb_client_menu())
    else:
        pid = await add_project(message.from_user.id, (message.text or "").strip(), "", "", "", "")
        await state.clear()
        await message.answer(f"Проект создан ✅ (id={pid})", reply_markup=kb_client_menu())

@dp.message(F.text == "Описание")
async def edit_pick_description(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "client":
        return
    await message.answer("Введите новое краткое описание:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(EditClientProject.description)

@dp.message(EditClientProject.description)
async def edit_c_desc(message: types.Message, state: FSMContext):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT title, budget, styles, refs FROM projects WHERE client_id=? "
            "ORDER BY created_at DESC, id DESC LIMIT 1",
            (message.from_user.id,)
        )
        r = await cur.fetchone()
    title, budget, styles, refs = (r if r else ("", "", "", ""))
    await update_latest_project(message.from_user.id, title or "", (message.text or "").strip(), budget or "", styles or "", refs or "")
    await state.clear()
    await message.answer("Описание обновлено ✅", reply_markup=kb_client_menu())

@dp.message(F.text == "Бюджет")
async def edit_pick_budget(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "client":
        return
    await message.answer("Введите новый бюджет:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(EditClientProject.budget)

@dp.message(EditClientProject.budget)
async def edit_c_budget(message: types.Message, state: FSMContext):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT title, description, styles, refs FROM projects WHERE client_id=? "
            "ORDER BY created_at DESC, id DESC LIMIT 1",
            (message.from_user.id,)
        )
        r = await cur.fetchone()
    title, desc, styles, refs = (r if r else ("", "", "", ""))
    await update_latest_project(message.from_user.id, title or "", desc or "", (message.text or "").strip(), styles or "", refs or "")
    await state.clear()
    await message.answer("Бюджет обновлён ✅", reply_markup=kb_client_menu())

@dp.message(F.text == "Стили")
async def edit_pick_styles(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "client":
        return
    await message.answer("Введите стили (через запятую):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(EditClientProject.styles)

@dp.message(EditClientProject.styles)
async def edit_c_styles(message: types.Message, state: FSMContext):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT title, description, budget, refs FROM projects WHERE client_id=? "
            "ORDER BY created_at DESC, id DESC LIMIT 1",
            (message.from_user.id,)
        )
        r = await cur.fetchone()
    title, desc, budget, refs = (r if r else ("", "", "", ""))
    await update_latest_project(message.from_user.id, title or "", desc or "", budget or "", (message.text or "").strip(), refs or "")
    await state.clear()
    await message.answer("Стили обновлены ✅", reply_markup=kb_client_menu())

@dp.message(F.text == "Референсы")
async def edit_pick_refs(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "client":
        return
    await message.answer("Пришлите ссылки на референсы или нажмите «Пропустить».", reply_markup=kb_skip())
    await state.set_state(EditClientProject.refs)

@dp.message(EditClientProject.refs)
async def edit_c_refs(message: types.Message, state: FSMContext):
    refs = "" if _normalize(message.text) == "пропустить" else (message.text or "").strip()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT title, description, budget, styles FROM projects WHERE client_id=? "
            "ORDER BY created_at DESC, id DESC LIMIT 1",
            (message.from_user.id,)
        )
        r = await cur.fetchone()
    title, desc, budget, styles = (r if r else ("", "", "", ""))
    await update_latest_project(message.from_user.id, title or "", desc or "", budget or "", styles or "", refs or "")
    await state.clear()
    await message.answer("Референсы обновлены ✅", reply_markup=kb_client_menu())

# ====================== Feed (Find / Swipe) ======================
async def next_designer_for_client(client_id:int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT u.user_id, u.name, d.skills
            FROM users u
            JOIN designers d ON u.user_id = d.user_id
            WHERE u.user_id != ?
              AND u.user_id NOT IN (
                  SELECT target_id FROM swipes WHERE viewer=? AND target_type='designer'
              )
            ORDER BY RANDOM() LIMIT 1
            """,
            (client_id, client_id)
        )
        r = await cur.fetchone()
        if not r:
            return None
        uid, name, skills = r
        cur2 = await db.execute("SELECT file_id FROM portfolio WHERE user_id=? ORDER BY id DESC LIMIT 3", (uid,))
        photos = [row[0] for row in await cur2.fetchall()]
        return {"user_id": uid, "skills": skills or "—", "name": name or "—", "photos": photos}

async def next_project_for_designer(designer_id:int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT p.id, p.title, p.description, p.budget, p.styles, u.name, p.client_id
            FROM projects p
            JOIN users u ON u.user_id = p.client_id
            WHERE p.client_id != ?
              AND p.id NOT IN (
                  SELECT target_id FROM swipes WHERE viewer=? AND target_type='project'
              )
            ORDER BY RANDOM() LIMIT 1
            """,
            (designer_id, designer_id)
        )
        r = await cur.fetchone()
        if not r:
            return None
        pid, title, desc, budget, styles, client_name, client_id = r
        return {
            "id": pid, "title": title or "—", "description": desc or "—",
            "budget": budget or "—", "styles": styles or "—",
            "client_name": client_name or "—", "client_id": client_id
        }

@dp.message(F.text == "🔍 Найти дизайнера")
@dp.message(Command("find_designer"))
async def find_designer(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "client":
        await message.answer("Команда доступна только Заказчикам. Нажмите /start.")
        return
    card = await next_designer_for_client(message.from_user.id)
    if not card:
        await message.answer("Пока нет дизайнеров для показа.", reply_markup=kb_client_menu())
        return
    if card["photos"]:
        await message.answer_photo(card["photos"][0], caption=f"{card['name']}\nНавыки: {card['skills']}", reply_markup=kb_client_swipe())
    else:
        await message.answer(f"{card['name']}\nНавыки: {card['skills']}", reply_markup=kb_client_swipe())
    await state.update_data(curr_designer_id=card["user_id"])

@dp.message(F.text == "❤️ Нравится")
async def like_designer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    uid = data.get("curr_designer_id")
    if not uid:
        await message.answer("Откройте ленту: «🔍 Найти дизайнера».")
        return

    await record_swipe(message.from_user.id, "designer", int(uid), "like")
    match_id: Optional[int] = None

    # Взаимность: дизайнер ранее лайкнул какой-то проект этого клиента
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT 1 FROM swipes
            WHERE viewer=? AND target_type='project' AND action='like'
              AND target_id IN (SELECT id FROM projects WHERE client_id=?)
            """,
            (uid, message.from_user.id)
        )
        r = await cur.fetchone()
        if r:
            match_id = await create_match(message.from_user.id, int(uid))

    if match_id:
        await set_active_chat(message.from_user.id, match_id)
        await set_active_chat(int(uid), match_id)
        await message.answer("🎯 Матч! Можете начать общение 💬", reply_markup=kb_client_menu())
        try:
            await bot.send_message(int(uid), "✨ У вас новый матч! Заказчик заинтересован в сотрудничестве.", reply_markup=kb_designer_menu())
        except Exception as e:
            logger.warning(f"Не удалось уведомить дизайнера: {e}")
    else:
        try:
            await bot.send_message(int(uid), "💌 Кто-то заинтересовался вашим профилем! Зайдите в ленту проектов.", reply_markup=kb_designer_menu())
        except Exception as e:
            logger.warning(f"Не удалось уведомить дизайнера: {e}")

    card = await next_designer_for_client(message.from_user.id)
    if not card:
        await message.answer("Это был последний дизайнер.", reply_markup=kb_client_menu())
        await state.update_data(curr_designer_id=None)
        return
    if card["photos"]:
        try:
            await message.answer_media_group([InputMediaPhoto(media=fid) for fid in card["photos"]])
        except Exception:
            for fid in card["photos"]:
                await message.answer_photo(fid)
    await state.update_data(curr_designer_id=card["user_id"])
    await message.answer(f"{card['name']}\nНавыки: {card['skills']}", reply_markup=kb_client_swipe())

@dp.message(F.text == "→ Пропустить")
async def skip_designer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    uid = data.get("curr_designer_id")
    if not uid:
        await message.answer("Откройте ленту: «🔍 Найти дизайнера».")
        return
    await record_swipe(message.from_user.id, "designer", int(uid), "skip")
    card = await next_designer_for_client(message.from_user.id)
    if not card:
        await message.answer("Это был последний дизайнер.", reply_markup=kb_client_menu())
        await state.update_data(curr_designer_id=None)
        return
    if card["photos"]:
        try:
            await message.answer_media_group([InputMediaPhoto(media=fid) for fid in card["photos"]])
        except Exception:
            for fid in card["photos"]:
                await message.answer_photo(fid)
    await state.update_data(curr_designer_id=card["user_id"])
    await message.answer(f"{card['name']}\nНавыки: {card['skills']}", reply_markup=kb_client_swipe())

@dp.message(F.text == "📂 Портфолио")
async def view_portfolio(message: types.Message, state: FSMContext):
    data = await state.get_data()
    uid = data.get("curr_designer_id")
    if not uid:
        await message.answer("Сначала откройте карточку дизайнера.")
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT file_id FROM portfolio WHERE user_id=? ORDER BY id DESC", (int(uid),))
        rows = await cur.fetchall()
    if not rows:
        await message.answer("Портфолио пусто.", reply_markup=kb_client_swipe())
        return
    media = [InputMediaPhoto(media=r[0]) for r in rows[:10]]
    try:
        await message.answer_media_group(media)
    except Exception:
        for m in media:
            await message.answer_photo(m.media)

@dp.message(F.text == "🧭 Найти проект")
@dp.message(Command("find_project"))
async def find_project(message: types.Message, state: FSMContext):
    if await get_user_role(message.from_user.id) != "designer":
        await message.answer("Команда доступна только Дизайнерам. Нажмите /start.")
        return
    proj = await next_project_for_designer(message.from_user.id)
    if not proj:
        await message.answer("Пока нет проектов для показа.", reply_markup=kb_designer_menu())
        return
    caption = (
        f"{proj['title']}\n"
        f"{proj['description'][:300]}...\n"
        f"Бюджет: {proj['budget']}\n"
        f"Стили: {proj['styles']}"
    )
    await message.answer_photo("https://via.placeholder.com/600x400?text=Project", caption=caption, reply_markup=kb_designer_swipe())
    await state.update_data(curr_project_id=proj["id"], curr_project_client=proj["client_id"])

@dp.message(F.text == "ℹ️ Подробнее")
async def more_project(message: types.Message, state: FSMContext):
    data = await state.get_data()
    pid = data.get("curr_project_id")
    if not pid:
        await message.answer("Сначала откройте карточку проекта.", reply_markup=kb_designer_swipe())
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT title, description, budget, styles, refs FROM projects WHERE id=?", (int(pid),))
        r = await cur.fetchone()
    if not r:
        await message.answer("Проект не найден.", reply_markup=kb_designer_swipe())
        return
    title, desc, budget, styles, refs = r
    await message.answer(f"{title}\n\n{desc}\n\nБюджет: {budget}\nСтили: {styles}\nРеференсы: {refs}", reply_markup=kb_designer_swipe())

@dp.message(F.text == "✋ Я готов")
async def ready_for_project(message: types.Message, state: FSMContext):
    data = await state.get_data()
    pid = data.get("curr_project_id")
    client_id = data.get("curr_project_client")
    if not pid or client_id is None:
        await message.answer("Сначала откройте любой проект в ленте.")
        return

    await record_swipe(message.from_user.id, "project", int(pid), "like")
    match_id: Optional[int] = None

    # Взаимность: клиент лайкнул этого дизайнера
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT 1 FROM swipes
            WHERE viewer=? AND target_type='designer' AND action='like'
              AND target_id=?
            """,
            (int(client_id), message.from_user.id)
        )
        r = await cur.fetchone()
        if r:
            match_id = await create_match(int(client_id), message.from_user.id)

    if match_id:
        await set_active_chat(int(client_id), match_id)
        await set_active_chat(message.from_user.id, match_id)
        await message.answer("🎯 Матч! Можете начать общение 💬", reply_markup=kb_designer_menu())
        try:
            await bot.send_message(int(client_id), "✨ У вас новый матч! Дизайнер готов к работе.", reply_markup=kb_client_menu())
        except Exception as e:
            logger.warning(f"Не удалось уведомить заказчика: {e}")
    else:
        try:
            await bot.send_message(int(client_id), "💌 Дизайнер проявил интерес к вашему проекту! Зайдите в ленту дизайнеров.", reply_markup=kb_client_menu())
        except Exception as e:
            logger.warning(f"Не удалось уведомить заказчика: {e}")

    proj = await next_project_for_designer(message.from_user.id)
    if not proj:
        await message.answer("Это был последний проект.", reply_markup=kb_designer_menu())
        await state.update_data(curr_project_id=None, curr_project_client=None)
        return
    await state.update_data(curr_project_id=proj["id"], curr_project_client=proj["client_id"])
    await message.answer(
        f"{proj['title']}\n{proj['description'][:300]}...\nБюджет: {proj['budget']}\nСтили: {proj['styles']}",
        reply_markup=kb_designer_swipe()
    )

@dp.message(F.text == "→ Не интересно")
async def not_interested(message: types.Message, state: FSMContext):
    data = await state.get_data()
    pid = data.get("curr_project_id")
    if not pid:
        await message.answer("Сначала откройте любой проект в ленте.")
        return
    await record_swipe(message.from_user.id, "project", int(pid), "skip")
    proj = await next_project_for_designer(message.from_user.id)
    if not proj:
        await message.answer("Это был последний проект.", reply_markup=kb_designer_menu())
        await state.update_data(curr_project_id=None, curr_project_client=None)
        return
    await state.update_data(curr_project_id=proj["id"], curr_project_client=proj["client_id"])
    await message.answer(
        f"{proj['title']}\n{proj['description'][:300]}...\nБюджет: {proj['budget']}\nСтили: {proj['styles']}",
        reply_markup=kb_designer_swipe()
    )

# ====================== Settings, Status, Back ======================
@dp.message(F.text == "🟢 Статус")
async def status_menu(message: types.Message):
    await message.answer("Выберите статус:", reply_markup=kb_status())

@dp.message(F.text.in_({"🟢 В поиске", "🟡 Занят", "🔴 Не активен"}))
async def set_status(message: types.Message):
    mapping = {"🟢 В поиске": "active", "🟡 Занят": "busy", "🔴 Не активен": "inactive"}
    val = mapping.get(message.text)
    if not val:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET status=? WHERE user_id=?", (val, message.from_user.id))
        await db.commit()
    await message.answer("Статус обновлён ✅")

@dp.message(F.text == "⚙️ Настройки")
async def settings_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Настройки:", reply_markup=kb_settings())

@dp.message(F.text == "🔁 Сменить роль")
async def change_role(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Выберите новую роль:", reply_markup=kb_role())

@dp.message(F.text == "◀︎ Назад")
async def go_back(message: types.Message, state: FSMContext):
    await state.clear()
    role = await get_user_role(message.from_user.id)
    if role == "designer":
        await message.answer("Главное меню:", reply_markup=kb_designer_menu())
    elif role == "client":
        await message.answer("Главное меню:", reply_markup=kb_client_menu())
    else:
        await message.answer("Привет! Кто вы по роли?", reply_markup=kb_role())

# ====================== Chat relay & Leave ======================
async def close_chat_for(user_id:int):
    partner = await get_match_partner(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM active_chat WHERE user_id=?", (user_id,))
        if partner:
            await db.execute("DELETE FROM active_chat WHERE user_id=?", (partner,))
        await db.commit()
    if partner:
        try:
            role_partner = await get_user_role(partner)
            menu_partner = kb_designer_menu() if role_partner == "designer" else kb_client_menu()
            await bot.send_message(chat_id=partner, text="Партнёр завершил диалог.", reply_markup=menu_partner)
        except Exception:
            pass

@dp.message(F.text == "🚪 Завершить диалог")
async def leave_dialog(message: types.Message):
    await close_chat_for(message.from_user.id)
    role = await get_user_role(message.from_user.id)
    menu = kb_designer_menu() if role == "designer" else kb_client_menu()
    await message.answer("Диалог завершён.", reply_markup=menu)

@dp.message()
async def relay(message: types.Message):
    control_texts = {
        "Я — Дизайнер 🎨","Я — Заказчик 💼",
        "🧭 Найти проект","🔍 Найти дизайнера",
        "🧾 Мой профиль","✏️ Изменить профиль",
        "🟢 Статус","⚙️ Настройки","🔁 Сменить роль",
        "❤️ Нравится","→ Пропустить","📂 Портфолио",
        "✋ Я готов","→ Не интересно","ℹ️ Подробнее",
        "Готово","Пропустить","◀︎ Назад","🚪 Завершить диалог",
        "Имя","Навыки","Портфолио (ссылка)","Загрузить новые работы","Всё заново",
        "Название проекта","Описание","Бюджет","Стили","Референсы"
    }
    if message.text and (message.text.startswith("/") or message.text in control_texts):
        return
    partner = await get_match_partner(message.from_user.id)
    if not partner:
        return
    try:
        if message.photo:
            await bot.send_photo(chat_id=partner, photo=message.photo[-1].file_id, caption=f"От {message.from_user.full_name}")
            await message.answer("Отправлено партнёру")
        elif message.video:
            await bot.send_video(chat_id=partner, video=message.video.file_id, caption=f"От {message.from_user.full_name}")
            await message.answer("Отправлено партнёру")
        elif message.text:
            await bot.send_message(chat_id=partner, text=f"От {message.from_user.full_name}: {message.text}")
            await message.answer("Отправлено партнёру")
    except Exception as e:
        logger.exception("Relay failed: %s", e)

# ====================== Run ======================
async def on_startup():
    await init_db()
    logger.info("Bot ready")

async def main():
    await on_startup()
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
