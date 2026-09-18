# Platina | Kimyo — referral + masala yuborish + admin reply

import asyncio
import html
import sqlite3
from urllib.parse import urlencode

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = "8812092136:AAGT1AoIDPzG1d9rkZCSoDedktcLEBRQuJI"
CHANNEL_ID = "@platina_kimyo"
CHANNEL_USERNAME = "platina_kimyo"
ADMIN_IDS = {6365300596}
DB_NAME = "platina_referral.db"
REQUIRED_REFERRALS = 4

bot = Bot(token=TOKEN)
dp = Dispatcher()


def db():
    return sqlite3.connect(DB_NAME)


def init_db():
    con = db()
    c = con.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        invite_link TEXT UNIQUE,
        referrals INTEGER DEFAULT 0,
        qualified INTEGER DEFAULT 0,
        awaiting_problem INTEGER DEFAULT 0
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS referrals(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inviter_id INTEGER NOT NULL,
        invited_id INTEGER NOT NULL UNIQUE,
        invite_link TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS problem_messages(
        admin_chat_id INTEGER NOT NULL,
        admin_message_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        PRIMARY KEY(admin_chat_id, admin_message_id))""")
    con.commit()
    con.close()


def get_user(uid):
    con = db()
    c = con.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    r = c.fetchone()
    con.close()
    return r


def create_user(uid, username, first_name):
    con = db()
    c = con.cursor()
    c.execute(
        """INSERT INTO users(user_id, username, first_name)
           VALUES(?,?,?)
           ON CONFLICT(user_id) DO UPDATE SET
           username=excluded.username,
           first_name=excluded.first_name""",
        (uid, username, first_name)
    )
    con.commit()
    con.close()


def set_invite(uid, link):
    con = db()
    c = con.cursor()
    c.execute("UPDATE users SET invite_link=? WHERE user_id=?", (link, uid))
    con.commit()
    con.close()


def user_by_invite(link):
    con = db()
    c = con.cursor()
    c.execute("SELECT * FROM users WHERE invite_link=?", (link,))
    r = c.fetchone()
    con.close()
    return r


def add_referral(inviter, invited, link):
    con = db()
    c = con.cursor()
    try:
        c.execute(
            "INSERT INTO referrals(inviter_id, invited_id, invite_link) VALUES(?,?,?)",
            (inviter, invited, link)
        )
        c.execute(
            "UPDATE users SET referrals=referrals+1 WHERE user_id=?",
            (inviter,)
        )
        con.commit()
        c.execute("SELECT referrals FROM users WHERE user_id=?", (inviter,))
        r = c.fetchone()
        con.close()
        return r[0] if r else None
    except sqlite3.IntegrityError:
        con.rollback()
        con.close()
        return None


def set_awaiting(uid, value):
    con = db()
    c = con.cursor()
    c.execute("UPDATE users SET awaiting_problem=? WHERE user_id=?", (value, uid))
    con.commit()
    con.close()


def qualify(uid):
    con = db()
    c = con.cursor()
    c.execute("UPDATE users SET qualified=1 WHERE user_id=?", (uid,))
    con.commit()
    con.close()


def save_problem(admin_chat, admin_msg, uid):
    con = db()
    c = con.cursor()
    c.execute(
        "INSERT OR REPLACE INTO problem_messages VALUES(?,?,?)",
        (admin_chat, admin_msg, uid)
    )
    con.commit()
    con.close()


def problem_owner(admin_chat, admin_msg):
    con = db()
    c = con.cursor()
    c.execute(
        "SELECT user_id FROM problem_messages WHERE admin_chat_id=? AND admin_message_id=?",
        (admin_chat, admin_msg)
    )
    r = c.fetchone()
    con.close()
    return r[0] if r else None


def keyboard(uid):
    u = get_user(uid)
    if not u:
        return None

    b = InlineKeyboardBuilder()

    if u[5]:
        b.button(text="🧪 Masalamni yuborish", callback_data="send_problem")

    b.button(text="📊 Mening natijam", callback_data="status")
    b.button(text="📤 Do‘stlarga yuborish", callback_data="share")
    b.adjust(1)

    return b.as_markup()


@dp.message(CommandStart())
async def start(message: Message):
    u = message.from_user
    create_user(u.id, u.username, u.first_name)
    row = get_user(u.id)

    if not row[3]:
        try:
            invite = await bot.create_chat_invite_link(
                chat_id=CHANNEL_ID,
                name=f"ref_{u.id}",
                creates_join_request=False
            )
            set_invite(u.id, invite.invite_link)
            link = invite.invite_link
        except Exception as e:
            print("Invite link xatoligi:", e)
            await message.answer(
                "❌ Shaxsiy taklif havolasi yaratilmadi. "
                "Bot kanal administratori va invite-link yaratish huquqiga ega ekanini tekshiring."
            )
            return
    else:
        link = row[3]

    row = get_user(u.id)

    await message.answer(
        "🧪 <b>PLATINA | KIMYO</b>\n\n"
        "Kimyodan masalalarni <b>bepul yechim va tahlil</b> qiling!\n\n"
        "📚 <b>Kanalimizda siz uchun:</b>\n"
        "• 🧪 Kimyodan masala va ularning yechimlari\n"
        "• 📖 Foydali kimyoviy ma’lumotlar\n"
        "• 📑 Qo‘llanmalar va o‘quv materiallari\n"
        "• 💡 Kimyoni osonroq o‘rganishga yordam beradigan materiallar bo'ladi\n\n"
        "🎁 4 ta do‘stingizni shaxsiy havolangiz orqali kanalga taklif qiling "
        "va o‘z masalangizni bepul tahlil qildiring.\n\n"
        f"👥 Natija: <b>{row[4]}/{REQUIRED_REFERRALS}</b>\n\n"
        f"🔗 <b>Shaxsiy havolangiz:</b> {link}",
        parse_mode="HTML",
        reply_markup=keyboard(u.id)
    )


@dp.callback_query(F.data == "share")
async def share(cb: CallbackQuery):
    u = get_user(cb.from_user.id)

    if not u:
        return await cb.answer("Avval /start bosing.", show_alert=True)

    share_url = "https://t.me/share/url?" + urlencode({
        "url": u[3],
        "text": (
            "🧪 PLATINA | KIMYO kanaliga qo‘shiling!\n\n"
            "📚 Kimyodan foydali ma’lumotlar, qo‘llanmalar, "
            "o‘quv materiallari va masalalar yechimlari.\n\n"
            "🎁 4 ta do‘stingizni taklif qilsangiz, "
            "o‘zingizning kimyo masalangizni bepul tahlil qildirasiz! 👇"
        )
    })

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Telegram orqali yuborish", url=share_url)],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back")]
    ])

    await cb.message.edit_text(
        f"📤 <b>Do‘stlaringizga yuboring</b>\n\n"
        f"👥 Hozirgi natija: <b>{u[4]}/{REQUIRED_REFERRALS}</b>",
        parse_mode="HTML",
        reply_markup=kb
    )
    await cb.answer()


@dp.callback_query(F.data == "status")
async def status(cb: CallbackQuery):
    u = get_user(cb.from_user.id)

    if not u:
        return await cb.answer("Avval /start bosing.", show_alert=True)

    if u[5]:
        text = (
            "🎉 <b>Tabriklaymiz!</b>\n\n"
            "Siz 4 ta do‘stingizni taklif qildingiz.\n"
            "🧪 Endi masalangizni yuborishingiz mumkin."
        )
    else:
        text = (
            f"📊 <b>Sizning natijangiz</b>\n\n"
            f"👥 Taklif qilinganlar: <b>{u[4]}/{REQUIRED_REFERRALS}</b>\n"
            f"🎯 Qolgan: <b>{max(0, REQUIRED_REFERRALS-u[4])}</b> ta"
        )

    await cb.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard(cb.from_user.id)
    )
    await cb.answer()


@dp.callback_query(F.data == "send_problem")
async def send_problem(cb: CallbackQuery):
    u = get_user(cb.from_user.id)

    if not u or not u[5]:
        return await cb.answer(
            "Avval 4 ta odamni taklif qilishingiz kerak.",
            show_alert=True
        )

    set_awaiting(cb.from_user.id, 1)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_problem")]
    ])

    await cb.message.answer(
        "🧪 <b>Masalangizni yuboring</b>\n\n"
        "📷 Rasm yoki 📝 matn ko‘rinishida yuborishingiz mumkin.\n\n"
        "Masala adminimizga avtomatik yuboriladi.",
        parse_mode="HTML",
        reply_markup=kb
    )
    await cb.answer()


@dp.callback_query(F.data == "cancel_problem")
async def cancel(cb: CallbackQuery):
    set_awaiting(cb.from_user.id, 0)

    await cb.message.edit_text(
        "❌ <b>Masala yuborish bekor qilindi.</b>",
        parse_mode="HTML",
        reply_markup=keyboard(cb.from_user.id)
    )
    await cb.answer()


async def notify_admins(uid, message: Message, caption: str):
    sent = False

    for aid in ADMIN_IDS:
        if aid == 0:
            continue

        try:
            if message.photo:
                x = await bot.send_photo(
                    aid,
                    message.photo[-1].file_id,
                    caption=caption,
                    parse_mode="HTML"
                )
            else:
                x = await bot.send_message(
                    aid,
                    caption,
                    parse_mode="HTML"
                )

            save_problem(aid, x.message_id, uid)
            sent = True

        except Exception as e:
            print(f"Admin {aid} ga yuborishda xato:", e)

    return sent


# Admin reply handler generic message/photo handlerlardan oldin turadi.
@dp.message(F.reply_to_message)
async def admin_reply(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    uid = problem_owner(message.chat.id, message.reply_to_message.message_id)

    if not uid:
        return

    try:
        if message.text:
            await bot.send_message(
                uid,
                "🧪 <b>PLATINA | KIMYO — MASALA YECHIMI</b>\n\n"
                + html.escape(message.text),
                parse_mode="HTML"
            )
        elif message.photo:
            await bot.send_photo(
                uid,
                message.photo[-1].file_id,
                caption="🧪 <b>PLATINA | KIMYO — MASALA YECHIMI</b>",
                parse_mode="HTML"
            )
        elif message.document:
            await bot.send_document(
                uid,
                message.document.file_id,
                caption="🧪 PLATINA | KIMYO — MASALA YECHIMI"
            )
        else:
            await bot.copy_message(uid, message.chat.id, message.message_id)

        await message.answer("✅ Javob foydalanuvchiga yuborildi.")

    except Exception as e:
        print("Admin reply xatosi:", e)
        await message.answer("❌ Javobni yuborishda xatolik yuz berdi.")


@dp.message(F.photo)
async def photo_problem(message: Message):
    u = get_user(message.from_user.id)

    if not u or not u[5] or not u[6]:
        return

    username = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else "Username yo‘q"
    )

    cap = (
        "🧪 <b>YANGI MASALA</b>\n\n"
        f"👤 Ism: {html.escape(message.from_user.full_name)}\n"
        f"🔹 Username: {html.escape(username)}\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"👥 Referral: <b>{u[4]}/{REQUIRED_REFERRALS}</b>\n\n"
        "📷 Abiturient yuborgan masala.\n\n"
        "↩️ <i>Javob berish uchun shu xabarga REPLY qiling.</i>"
    )

    if await notify_admins(message.from_user.id, message, cap):
        set_awaiting(message.from_user.id, 0)
        await message.answer(
            "✅ <b>Masalangiz qabul qilindi!</b>\n\n"
            "Yechim tayyor bo‘lgach, javob shu bot orqali sizga yuboriladi.",
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Masalani yuborishda xatolik yuz berdi.")


@dp.message(F.text)
async def text_problem(message: Message):
    if message.text.startswith("/"):
        return

    u = get_user(message.from_user.id)

    if not u or not u[5] or not u[6]:
        return

    username = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else "Username yo‘q"
    )

    cap = (
        "🧪 <b>YANGI MASALA</b>\n\n"
        f"👤 Ism: {html.escape(message.from_user.full_name)}\n"
        f"🔹 Username: {html.escape(username)}\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"👥 Referral: <b>{u[4]}/{REQUIRED_REFERRALS}</b>\n\n"
        f"📝 <b>Masala:</b>\n{html.escape(message.text)}\n\n"
        "↩️ <i>Javob berish uchun shu xabarga REPLY qiling.</i>"
    )

    if await notify_admins(message.from_user.id, message, cap):
        set_awaiting(message.from_user.id, 0)
        await message.answer(
            "✅ <b>Masalangiz qabul qilindi!</b>\n\n"
            "Yechim tayyor bo‘lgach, javob shu bot orqali sizga yuboriladi.",
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Masalani yuborishda xatolik yuz berdi.")


@dp.message(Command("myid", "id"))
async def myid(message: Message):
    await message.answer(
        f"🆔 Telegram ID: <code>{message.from_user.id}</code>",
        parse_mode="HTML"
    )


@dp.message(Command("stats"))
async def stats(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    con = db()
    c = con.cursor()

    c.execute("SELECT COUNT(*) FROM users")
    users = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM referrals")
    refs = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM users WHERE qualified=1")
    q = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM users WHERE awaiting_problem=1")
    w = c.fetchone()[0]

    con.close()

    await message.answer(
        f"📊 <b>PLATINA STATISTIKA</b>\n\n"
        f"👤 Foydalanuvchilar: <b>{users}</b>\n"
        f"👥 Jami referral: <b>{refs}</b>\n"
        f"🎓 4/4 qilganlar: <b>{q}</b>\n"
        f"🧪 Masala yuborayotganlar: <b>{w}</b>",
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "back")
async def back(cb: CallbackQuery):
    u = get_user(cb.from_user.id)

    if u:
        await cb.message.edit_text(
            f"🧪 <b>PLATINA | KIMYO</b>\n\n"
            f"Kerakli bo‘limni tanlang.\n\n"
            f"👥 Natija: <b>{u[4]}/{REQUIRED_REFERRALS}</b>",
            parse_mode="HTML",
            reply_markup=keyboard(cb.from_user.id)
        )

    await cb.answer()


@dp.chat_member()
async def channel_member(update: ChatMemberUpdated):
    if (
        update.chat.username
        and update.chat.username.lower() != CHANNEL_USERNAME.lower()
    ):
        return

    old = update.old_chat_member.status
    new = update.new_chat_member.status

    was = old in {"member", "administrator", "creator"}
    ismem = new in {"member", "administrator", "creator"}

    if was or not ismem or not update.invite_link:
        return

    link = update.invite_link.invite_link
    inviter = user_by_invite(link)

    if not inviter:
        print("Referral egasi topilmadi:", link)
        return

    invited = update.new_chat_member.user.id

    if inviter[0] == invited:
        return

    count = add_referral(inviter[0], invited, link)

    if count is None:
        return

    print(
        f"REFERRAL: {inviter[0]} -> {invited} = "
        f"{count}/{REQUIRED_REFERRALS}"
    )

    if count >= REQUIRED_REFERRALS:
        qualify(inviter[0])

        await bot.send_message(
            inviter[0],
            "🎉 <b>TABRIKLAYMIZ!</b>\n\n"
            "Siz 4 ta odamni muvaffaqiyatli taklif qildingiz!\n\n"
            "🧪 Endi masalangizni yuborishingiz mumkin.",
            parse_mode="HTML",
            reply_markup=keyboard(inviter[0])
        )
    else:
        await bot.send_message(
            inviter[0],
            f"🎉 Yangi odam qo‘shildi!\n\n"
            f"👥 Natijangiz: <b>{count}/{REQUIRED_REFERRALS}</b>\n"
            f"🎯 Qolgan: <b>{REQUIRED_REFERRALS-count}</b> ta",
            parse_mode="HTML",
            reply_markup=keyboard(inviter[0])
        )


async def main():
    init_db()
    print("🤖 Platina referral bot ishga tushdi...")
    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Bot to‘xtatildi.")
