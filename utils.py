import json
from aiogram import Bot

def load_sponsors():
    with open("sponsors.json", "r") as f:
        return json.load(f)

def save_sponsors(sponsors):
    with open("sponsors.json", "w") as f:
        json.dump(sponsors, f)

def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except:
        return []

def save_user(user_id):
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        with open("users.json", "w") as f:
            json.dump(users, f)

async def check_subscriptions(bot: Bot, user_id: int):
    sponsors = load_sponsors()
    for channel in sponsors:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception as e:
            print(f"[!] Obuna tekshiruvda xatolik: {e}")
            return False
    return True

