import os
import telebot
from flask import Flask, request
from openai import OpenAI

# 1. Load Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
# RENDER_EXTERNAL_URL is automatically provided by Render.com
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL") 

if not BOT_TOKEN or not HF_TOKEN:
    raise ValueError("BOT_TOKEN and HF_TOKEN must be set in environment variables.")

# 2. Initialize Telegram Bot and OpenAI Client
bot = telebot.TeleBot(BOT_TOKEN)

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN,
)

app = Flask(__name__)

# 3. Handler for Text Messages
@bot.message_handler(content_types=['text'])
def handle_text(message):
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        response = client.chat.completions.create(
            model="moonshotai/Kimi-K2.5:novita",
            messages=[
                {"role": "user", "content": message.text}
            ]
        )
        reply = response.choices[0].message.content
        bot.reply_to(message, reply)
    except Exception as e:
        bot.reply_to(message, f"An API error occurred: {str(e)}")

# 4. Handler for Image Messages (Multimodal)
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        # Get the highest resolution photo sent by the user
        file_info = bot.get_file(message.photo[-1].file_id)
        image_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        
        # Use user's caption as the prompt, or default to a generic prompt
        prompt = message.caption if message.caption else "Describe this image in one sentence."

        # Send to Hugging Face / OpenAI compatible router
        response = client.chat.completions.create(
            model="moonshotai/Kimi-K2.5:novita",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
        )
        reply = response.choices[0].message.content
        bot.reply_to(message, reply)
    except Exception as e:
        bot.reply_to(message, f"An API error occurred: {str(e)}")

# 5. Flask Routes for Telegram Webhook
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    # Telegram sends updates to this route
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def index():
    return "Telegram Bot is running smoothly!", 200

# 6. Start Server and Setup Webhook
if __name__ == "__main__":
    # Remove previous webhooks and set the new one to the Render URL
    bot.remove_webhook()
    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL}/{BOT_TOKEN}"
        bot.set_webhook(url=webhook_url)
        print(f"Webhook set to: {webhook_url}")
    
    # Render assigns a dynamic port via the PORT environment variable
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
