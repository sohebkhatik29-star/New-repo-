import logging
from pyrogram import Client, filters, enums
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    Message
)
from database.users_chats_db import db
from info import ADMINS, INITIAL_ADMINS, QR_CODE, OWNER_UPI_ID, SUBSCRIPTION
from Script import script

logger = logging.getLogger(__name__)

# Fast In-memory state tracking
ADMIN_PREM_STATE = {}

def is_admin(user_id: int) -> bool:
    try:
        uid = int(user_id)
        if uid in ADMINS or str(uid) in [str(a) for a in ADMINS]:
            return True
        if uid in INITIAL_ADMINS or str(uid) in [str(a) for a in INITIAL_ADMINS]:
            return True
        return False
    except Exception:
        return False

async def get_premium_panel_markup(cfg: dict) -> InlineKeyboardMarkup:
    is_on = cfg.get("is_enabled", False)
    status_icon = "🟢 ON" if is_on else "🔴 OFF"
    toggle_text = f"🔘 ᴘʀᴇᴍɪᴜᴍ ᴍᴏᴅᴇ: {status_icon}"

    buttons = [
        [
            InlineKeyboardButton(toggle_text, callback_data="prem_toggle_mode")
        ],
        [
            InlineKeyboardButton("📝 ꜱᴇᴛ ᴘʀᴇᴍɪᴜᴍ ᴛᴇxᴛ", callback_data="prem_set_text"),
            InlineKeyboardButton("🖼️ ꜱᴇᴛ ǫʀ ᴄᴏᴅᴇ", callback_data="prem_set_qr")
        ],
        [
            InlineKeyboardButton("💳 ꜱᴇᴛ ᴜᴘɪ ɪᴅ", callback_data="prem_set_upi"),
            InlineKeyboardButton("📸 ꜱᴇᴛ ꜱᴄʀᴇᴇɴꜱʜᴏᴛ ɪᴅ", callback_data="prem_set_owner")
        ],
        [
            InlineKeyboardButton("👁️ ᴘʀᴇᴠɪᴇᴡ ᴘʟᴀɴ ᴄᴀʀᴅ", callback_data="prem_preview_plan")
        ],
        [
            InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ", callback_data="admin_settings")
        ]
    ]
    return InlineKeyboardMarkup(buttons)

async def build_premium_panel_text(cfg: dict) -> str:
    is_on = cfg.get("is_enabled", False)
    status_str = "🟢 <b>ACTIVE (Users Must Buy Premium for Movies)</b>" if is_on else "🔴 <b>DISABLED (Users Get Movies Directly)</b>"
    
    plan_txt = cfg.get("plan_text")
    plan_preview = (plan_txt[:80] + "...") if plan_txt else "<i>Default Template</i>"
    
    qr = cfg.get("qr_code") or QR_CODE or "<i>Not Set</i>"
    qr_preview = "Custom Photo/Link Set ✅" if cfg.get("qr_code") else f"<code>{QR_CODE}</code>"
    
    upi = cfg.get("upi_id") or OWNER_UPI_ID or "<i>Not Set</i>"
    screenshot_user = cfg.get("screenshot_user") or "Movies_1783"

    text = (
        "💎 <b><u>Premium Plan & Payment Control Panel</u></b>\n\n"
        f"⚡ <b>Premium Gate Status:</b> {status_str}\n\n"
        f"💳 <b>Active UPI ID:</b> <code>{upi}</code>\n"
        f"🖼️ <b>QR Code:</b> {qr_preview}\n"
        f"📸 <b>Screenshot Contact:</b> @{screenshot_user.replace('@', '')}\n"
        f"📝 <b>Plan Text:</b> {plan_preview}\n\n"
        "<i>Select any button below to update settings:</i>"
    )
    return text

# =========================================================================
# Main Premium Panel Callback
# =========================================================================
@Client.on_callback_query(filters.regex(r"^admin_premium_panel$"))
async def admin_premium_panel_cb(client: Client, query: CallbackQuery):
    if not is_admin(query.from_user.id):
        return await query.answer("⛔️ Access Denied!", show_alert=True)
    
    ADMIN_PREM_STATE.pop(query.from_user.id, None)
    await db.clear_admin_prem_state(query.from_user.id)
    cfg = await db.get_premium_config()
    text = await build_premium_panel_text(cfg)
    markup = await get_premium_panel_markup(cfg)
    
    try:
        await query.message.delete()
    except Exception:
        pass
    
    await client.send_message(
        chat_id=query.message.chat.id,
        text=text,
        reply_markup=markup
    )
    await query.answer()

# =========================================================================
# Toggle Premium Mode ON/OFF
# =========================================================================
@Client.on_callback_query(filters.regex(r"^prem_toggle_mode$"))
async def prem_toggle_mode_cb(client: Client, query: CallbackQuery):
    if not is_admin(query.from_user.id):
        return await query.answer("⛔️ Access Denied!", show_alert=True)
    
    new_state = await db.toggle_premium_mode()
    cfg = await db.get_premium_config()
    text = await build_premium_panel_text(cfg)
    markup = await get_premium_panel_markup(cfg)
    
    try:
        await query.message.edit_text(text, reply_markup=markup)
    except Exception:
        try:
            await query.message.delete()
        except Exception:
            pass
        await client.send_message(query.message.chat.id, text, reply_markup=markup)
    
    status_msg = "🟢 Premium Mode ENABLED! Users will see plan before getting movies." if new_state else "🔴 Premium Mode DISABLED! Users will get movies directly."
    await query.answer(status_msg, show_alert=True)

# =========================================================================
# Set Premium Plan Text Prompt
# =========================================================================
@Client.on_callback_query(filters.regex(r"^prem_set_text$"))
async def prem_set_text_cb(client: Client, query: CallbackQuery):
    if not is_admin(query.from_user.id):
        return await query.answer("⛔️ Access Denied!", show_alert=True)
    
    prompt = (
        "📝 <b><u>Set Premium Plan Message</u></b>\n\n"
        "Please send the new <b>Premium Plan Text / Description</b> now.\n\n"
        "You can include your prices, validity days, payment instructions and emojis (HTML formatting supported).\n\n"
        "<i>Click Cancel below to abort.</i>"
    )
    cancel_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚫 ᴄᴀɴᴄᴇʟ", callback_data="prem_cancel")]
    ])
    
    try:
        await query.message.delete()
    except Exception:
        pass
    
    sent = await client.send_message(query.message.chat.id, prompt, reply_markup=cancel_markup)
    state_data = {
        "step": "WAITING_PREM_TEXT",
        "prompt_msg_id": sent.id
    }
    ADMIN_PREM_STATE[query.from_user.id] = state_data
    await db.set_admin_prem_state(query.from_user.id, state_data)
    await query.answer()

# =========================================================================
# Set QR Code Photo Prompt
# =========================================================================
@Client.on_callback_query(filters.regex(r"^prem_set_qr$"))
async def prem_set_qr_cb(client: Client, query: CallbackQuery):
    if not is_admin(query.from_user.id):
        return await query.answer("⛔️ Access Denied!", show_alert=True)
    
    prompt = (
        "🖼️ <b><u>Set Payment QR Code Photo</u></b>\n\n"
        "Please send your <b>Payment QR Code Image / Photo</b> (or a direct image URL) now.\n\n"
        "<i>Click Cancel below to abort.</i>"
    )
    cancel_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚫 ᴄᴀɴᴄᴇʟ", callback_data="prem_cancel")]
    ])
    
    try:
        await query.message.delete()
    except Exception:
        pass
    
    sent = await client.send_message(query.message.chat.id, prompt, reply_markup=cancel_markup)
    state_data = {
        "step": "WAITING_PREM_QR",
        "prompt_msg_id": sent.id
    }
    ADMIN_PREM_STATE[query.from_user.id] = state_data
    await db.set_admin_prem_state(query.from_user.id, state_data)
    await query.answer()

# =========================================================================
# Set UPI ID Prompt
# =========================================================================
@Client.on_callback_query(filters.regex(r"^prem_set_upi$"))
async def prem_set_upi_cb(client: Client, query: CallbackQuery):
    if not is_admin(query.from_user.id):
        return await query.answer("⛔️ Access Denied!", show_alert=True)
    
    prompt = (
        "💳 <b><u>Set Payment UPI ID</u></b>\n\n"
        "Please send the new <b>UPI ID</b> now (e.g. <code>delhisehoon1782@ptyes</code>).\n\n"
        "<i>Click Cancel below to abort.</i>"
    )
    cancel_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚫 ᴄᴀɴᴄᴇʟ", callback_data="prem_cancel")]
    ])
    
    try:
        await query.message.delete()
    except Exception:
        pass
    
    sent = await client.send_message(query.message.chat.id, prompt, reply_markup=cancel_markup)
    state_data = {
        "step": "WAITING_PREM_UPI",
        "prompt_msg_id": sent.id
    }
    ADMIN_PREM_STATE[query.from_user.id] = state_data
    await db.set_admin_prem_state(query.from_user.id, state_data)
    await query.answer()

# =========================================================================
# Set Screenshot Owner Username Prompt
# =========================================================================
@Client.on_callback_query(filters.regex(r"^prem_set_owner$"))
async def prem_set_owner_cb(client: Client, query: CallbackQuery):
    if not is_admin(query.from_user.id):
        return await query.answer("⛔️ Access Denied!", show_alert=True)
    
    prompt = (
        "📸 <b><u>Set Send Payment Screenshot Username</u></b>\n\n"
        "Please send the <b>Telegram Username</b> or Link where users should send payment screenshots (e.g. <code>Movies_1783</code> or <code>@Movies_1783</code>).\n\n"
        "A button <b>'📸 ꜱᴇɴᴅ ᴘᴀʏᴍᴇɴᴛ ꜱᴄʀᴇᴇɴꜱʜᴏᴛ'</b> will open this username in 1-click for users.\n\n"
        "<i>Click Cancel below to abort.</i>"
    )
    cancel_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚫 ᴄᴀɴᴄᴇʟ", callback_data="prem_cancel")]
    ])
    
    try:
        await query.message.delete()
    except Exception:
        pass
    
    sent = await client.send_message(query.message.chat.id, prompt, reply_markup=cancel_markup)
    state_data = {
        "step": "WAITING_PREM_OWNER",
        "prompt_msg_id": sent.id
    }
    ADMIN_PREM_STATE[query.from_user.id] = state_data
    await db.set_admin_prem_state(query.from_user.id, state_data)
    await query.answer()

# =========================================================================
# Cancel Action Callback
# =========================================================================
@Client.on_callback_query(filters.regex(r"^prem_cancel$"))
async def prem_cancel_cb(client: Client, query: CallbackQuery):
    if not is_admin(query.from_user.id):
        return await query.answer("⛔️ Access Denied!", show_alert=True)
    
    ADMIN_PREM_STATE.pop(query.from_user.id, None)
    await db.clear_admin_prem_state(query.from_user.id)
    cfg = await db.get_premium_config()
    text = await build_premium_panel_text(cfg)
    markup = await get_premium_panel_markup(cfg)
    
    try:
        await query.message.delete()
    except Exception:
        pass
    
    await client.send_message(query.message.chat.id, text, reply_markup=markup)
    await query.answer("Action Cancelled")

# =========================================================================
# Preview Premium Plan Card
# =========================================================================
@Client.on_callback_query(filters.regex(r"^prem_preview_plan$"))
async def prem_preview_plan_cb(client: Client, query: CallbackQuery):
    if not is_admin(query.from_user.id):
        return await query.answer("⛔️ Access Denied!", show_alert=True)
    
    cfg = await db.get_premium_config()
    upi_id = cfg.get("upi_id") or OWNER_UPI_ID or "delhisehoon1782@ptyes"
    owner_user = (cfg.get("screenshot_user") or "Movies_1783").replace("@", "").strip()
    qr_media = cfg.get("qr_code") or QR_CODE or SUBSCRIPTION
    
    custom_plan_text = cfg.get("plan_text")
    if not custom_plan_text:
        caption = (
            f"👑 <b><u>PREMIUM SUBSCRIPTION PLANS</u></b>\n\n"
            f"🌟 <b>Direct Downloads Without Waiting</b>\n"
            f"⚡ <b>Fast Speed & No Ads</b>\n"
            f"🍿 <b>Full Movies & Web Series Access</b>\n\n"
            f"💳 <b>Pay via UPI:</b> <code>{upi_id}</code>\n"
            f"📸 <i>Scan the QR Code above to pay, then click below to send the screenshot!</i>"
        )
    else:
        caption = custom_plan_text
    
    preview_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📸 ꜱᴇɴᴅ ᴘᴀʏᴍᴇɴᴛ ꜱᴄʀᴇᴇɴꜱʜᴏᴛ", url=f"https://t.me/{owner_user}")
        ],
        [
            InlineKeyboardButton("« Back to Premium Settings", callback_data="admin_premium_panel")
        ]
    ])
    
    try:
        await query.message.delete()
    except Exception:
        pass
    
    try:
        await client.send_photo(
            chat_id=query.message.chat.id,
            photo=qr_media,
            caption=caption,
            protect_content=False,
            reply_markup=preview_markup
        )
    except Exception:
        await client.send_message(
            chat_id=query.message.chat.id,
            text=caption,
            protect_content=False,
            reply_markup=preview_markup
        )
    await query.answer()

# =========================================================================
# Admin Input Message Handler (Text & Photo Listeners with group=-2)
# =========================================================================
@Client.on_message(filters.private & ~filters.bot & ~filters.regex(r"^[/\!.]"), group=-2)
async def admin_premium_input_handler(client: Client, message: Message):
    if not message.from_user or not is_admin(message.from_user.id):
        return
    
    user_id = message.from_user.id
    state = ADMIN_PREM_STATE.get(user_id)
    
    if not state:
        return
    
    step = state.get("step")
    prompt_id = state.get("prompt_msg_id")
    
    # 1. SET PREMIUM TEXT
    if step == "WAITING_PREM_TEXT":
        message.stop_propagation()
        if not message.text:
            return await message.reply_text("❌ Please send a valid text message for the premium plan.")
        
        new_text = message.text.html if hasattr(message.text, 'html') else message.text
        await db.update_premium_config("plan_text", new_text)
        ADMIN_PREM_STATE.pop(user_id, None)
        await db.clear_admin_prem_state(user_id)
        
        try:
            await message.delete()
        except Exception:
            pass
        if prompt_id:
            try:
                await client.delete_messages(message.chat.id, prompt_id)
            except Exception:
                pass
        
        cfg = await db.get_premium_config()
        text = await build_premium_panel_text(cfg)
        markup = await get_premium_panel_markup(cfg)
        
        await client.send_message(
            chat_id=message.chat.id,
            text=f"✅ <b>Premium Plan Text Updated Successfully!</b>\n\n" + text,
            reply_markup=markup
        )
        return
    
    # 2. SET QR CODE PHOTO
    if step == "WAITING_PREM_QR":
        message.stop_propagation()
        qr_val = None
        if message.photo:
            qr_val = message.photo.file_id
        elif message.text and (message.text.startswith("http://") or message.text.startswith("https://")):
            qr_val = message.text.strip()
        else:
            return await message.reply_text("❌ Please send a photo or a valid image URL (e.g. Telegraph/Catbox).")
        
        await db.update_premium_config("qr_code", qr_val)
        ADMIN_PREM_STATE.pop(user_id, None)
        await db.clear_admin_prem_state(user_id)
        
        try:
            await message.delete()
        except Exception:
            pass
        if prompt_id:
            try:
                await client.delete_messages(message.chat.id, prompt_id)
            except Exception:
                pass
        
        cfg = await db.get_premium_config()
        text = await build_premium_panel_text(cfg)
        markup = await get_premium_panel_markup(cfg)
        
        await client.send_message(
            chat_id=message.chat.id,
            text=f"✅ <b>Payment QR Code Photo Updated Successfully!</b>\n\n" + text,
            reply_markup=markup
        )
        return
    
    # 3. SET UPI ID
    if step == "WAITING_PREM_UPI":
        message.stop_propagation()
        if not message.text:
            return await message.reply_text("❌ Please send a valid UPI ID (e.g. <code>delhisehoon1782@ptyes</code>).")
        
        upi_clean = message.text.strip()
        await db.update_premium_config("upi_id", upi_clean)
        ADMIN_PREM_STATE.pop(user_id, None)
        await db.clear_admin_prem_state(user_id)
        
        try:
            await message.delete()
        except Exception:
            pass
        if prompt_id:
            try:
                await client.delete_messages(message.chat.id, prompt_id)
            except Exception:
                pass
        
        cfg = await db.get_premium_config()
        text = await build_premium_panel_text(cfg)
        markup = await get_premium_panel_markup(cfg)
        
        await client.send_message(
            chat_id=message.chat.id,
            text=f"✅ <b>UPI ID Updated to <code>{upi_clean}</code>!</b>\n\n" + text,
            reply_markup=markup
        )
        return
    
    # 4. SET SCREENSHOT OWNER USERNAME
    if step == "WAITING_PREM_OWNER":
        message.stop_propagation()
        if not message.text:
            return await message.reply_text("❌ Please send a valid Telegram username (e.g. <code>Movies_1783</code>).")
        
        raw_user = message.text.strip().replace("https://t.me/", "").replace("http://t.me/", "").replace("@", "").replace("/", "")
        await db.update_premium_config("screenshot_user", raw_user)
        ADMIN_PREM_STATE.pop(user_id, None)
        await db.clear_admin_prem_state(user_id)
        
        try:
            await message.delete()
        except Exception:
            pass
        if prompt_id:
            try:
                await client.delete_messages(message.chat.id, prompt_id)
            except Exception:
                pass
        
        cfg = await db.get_premium_config()
        text = await build_premium_panel_text(cfg)
        markup = await get_premium_panel_markup(cfg)
        
        await client.send_message(
            chat_id=message.chat.id,
            text=f"✅ <b>Payment Screenshot Contact set to @{raw_user}!</b>\n\n" + text,
            reply_markup=markup
        )
        return
