import io
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
import qrcode
from PIL import Image
import cv2
import numpy as np
from PIL import Image

def decode_qr_from_image(image_path):
    img = cv2.imread(image_path)

    detector = cv2.QRCodeDetector()
    data, bbox, _ = detector.detectAndDecode(img)

    if data:
        return data
    return None



#Token : 7627346064:AAGjH-hdUlksI4bFbn55YVQjxy2ciu7Pdgw
BOT_TOKEN = os.getenv("BOT_TOKEN")
from telegram.request import HTTPXRequest

request = HTTPXRequest(
    connect_timeout=60,
    read_timeout=60,
    write_timeout=60,
    pool_timeout=60
)

app = (
    ApplicationBuilder()
    .token(BOT_TOKEN)
    .request(request)
    .build()
)




# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 *Welcome to QR Bot*\n\n"
        "*Private Chat:*\n"
        "• Send any text → QR generated\n"
        "• Send QR image → Decoded\n\n"
        "*Groups:*\n"
        "• /qr <text> → Generate QR\n"
        "• Send QR image with caption `/decode` → Decode\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ---------- QR GENERATOR ----------
def generate_qr(text: str) -> io.BytesIO:
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(text)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    bio = io.BytesIO()
    bio.name = "qr.png"
    img.save(bio, "PNG")
    bio.seek(0)
    return bio


# ---------- /qr ----------
async def qr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        await update.message.reply_text(
            "❌ /qr works only in groups.\n"
            "Just send text directly in private chat."
        )
        return

    if not context.args:
        await update.message.reply_text("❌ Usage: /qr <text>")
        return

    text = " ".join(context.args)
    qr_img = generate_qr(text)

    await update.message.reply_photo(
        photo=qr_img,
        caption=f'📦 QR Generated for text "{text}"'
    )


# ---------- BLOCK /decode IN PRIVATE ----------
async def decode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "private":
        await update.message.reply_text(
            "❌ /decode works only in groups.\n"
            "Just send the QR image directly in private chat."
        )


# ---------- PRIVATE TEXT → QR ----------
async def text_to_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return

    text = update.message.text
    qr_img = generate_qr(text)

    await update.message.reply_photo(
        photo=qr_img,
        caption=f'📦 QR Generated for text "{text}"'
    )


# ---------- DECODE QR IMAGE ----------
async def decode_qr_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    # GROUP: must have caption /decode
    if msg.chat.type != "private":
        if msg.caption != "/decode":
            return

    photo = msg.photo[-1]
    file = await photo.get_file()

    image_path = f"/tmp/{msg.message_id}.png"
    await file.download_to_drive(image_path)

    decoded = decode_qr_from_image(image_path)
    os.remove(image_path)

    if not decoded:
        await msg.reply_text("❌ No QR code found")
        return

    await msg.reply_text(
        f"🔓 *Decoded QR:*\n\n`{decoded}`",
        parse_mode="Markdown"
    )


async def decode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    # Private chat → block
    if msg.chat.type == "private":
        await msg.reply_text(
            "❌ Just send the QR image directly in private chat."
        )
        return

    # Must be a reply
    if not msg.reply_to_message or not msg.reply_to_message.photo:
        await msg.reply_text(
            "❌ Reply to a QR image with /decode"
        )
        return

    replied = msg.reply_to_message
    photo = replied.photo[-1]
    file = await photo.get_file()

    image_path = f"/tmp/{replied.message_id}.png"
    await file.download_to_drive(image_path)

    decoded = decode_qr_from_image(image_path)
    os.remove(image_path)

    if not decoded:
        await msg.reply_text("❌ No QR code found")
        return

    await msg.reply_text(
        f"🔓 *Decoded QR:*\n\n`{decoded}`",
        parse_mode="Markdown"
    )

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("qr", qr_command))
    app.add_handler(CommandHandler("decode", decode_command))

    # Text → QR (PRIVATE ONLY, COMMANDS IGNORED)
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_to_qr
        )
    )

    # Photo → Decode
    app.add_handler(MessageHandler(filters.PHOTO, decode_qr_photo))

    print("✅ QR Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
