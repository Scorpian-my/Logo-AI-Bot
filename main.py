# -=-=-=-=-=-=-=-=-=-=-=
#
# -=-=-=-=-=-=-=-=-=-=-=
from rubpy import Client, handlers, Message, models
from requests import get, post
from random import randrange
from os import remove
from re import findall
import requests
import asyncio
import random
from persiantools.jdatetime import JalaliDate
balance = {}
warning = {}
generate_ai = {}
voice = {}
# Guid manager of the channel and group
owner = input("Enter Your Guid [Guid Owner]: ")
gap = input("Enter Guid Group: ")  # Guid Group
# Channel Guid for mandatory join
Channell = input("Enter Your Channel Guid: ")
print("Run Successfuly")




def voice_generate(text, file):
    voice = get(
        f"https://api.irateam.ir/create-voice/?text={text}&Character=DilaraNeural").json()
    voice = voice["results"]["url"]
    voice = requests.get(voice)
    with open(f"{file}", "wb") as f:
        f.write(voice.content)
        f.close()


def Pic_Prof(id):
    url = f"https://rubika.ir/{id}"

    response = get(url)
    page_content = response.text
    pattern = r'<img.*?src="(.*?)"'
    image_links = findall(pattern, page_content)
    link = []
    link.append(image_links)
    response = get(link[0][2])
    with open("Profile.png", "wb") as f:
        f.write(response.content)
        f.close()


def get_user_balance(user_id):
    return balance.get(user_id, 0)


def up_balance(user_id, amount):
    current_balance, current_AI, current_voice = (
        balance.get(user_id, 0),
        generate_ai.get(user_id, 0),
        voice.get(user_id, 0),
    )
    new_balance, new_ai, new_voice = (
        current_balance + amount,
        current_AI + amount,
        current_voice + amount,
    )
    balance[user_id], generate_ai[user_id], voice[user_id] = (
        new_balance,
        new_ai,
        new_voice,
    )


def decrease_user_balance(user_id, amount):
    current_balance = balance.get(user_id, 0)
    new_balance = current_balance - amount
    balance[user_id] = new_balance if new_balance >= 0 else 0


def join_message():
    join_message = """👋 کاربر عزیز

🌟 برای استفاده از دستورات ربات، ابتدا به کانال زیر عضو شوید:

📢 @FreeTube

🔥 پس از عضویت، امکان استفاده از دستورات ربات برای شما فعال می‌شود. 🤖
چنانچه شما از قبل عضو ربات بودید لطفا یک بار لفت بدید از کانال مجدد جوین شوید
با تشکر!
"""
    return join_message


def gpt(prompt):
    requests.session().cookies.clear()

    options_url = "https://api.tapsi.cab/api/v1/chat-gpt/chat/completion"
    headers = {
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type,x-agent",
        "Origin": "https://chatgpt.tapsi.cab",
    }
    response = requests.options(options_url, headers=headers)
    rand = random.randrange(11, 99)
    rand1 = random.randrange(111, 999)

    ip_address = f"{rand}.{rand1}.{rand}.{rand}"

    ip_parts = ip_address.split(".")
    random.shuffle(ip_parts)
    new_ip = ".".join(ip_parts)

    webkit_version = f"{random.randint(500, 600)}.{random.randint(0, 99)}"
    major_version = random.randint(100, 150)
    minor_version = random.randint(0, 9)
    build_version = random.randint(0, 9999)
    safari_version = f"{random.randint(500, 600)}.{random.randint(0, 99)}"
    user_agent = f"Mozilla/5.0 (Linux; Android 10; STK-L21) AppleWebKit/{webkit_version} (KHTML, like Gecko) Chrome/{major_version}.0.{minor_version}.{build_version} Mobile Safari/{safari_version}"

    post_url = "https://api.tapsi.cab/api/v1/chat-gpt/chat/completion"
    headers = {
        "Content-Type": "application/json",
        "X-Agent": user_agent,
        "X-Forwarded-For": new_ip,
        "Origin": "https://chatgpt.tapsi.cab",
    }
    data = {"messages": [{"role": "user", "content": prompt}]}
    return requests.post(post_url, headers=headers, json=data).json()["data"][
        "message"
    ]["content"]


def download_image(number, logo, save):
    log = "https://haji-api.ir/ephoto360/?type=text&id={}&text={}".format(
        number, logo)
    response = get(log)
    with open(f"{save}.png", "wb") as f:
        f.write(response.content)
        f.close()


def is_user_in_channel(guid, Channel1):
    channel_members = Channel1["in_chat_members"]
    for member in channel_members:
        if member["member_guid"] == guid:
            return True
    return False


def AI(text, type):
    generate = requests.get(
        "https://haji-api.ir/prompts/?text={}".format(text)).json()
    photos = generate["result"]
    random_index = randrange(0, len(photos) - 1)
    random_photo = photos[random_index]
    response = requests.get(random_photo)
    with open(f"{type}.png", "wb") as ai:
        ai.write(response.content)


def detect_profanity(text):
    with open("Fosh.txt", "r", encoding="utf-8") as file:
        lines = file.readlines()

        for line in lines:
            words = line.split()

            for word in words:
                if word in text:
                    return True

    return False


async def main():
    global Channell
    async with Client(session='rubpy') as client:
        await client.join_channel("c0BMKOd0fd6d1b62a51de3a9590c2631")
        await client.send_message(gap, "ربات هوش مصنوعی و لوگوساز با موفقیت اجرا شد\nبا دستور راهنما از دستورات با خبر باشید")
        await client.send_message(owner, "سلام ادمین عزیز \nاین دستورات است برای هدایت صحیح ممبر ها\nبرای شارژ آنها ابتدا کلمه شارژ را بنویسید و بعد آیدی آن و عدد شارژ\nبه عنوان مثال\nشارژ @pyrogram 100\n-=-=-=-=-=-=-=-=-=-=-=\nبرای دریافت موجودی آن ها بنویسید\n/profile @ID")

        @client.on(handlers.MessageUpdates(models.is_group(gap)))
        async def updates(message: Message):
            text = message.raw_text
            messID = message["message_id"]
            guid = message["message"]["author_object_guid"]

            Name = await client.get_user_info(guid)
            Name = Name["user"]["first_name"]
            Channel1 = await client.get_channel_all_members(Channell)
            Channel1 = Channel1.to_dict()
            if text == "/start" or text == "ربات" or text == "سلام":
                await message.reply(f"""
                ‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌‌
👋 سلام کاربر ،{Name}
به ربات هوش مصنوعی خوش آمدید. 🤖

برای نمایش دستورات، کلمه 'راهنما' را ارسال کنید. 📚

با احترام، تیم ربات نویسی:

🌟 @Legacy_Source""")
            elif text == "راهنما":
                try:
                    await client.send_message(guid, """
سلام چطوری..! 🌟

اومدم خوش آمد گویی کنم وارد ربات شدی 🐳

امیدوارم از ربات لذت ببری و کنارمون بمونی 😊✨

-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

خلللللاصه بگذریم سر تو بدرد نمیارم و دستور های ربات رو بهت میگم 😄


میدونستی قابلیت حرف زدن هم داره؟

بهش بگی بگو سلام زندگی بهت ویس میده :)
به عنوان مثال:
بگو سلامتی نادرشاه افشار بزرگ
-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
واقعاً هیجان زده‌ایم که بهتون اعلام کنیم که میتونین با استفاده از دستور زیر پیام ناشناس بفرستین:

خب مرحله اول اگر میخوای لوگو بسازی با اسم قشنگت باید بری داخل این کاناله عددی که میخوای ربات با اسمت بسازه رو برداری

🌐 @LogoExpress

مثلا من میخوام با مدل لوگوی شماره 50 واسم لوگو بسازه

باید بنویسم 

/logo 50 Mahyar

اینجوری میتونم لوگو امو بسازم 😊✨


-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
واقعاً هیجان زده‌ایم که بهتون اعلام کنیم که میتونین با استفاده از دستور زیر پیام ناشناس بفرستین:

/sms @USERNAME سلام

با استفاده از این دستور، میتونین به کسی که توسط نام کاربری مشخص میشه، یک پیام ناشناس با محتوای "سلام" ارسال کنین.

پیام ناشناس بفرستید و لحظات شیرینی رو براش رقم بزنید! 💌💫
-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
تازه میتونی با کمک هوش مصنوعی عکس دلخواه بسازی! 😃✨

برای مثال، اگر میخوای عکسی از خونه ای در جنگل بسازی باید به انگلیسی بنویسی:

/generate A house in the forest



با استفاده از این دستور میتونم بهت عکسی مرتبط با خونه ای در جنگل بدم. امیدوارم ازش لذت ببری! 🏡🌳📷


ما خوشحالیم که همیشه در خدمتتون هستیم و میتونیم بهتون کمک کنیم. اگر سوال یا درخواست دیگه ای دارید، حتما بپرسید! 😊🌟
👉 @The_Pynux
""",
                                              )
                    await message.reply("دستورات ربات به پیوی شما ارسال شد")
                except Exception as e:
                    print(e)

            elif text.startswith("/generate "):
                Gen = text.replace("/generate ", "").replace('"', "")
                Gen = Gen.lower()
                if guid == owner:
                    try:
                        AI(Gen, "owner")
                        await client.send_photo(gap, "owner.jpg", "تقدیم با عشق", "owner.jpg", "360", "360", reply_to_message_id=messID)
                        remove("owner.png")
                    except Exception as e:
                        print(e)
                else:
                    if detect_profanity(Gen):
                        if guid not in warning:
                            warning[guid] = 0
                        if warning[guid] < 2:
                            warning[guid] += 1
                            await message.reply(
                                f"شما به دلیل رعایت نکردن قوانین ربات، از کلمات ممنوعه استفاده کردید، اخطار گرفتید \n تعداد اخطار های شما: {warning[guid]}"
                            )
                        else:
                            await message.reply(
                                f"شما به دلیل رعایت نکردن قوانین ربات، از کلمات ممنوعه استفاده کردید، اخطار گرفتید \n تعداد اخطار های شما: 3"
                            )
                            await message.reply(
                                "شما به حداکثر اخطار رسیدید، تا دیدار بعد خدانگهدار"
                            )
                            await client.ban_group_member(gap, guid)
                    else:
                        if is_user_in_channel(guid, Channel1):
                            try:
                                if guid not in generate_ai:
                                    generate_ai[guid] = 15
                                if generate_ai[guid] > 1:
                                    generate_ai[guid] -= 1
                                    AI(Gen, "user")
                                    await client.send_photo(
                                        gap,
                                        "user.png",
                                        f"درخواست شما با موفقیت تکمیل شد.🎉\n\n- Daily credit : {generate_ai[guid]}/15🎉\n∞ Scorpian AI Bot ∞\n# @Legacy_Source", "user.png", "360", "360", reply_to_message_id=messID
                                    )
                                else:
                                    await message.reply(
                                        "موجودی شما تمام شده است برای شارژ و یا تمدید با این آیدی در ارتباط باشید :\n@Pyrogram"
                                    )
                            except Exception as e:
                                print(e)
                        else:
                            await message.reply(join_message())
            if text.startswith("/logo "):
                text = text.replace("/logo ", "")
                text_parts = text.split()

                if len(text_parts) >= 2:
                    number_text = text_parts[0]
                    if number_text.isdigit():
                        number = int(number_text)
                        if 1 <= number <= 136:
                            if guid == owner:
                                try:
                                    download_image(
                                        text_parts[0], text_parts[1], "owner")
                                    await client.send_photo(gap, "owner.png", "تقدیم با عشق", "owner.png", "320", "202", reply_to_message_id=messID)

                                    remove("owner.png")
                                    return ...
                                except Exception as e:
                                    print(e)
                                    return ...
                            else:
                                try:
                                    if is_user_in_channel(guid, Channel1):
                                        if guid not in balance:
                                            balance[guid] = 15
                                        if balance[guid] > 1:
                                            balance[guid] -= 1
                                            download_image(
                                                text_parts[0], text_parts[1], "user")
                                            await client.send_photo(gap, "user.png", f"درخواست شما با موفقیت تکمیل شد.\n\n- Daily credit : {balance[guid]}/15\n∞ Scorpian AI Bot ∞\n# @LogoExpress", "user.png", "360", "360", "Music.jpg", messID)
                                            remove("user.png")
                                        else:
                                            await message.reply(
                                                "موجودی شما تمام شده است برای شارژ و یا تمدید با این آیدی در ارتباط باشید :\n@Pyrogram"
                                            )
                                    else:
                                        await message.reply(join_message())
                                except Exception as e:
                                    print(e)
                        else:
                            await message.reply(
                                "کاربر عزیز، عدد وارد شده باید بین 1 تا 136 باشد"
                            )
                            return ...
                    else:
                        await message.reply(
                            "کاربر عزیز، لطفاً یک عدد معتبر را وارد کنید"
                        )
                        return ...
                else:
                    await message.reply(
                        "نوع درخواست شما اشتباه است\n برای درخواست عکس باید عدد مورد نظر خود را ازینجا بردارید\n@LogoExpress\nمثالی از نمونه درخواست:\n/logo 120 Mahyar"
                    )
                    return ...
            elif text.startswith("!"):
                text.replace("!", "")
                try:
                    if len(text) > 4999:
                        await message.reply(
                            "تعداد متن های جواب بیشتر از حد است و نمیتوان فرستاد"
                        )
                    else:
                        await message.reply(f"پاسخ شما:\n{gpt(text)}")
                except Exception as e:
                    print(e)

            elif text.startswith("شارژ @"):
                if guid == owner:
                    text = text.replace("شارژ @", "")
                    text = text.split()
                    username = text[0]
                    amount = int(text[1])
                    try:
                        user = await client.get_object_by_username(username)
                        if user:
                            guis = user["user"]["user_guid"]
                            up_balance(guis, amount)
                            await message.reply(
                                f"مقدار شارژ کاربر @{username} به میزان {amount} افزایش یافت."
                            )
                        else:
                            await message.reply(f"کاربر {username} یافت نشد.")
                    except Exception as e:
                        print(e)
                else:
                    ...
            elif text.startswith("بگو "):
                text = text.replace("بگو ", "")
                if guid == owner:
                    try:
                        voice_generate(text, "owner.mp3")
                        await client.send_voice(gap, "owner.mp3", "**بفرمایید قربان**", "owner.mp3", time="12345678", reply_to_message_id=messID)
                        remove("owner.mp3")
                        return ...
                    except Exception as e:
                        print(e)

                else:
                    if is_user_in_channel(guid, Channel1):
                        try:
                            if len(text) > 700:
                                await message.reply(
                                    "تعداد متن های جواب بیشتر از حد است و نمیتوان فرستاد"
                                )
                            else:
                                if guid not in voice:
                                    voice[guid] = 15
                                if voice[guid] > 1:
                                    voice[guid] -= 1
                                    voice_generate(text, "user.mp3")
                                    await client.send_voice(gap, "user.mp3", f"**ویس شما آماده شد**\nاعتبار فعلی شما: {voice[guid]}/15", "user.mp3", time="12345678", reply_to_message_id=messID)

                                    remove("user.mp3")
                                else:
                                    await message.reply(
                                        "موجودی شما تمام شده است برای شارژ و یا تمدید با این آیدی در ارتباط باشید :\n@Pyrogram"
                                    )
                        except Exception as e:
                            print(e)

                    else:
                        await message.reply(join_message())
                try:
                    remove("voice.mp3")
                except Exception as e:
                    print(e)
            elif text.startswith('/sms'):
                try:
                    info = await client.get_object_by_username(text.split()[1][1:])
                    info = info["user"]["user_guid"]
                    await client.send_message(info, '📨 شما یک پیام ناشناس دارید:‌\n\n'+" ".join(text.split()[2:]))
                    await message.reply(f'پیام شما با موفقیت ارسال شد...')
                except Exception as e:
                    await message.reply("احتمالا آیدی وجود ندارد")
            elif text.startswith("/profile @"):
                text = text.replace("/profile @", "")
                text = text.lower()
                profile = await client.get_object_by_username(text)
                stamp = profile["user"]["last_online"]
                name = profile["user"]["first_name"]
                last = profile["user"]["last_name"]
                user = profile["user"]["username"]
                bio = profile["user"]["bio"]
                time = JalaliDate.fromtimestamp(int(stamp))
                Pic_Prof(text)
                if text == "pyrogram":
                    await client.send_photo(gap, "Profile.png", f"""
🌟 اطلاعات کاربر مورد نظر:
––––––––––––––––––––––––
👤 نام کاربر: {name}{last}
-=-=-=-=-=-=-=-=-=-=-=
💰 اعتبار: VIP
-=-=-=-=-=-=-=-=-=-=-=
🆔 آیدی: @{user}
-=-=-=-=-=-=-=-=-=-=-=
💬 بیوگرافی: {bio}
-=-=-=-=-=-=-=-=-=-=-=
⏱ آخرین بازدید:
{time}
-=-=-=-=-=-=-=-=-=-=-=
🔐 اشتراک کاربر: VIP
––––––––––––––––––––––––
#Information_Bot""", "Profile.png", "320", "202", reply_to_message_id=messID)
                else:
                    try:
                        await client.send_photo(gap, "Profile.png", f"""
🌟 اطلاعات کاربر مورد نظر:
––––––––––––––––––––––––
👤 نام کاربر: {name}{last}
-=-=-=-=-=-=-=-=-=-=-=
💰 اعتبار: VIP
-=-=-=-=-=-=-=-=-=-=-=
🆔 آیدی: @{user}
-=-=-=-=-=-=-=-=-=-=-=
💬 بیوگرافی: {bio}
-=-=-=-=-=-=-=-=-=-=-=
⏱ آخرین بازدید:
{time}
-=-=-=-=-=-=-=-=-=-=-=
🔐 اشتراک کاربر: معمولی
––––––––––––––––––––––––
#Information_Bot""", "Profile.png", "320", "202", reply_to_message_id=messID)
                    except Exception as e:
                        print(e)
        await client.run_until_disconnected()
asyncio.run(main())
