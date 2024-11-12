import asyncio
from telegram import Bot

bot_token = "7212490708:AAG_mkQxkkcXfxPYqMRhV_Tp5J2a8RiBSeA"
chat_id = "-4281047122"

async def send_test_message():
    try:
        telegram_notify = Bot(token=bot_token)
        await telegram_notify.send_message(chat_id=chat_id, text="Test message from bot")
        print("Test message sent successfully")
    except Exception as ex:
        print(f"Error sending test message: {ex}")

asyncio.run(send_test_message())
    
    