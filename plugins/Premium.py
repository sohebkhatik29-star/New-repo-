
import pytz
import datetime
from Script import script 
from info import *
from utils import get_seconds, temp
from database.users_chats_db import db 
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.errors.exceptions.bad_request_400 import MessageTooLong
from pyrogram.types import *


def _is_admin(user_id: int) -> bool:
    """Check admin against live ADMINS list (includes custom admins synced at runtime)."""
    try:
        uid = int(user_id)
        return uid in ADMINS or str(uid) in [str(a) for a in ADMINS]
    except Exception:
        return False


async def _require_admin(message) -> bool:
    if not message.from_user or not _is_admin(message.from_user.id):
        try:
            await message.reply_text(
                "❌ <b>Access Denied</b>\n\n"
                "You are not an admin.\n"
                f"Your ID: <code>{message.from_user.id if message.from_user else 'N/A'}</code>\n\n"
                "Add this ID to <code>ADMINS</code> env on Render, or add via Manage Admins panel.",
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            pass
        return False
    return True


@Client.on_message(filters.command("remove_premium") & filters.private)
async def remove_premium(client, message):
    if not await _require_admin(message):
        return
    if len(message.command) == 2:
        user_id = int(message.command[1])
        user = await client.get_users(user_id)
        if await db.remove_premium_access(user_id):
            await message.reply_text("ᴜꜱᴇʀ ʀᴇᴍᴏᴠᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ !")
            await client.send_message(
                chat_id=user_id,
                text=script.PREMIUM_END_TEXT.format(user.mention)
            )
        else:
            await message.reply_text("ᴜɴᴀʙʟᴇ ᴛᴏ ʀᴇᴍᴏᴠᴇ ᴜꜱᴇᴅ !\nᴀʀᴇ ʏᴏᴜ ꜱᴜʀᴇ, ɪᴛ ᴡᴀꜱ ᴀ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀ ɪᴅ ?")
    else:
        await message.reply_text("ᴜꜱᴀɢᴇ : /remove_premium user_id") 


@Client.on_message(filters.command("myplan"))
async def myplan(client, message):
    try:
        user = message.from_user.mention
        user_id = message.from_user.id
        data = await db.get_user(user_id)

        if data and data.get("expiry_time"):
            expiry = data.get("expiry_time")
            expiry_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata"))
            expiry_str_in_ist = expiry_ist.strftime("%d-%m-%Y\n⏱️ ᴇxᴘɪʀʏ ᴛɪᴍᴇ : %I:%M:%S %p")

            current_time = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
            time_left = expiry_ist - current_time
            days = time_left.days
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_left_str = f"{days} ᴅᴀʏꜱ, {hours} ʜᴏᴜʀꜱ, {minutes} ᴍɪɴᴜᴛᴇꜱ"

            caption = (
                f"⚜️ <b>ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀ ᴅᴀᴛᴀ :</b>\n\n"
                f"👤 <b>ᴜꜱᴇʀ :</b> {user}\n"
                f"⚡ <b>ᴜꜱᴇʀ ɪᴅ :</b> <code>{user_id}</code>\n"
                f"⏰ <b>ᴛɪᴍᴇ ʟᴇꜰᴛ :</b> {time_left_str}\n"
                f"⌛️ <b>ᴇxᴘɪʀʏ ᴅᴀᴛᴇ :</b> {expiry_str_in_ist}"
            )

            await message.reply_photo(
                photo=SUBSCRIPTION, 
                caption=caption,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔥 ᴇxᴛᴇɴᴅ ᴘʟᴀɴ", callback_data="premium_info")]]
                )
            )
        else:
            await message.reply_photo(
                photo="https://i.ibb.co/gMrpRQWP/photo-2025-07-09-05-21-32-7524948058832896004.jpg", 
                caption=(
                    f"<b>ʜᴇʏ {user},\n\n"
                    f"ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴀɴ ᴀᴄᴛɪᴠᴇ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴ.\n"
                    f"ʙᴜʏ ᴏᴜʀ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ ᴛᴏ ᴇɴᴊᴏʏ ᴘʀᴇᴍɪᴜᴍ ʙᴇɴᴇꜰɪᴛꜱ.</b>"
                ),
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("💎 ᴄʜᴇᴄᴋᴏᴜᴛ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴꜱ", callback_data='premium_info')]]
                )
            )
    except Exception as e:
        print(e)

@Client.on_message(filters.command("get_premium") & filters.private)
async def get_premium(client, message):
    if not await _require_admin(message):
        return
    if len(message.command) == 2:
        user_id = int(message.command[1])
        user = await client.get_users(user_id)
        data = await db.get_user(user_id)  
        if data and data.get("expiry_time"):
            expiry = data.get("expiry_time") 
            expiry_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata"))
            expiry_str_in_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata")).strftime("%d-%m-%Y\n⏱️ ᴇxᴘɪʀʏ ᴛɪᴍᴇ : %I:%M:%S %p")            
            current_time = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
            time_left = expiry_ist - current_time
            days = time_left.days
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_left_str = f"{days} days, {hours} hours, {minutes} minutes"
            await message.reply_text(f"⚜️ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀ ᴅᴀᴛᴀ :\n\n👤 ᴜꜱᴇʀ : {user.mention}\n⚡ ᴜꜱᴇʀ ɪᴅ : <code>{user_id}</code>\n⏰ ᴛɪᴍᴇ ʟᴇꜰᴛ : {time_left_str}\n⌛️ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}")
        else:
            await message.reply_text("ɴᴏ ᴀɴʏ ᴘʀᴇᴍɪᴜᴍ ᴅᴀᴛᴀ ᴏꜰ ᴛʜᴇ ᴡᴀꜱ ꜰᴏᴜɴᴅ ɪɴ ᴅᴀᴛᴀʙᴀꜱᴇ !")
    else:
        await message.reply_text("ᴜꜱᴀɢᴇ : /get_premium user_id")

@Client.on_message(filters.command("add_premium") & filters.private)
async def give_premium_cmd_handler(client, message):
    """
    Usage:
      /add_premium <user_id> <number> <unit>
      /add_premium <user_id> <number><unit>
      Reply to a user: /add_premium <number> <unit>

    Examples:
      /add_premium 123456789 1 month
      /add_premium 123456789 30 day
      /add_premium 123456789 1month
    """
    if not await _require_admin(message):
        return
    try:
        args = message.command[1:]  # everything after /add_premium
        user_id = None
        time_str = None

        # Case 1: reply to a user message
        if message.reply_to_message and message.reply_to_message.from_user:
            user_id = message.reply_to_message.from_user.id
            time_str = " ".join(args).strip() if args else ""
        # Case 2: /add_premium USER_ID TIME...
        elif args:
            try:
                user_id = int(args[0])
            except ValueError:
                await message.reply_text(
                    "❌ <b>Invalid user_id</b>\n\n"
                    "📌 Usage: <code>/add_premium user_id 1 month</code>\n"
                    "📅 Example: <code>/add_premium 123456789 1 month</code>",
                    parse_mode=enums.ParseMode.HTML
                )
                return
            time_str = " ".join(args[1:]).strip() if len(args) > 1 else ""
        else:
            await message.reply_text(
                "📌 <b>Usage:</b> <code>/add_premium user_id time</code>\n"
                "📅 <b>Examples:</b>\n"
                "• <code>/add_premium 123456789 1 month</code>\n"
                "• <code>/add_premium 123456789 30 day</code>\n"
                "• <code>/add_premium 123456789 1year</code>\n"
                "• Reply to user: <code>/add_premium 1 month</code>\n\n"
                "🧭 Units: <code>min</code>, <code>hour</code>, <code>day</code>, <code>month</code>, <code>year</code>",
                parse_mode=enums.ParseMode.HTML
            )
            return

        if not time_str:
            await message.reply_text(
                "❌ Time missing!\n\n"
                "Example: <code>/add_premium {} 1 month</code>".format(user_id),
                parse_mode=enums.ParseMode.HTML
            )
            return

        seconds = await get_seconds(time_str)
        if seconds <= 0:
            await message.reply_text(
                "❌ <b>Invalid time format</b>\n\n"
                "Use: <code>1 day</code>, <code>1 hour</code>, <code>1 min</code>, "
                "<code>1 month</code>, <code>1 year</code>\n"
                f"You sent: <code>{time_str}</code>",
                parse_mode=enums.ParseMode.HTML
            )
            return

        try:
            user = await client.get_users(user_id)
        except Exception:
            await message.reply_text(
                f"❌ User not found: <code>{user_id}</code>\n"
                "User must have started the bot at least once.",
                parse_mode=enums.ParseMode.HTML
            )
            return

        time_zone = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
        current_time = time_zone.strftime("%d-%m-%Y\n⏱️ Joining time : %I:%M:%S %p")
        expiry_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
        user_data = {"id": user_id, "expiry_time": expiry_time}
        await db.update_user(user_data)

        data = await db.get_user(user_id)
        expiry = data.get("expiry_time")
        expiry_str_in_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata")).strftime(
            "%d-%m-%Y\n⏱️ Expiry time : %I:%M:%S %p"
        )

        success_text = (
            f"✅ <b>Premium Added Successfully</b>\n\n"
            f"👤 User : {user.mention}\n"
            f"⚡ User ID : <code>{user_id}</code>\n"
            f"⏰ Access : <code>{time_str}</code>\n\n"
            f"⏳ Joining : {current_time}\n"
            f"⌛️ Expiry : {expiry_str_in_ist}"
        )
        await message.reply_text(success_text, parse_mode=enums.ParseMode.HTML, disable_web_page_preview=True)

        # Notify user (ignore if blocked)
        try:
            await client.send_message(
                chat_id=user_id,
                text=(
                    f"👋 Hey {user.mention},\n"
                    f"Thank you for purchasing Premium. Enjoy! ✨🎉\n\n"
                    f"⏰ Access : <code>{time_str}</code>\n"
                    f"⏳ Joining : {current_time}\n"
                    f"⌛️ Expiry : {expiry_str_in_ist}"
                ),
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True
            )
        except Exception:
            pass

        # Premium logs (ignore if channel invalid)
        try:
            if PREMIUM_LOGS and PREMIUM_LOGS != -100:
                await client.send_message(
                    PREMIUM_LOGS,
                    text=f"#Added_Premium\n\n{success_text}",
                    parse_mode=enums.ParseMode.HTML,
                    disable_web_page_preview=True
                )
        except Exception:
            pass

    except Exception as e:
        await message.reply_text(
            f"⚠️ Error while adding premium:\n<code>{str(e)[:200]}</code>",
            parse_mode=enums.ParseMode.HTML
        )

@Client.on_message(filters.command("premium_users") & filters.private)
async def premium_user(client, message):
    if not await _require_admin(message):
        return
    aa = await message.reply_text("<i>ꜰᴇᴛᴄʜɪɴɢ...</i>")
    new = f" ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀꜱ ʟɪꜱᴛ :\n\n"
    user_count = 1
    users = await db.get_all_users()
    async for user in users:
        data = await db.get_user(user['id'])
        if data and data.get("expiry_time"):
            expiry = data.get("expiry_time") 
            expiry_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata"))
            expiry_str_in_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata")).strftime("%d-%m-%Y\n⏱️ ᴇxᴘɪʀʏ ᴛɪᴍᴇ : %I:%M:%S %p")            
            current_time = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
            time_left = expiry_ist - current_time
            days = time_left.days
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_left_str = f"{days} days, {hours} hours, {minutes} minutes"	 
            new += f"{user_count}. {(await client.get_users(user['id'])).mention}\n👤 ᴜꜱᴇʀ ɪᴅ : {user['id']}\n⏳ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}\n⏰ ᴛɪᴍᴇ ʟᴇꜰᴛ : {time_left_str}\n"
            user_count += 1
        else:
            pass
    try:    
        await aa.edit_text(new)
    except MessageTooLong:
        with open('usersplan.txt', 'w+') as outfile:
            outfile.write(new)
        await message.reply_document('usersplan.txt', caption="Paid Users:")


@Client.on_message(filters.command("plan"))
async def plan(client, message):
    user_id = message.from_user.id
    users = message.from_user.mention
    log_message = (
        f"<b><u>🚫 ᴛʜɪs ᴜsᴇʀs ᴛʀʏ ᴛᴏ ᴄʜᴇᴄᴋ /plan</u> {temp.B_LINK}\n\n"
        f"- ɪᴅ - `{user_id}`\n- ɴᴀᴍᴇ - {users}</b>")
    btn = [[
            InlineKeyboardButton('• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •', callback_data='buy_info'),
        ],[
            InlineKeyboardButton('• ʀᴇꜰᴇʀ ꜰʀɪᴇɴᴅꜱ', callback_data='reffff'),
            InlineKeyboardButton('ꜰʀᴇᴇ ᴛʀɪᴀʟ •', callback_data='free')
        ],[
            InlineKeyboardButton('🚫 ᴄʟᴏꜱᴇ 🚫', callback_data='close_data')
        ]]
    msg = await message.reply_photo(
        photo="https://graph.org/file/86da2027469565b5873d6.jpg",
        caption=script.BPREMIUM_TXT,
        reply_markup=InlineKeyboardMarkup(btn)
    )
    await client.send_message(PREMIUM_LOGS, log_message)
    await asyncio.sleep(300)
    await msg.delete()
    await message.delete()


# Telegram Star Payment Method 👇
# Credit - @BeingXAnonymous

@Client.on_callback_query(filters.regex(r"buy_\d+"))
async def premium_button(client, callback_query: CallbackQuery):
    try:
        amount = int(callback_query.data.split("_")[1])
        if amount in STAR_PREMIUM_PLANS:
            try:
                buttons = [[	
                    InlineKeyboardButton("ᴄᴀɴᴄᴇʟ 🚫", callback_data="close_data"),		    				
                ]]
                reply_markup = InlineKeyboardMarkup(buttons)
                await client.send_invoice(
                    chat_id=callback_query.message.chat.id,
                    title="Premium Subscription",
                    description=f"Pay {amount} Star And Get Premium For {STAR_PREMIUM_PLANS[amount]}",
                    payload=f"dreamxpremium_{amount}",
                    currency="XTR",
                    prices=[
                        LabeledPrice(
                            label="Premium Subscription", 
                            amount=amount
                        ) 
                    ],
                    reply_markup=reply_markup
                )
                await callback_query.answer()
            except Exception as e:
                print(f"Error sending invoice: {e}")
                await callback_query.answer("🚫 Error Processing Your Payment. Try again.", show_alert=True)
        else:
            await callback_query.answer("⚠️ Invalid Premium Package.", show_alert=True)
    except Exception as e:
        print(f"Error In buy_ - {e}")
 
@Client.on_pre_checkout_query()
async def pre_checkout_handler(client, query: PreCheckoutQuery):
    try:
        if query.payload.startswith("dreamxpremium_"):
            await query.answer(success=True)
        else:
            await query.answer(success=False, error_message="⚠️ Invalid Purchase Type.", show_alert=True)
    except Exception as e:
        print(f"Pre-checkout error: {e}")
        await query.answer(success=False, error_message="🚫 Unexpected Error Occurred." , show_alert=True)

@Client.on_message(filters.successful_payment)
async def successful_premium_payment(client, message):
    try:
        amount = int(message.successful_payment.total_amount)
        user_id = message.from_user.id
        time_zone = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
        current_time = time_zone.strftime("%d-%m-%Y | %I:%M:%S %p") 
        if amount in STAR_PREMIUM_PLANS:
            time = STAR_PREMIUM_PLANS[amount]
            seconds = await get_seconds(time)
            if seconds > 0:
                expiry_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
                user_data = {"id": user_id, "expiry_time": expiry_time}
                await db.update_user(user_data)
                data = await db.get_user(user_id)
                expiry = data.get("expiry_time")
                expiry_str_in_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata")).strftime("%d-%m-%Y | %I:%M:%S %p")    
                await message.reply(text=f"Thankyou For Purchasing Premium Service Using Star ✅\n\nSubscribtion Time - {time}\nExpire In - {expiry_str_in_ist}", disable_web_page_preview=True)                
                await client.send_message(PREMIUM_LOGS, text=f"#Purchase_Premium_With_Start\n\n👤 ᴜꜱᴇʀ - {message.user.mention}\n\n⚡ ᴜꜱᴇʀ ɪᴅ - <code>{user_id}</code>\n\n🚫 ꜱᴛᴀʀ ᴘᴀʏ - {amount}⭐\n\n⏰ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇꜱꜱ - {time}\n\n⌛️ ᴊᴏɪɴɪɴɢ ᴅᴀᴛᴇ - {current_time}\n\n⌛️ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ - {expiry_str_in_ist}", disable_web_page_preview=True)
            else:
                await message.reply("⚠️ Invalid Premium Time.")
        else:
            await message.reply("⚠️ Invalid Premium Package.")
    except Exception as e:
        print(f"Error Processing Premium Payment: {e}")
        await message.reply("✅ Thank You For Your Payment! (Error Logging Details)")


