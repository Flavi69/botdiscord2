import discord
from discord.ext import commands
import requests
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
import os

# Încarcă variabilele din fișierul .env
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
FREEIMAGE_API_KEY = os.getenv("FREEIMAGE_API_KEY")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
IGNORE_USER_ID = int(os.getenv("IGNORE_USER_ID"))

# Configurări Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="Muie Saxofon"))
    print(f"{bot.user.name} a fost conectat și este online!")

def upload_to_freeimage(image_url):
    try:
        image_data = requests.get(image_url).content
        response = requests.post(
            "https://freeimage.host/api/1/upload",
            data={"key": FREEIMAGE_API_KEY, "format": "json"},
            files={"source": ("image.png", image_data)}
        )
        return response.json()["image"]["url"] if response.status_code == 200 else None
    except Exception as e:
        return str(e)

# Funcția care creează colajul
async def create_collage(images):
    image_files = []
    for url in images:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        image_files.append(img)

    width = sum(img.width for img in image_files)
    height = max(img.height for img in image_files)
    collage = Image.new('RGB', (width, height))
    x_offset = 0
    for img in image_files:
        collage.paste(img, (x_offset, 0))
        x_offset += img.width

    output_buffer = BytesIO()
    collage.save(output_buffer, format="PNG")
    output_buffer.seek(0)
    return output_buffer

@bot.event
async def on_message(message):
    if message.author.id == IGNORE_USER_ID or message.channel.id != CHANNEL_ID:
        return

    if "!colaj" in message.content:
        await bot.process_commands(message)
        return

    if message.attachments:
        links = [upload_to_freeimage(attachment.url) for attachment in message.attachments]
        success_links = [link for link in links if link]

        for idx, link in enumerate(links):
            if link is None:
                await message.channel.send(f"{message.author.mention} A apărut o eroare la încărcarea imaginii {message.attachments[idx].url}.")
                await message.add_reaction("❌")

        if success_links:
            formatted_links = ",".join(success_links)
            msg = f"{message.author.mention} " + ("Imaginea încărcată:\n" if len(success_links) == 1 else "Imaginile încărcate:\n")
            await message.channel.send(f"{msg}```{formatted_links}```")
            await message.add_reaction("✅")
    else:
        await message.channel.send(f"{message.author.mention} Mesajul nu conține atașamente.")
        await message.add_reaction("❌")

    await bot.process_commands(message)

@bot.command(name="colaj")
async def colaj(ctx):
    if ctx.message.attachments:
        images = [attachment.url for attachment in ctx.message.attachments]
        
        if images:
            collage_buffer = await create_collage(images)
            await ctx.send("Colajul imaginilor:", file=discord.File(collage_buffer, "colaj.png"))
        else:
            await ctx.send("Nu a fost posibil să creez colajul.")
    else:
        await ctx.send("Nu există atașamente în acest mesaj.")

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx):
    if ctx.channel.id == CHANNEL_ID:
        deleted = await ctx.channel.purge(limit=None)
        await ctx.send(f"{len(deleted)} mesaje au fost șterse.", delete_after=5)

bot.run(TOKEN)
