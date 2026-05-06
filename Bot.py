import asyncio
import logging

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIG =================
API_TOKEN = "8490029817:AAEdacEaTmkZoIXG57L_BDexWWVPlMFGMHc"
ADMIN_ID = 8570832903

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

# ================= DATABASE =================
users = set()
settings = {
    "price": "25",
    "qr": "https://via.placeholder.com/300.png"
}

# ================= STATES =================
class OrderStates(StatesGroup):
    waiting_for_screenshot = State()
    waiting_for_details = State()

class AdminStates(StatesGroup):
    waiting_for_number = State()

# ================= KEYBOARDS =================
def main_menu(price):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Buy ₹{price}", callback_data="buy_now")]
    ])

def verify_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Send to Admin", callback_data="send_admin")]
    ])

def admin_kb(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{user_id}")
        ]
    ])

# ================= FUNCTIONS =================
async def add_user(user_id):
    users.add(user_id)

async def get_users():
    return list(users)

async def get_setting(key):
    return settings.get(key)

# ================= USER FLOW =================
@dp.message(Command("start"))
async def start(message: types.Message):
    await add_user(message.from_user.id)

    msg = await message.answer("⚡ Loading...")
    await asyncio.sleep(2)
    await msg.delete()

    price = await get_setting("price")

    await message.answer(
        f"🚀 Welcome\n\n💰 Price: ₹{price}",
        reply_markup=main_menu(price)
    )

# BUY
@dp.callback_query(F.data == "buy_now")
async def buy(callback: types.CallbackQuery, state: FSMContext):
    price = await get_setting("price")
    qr = await get_setting("qr")

    await callback.message.answer_photo(
        photo=qr,
        caption=f"💰 Pay ₹{price}\n\nSend screenshot after payment"
    )

    await state.set_state(OrderStates.waiting_for_screenshot)

# SCREENSHOT
@dp.message(OrderStates.waiting_for_screenshot, F.photo)
async def screenshot(message: types.Message, state: FSMContext):
    await state.update_data(file_id=message.photo[-1].file_id)
    await message.answer("📝 Send details (Example: WhatsApp, 1 qty)")
    await state.set_state(OrderStates.waiting_for_details)

# DETAILS
@dp.message(OrderStates.waiting_for_details)
async def details(message: types.Message, state: FSMContext):
    username = message.from_user.username
    username = f"@{username}" if username else "No Username"

    await state.update_data(
        user_id=message.from_user.id,
        username=username,
        details=message.text
    )

    await message.answer(
        "✅ Details saved\nClick below to send to admin",
        reply_markup=verify_kb()
    )

# SEND TO ADMIN
@dp.callback_query(F.data == "send_admin")
async def send_admin(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()

    caption = (
        f"🔔 New Order\n\n"
        f"👤 {data['username']}\n"
        f"📝 {data['details']}\n"
        f"🆔 {data['user_id']}"
    )

    await bot.send_photo(
        ADMIN_ID,
        data['file_id'],
        caption=caption,
        reply_markup=admin_kb(data['user_id'])
    )

    await callback.message.edit_text("📤 Sent to admin")
    await state.clear()

# ================= ADMIN =================
@dp.message(Command("admin"))
async def admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    users_list = await get_users()
    await message.answer(f"👨‍💻 Admin Panel\nUsers: {len(users_list)}")

# APPROVE
@dp.callback_query(F.data.startswith("approve_"))
async def approve(callback: types.CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[1])

    await state.update_data(user_id=user_id)
    await callback.message.answer("📤 Send number:")
    await state.set_state(AdminStates.waiting_for_number)

# SEND NUMBER
@dp.message(AdminStates.waiting_for_number)
async def send_number(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("user_id")

    if not user_id:
        await message.answer("❌ Error")
        return

    await bot.send_message(
        user_id,
        f"🎉 Payment Verified\n\nNumber:\n{message.text}"
    )

    await message.answer("✅ Sent")
    await state.clear()

# REJECT
@dp.callback_query(F.data.startswith("reject_"))
async def reject(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])

    await bot.send_message(user_id, "❌ Payment rejected")
    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ Rejected"
    )

# ================= MAIN =================
async def main():
    logging.basicConfig(level=logging.INFO)
    print("🚀 Bot running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
