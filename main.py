import discord
from discord.ext import commands
from discord import app_commands
import os
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

load_dotenv()

app = Flask('')

@app.route('/')
def home():
    return "Bot is Online and Active!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

class RaidView(discord.ui.View):
    def __init__(self, max_tanks, max_heals, max_dps):
        super().__init__(timeout=None)
        self.tanks, self.heals, self.dps = [], [], []
        self.waiting_list = []
        self.max_tanks = max_tanks
        self.max_heals = max_heals
        self.max_dps = max_dps

    async def update_embed(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]

        t_list = "\n".join([u.mention for u in self.tanks]) if self.tanks else "Empty"
        h_list = "\n".join([u.mention for u in self.heals]) if self.heals else "Empty"
        d_list = "\n".join([u.mention for u in self.dps]) if self.dps else "Empty"
        w_list = "\n".join([f"{u.mention} ({role})" for u, role in self.waiting_list]) if self.waiting_list else "Empty"

        embed.set_field_at(0, name=f"🛡️ Tanks ({len(self.tanks)}/{self.max_tanks})", value=t_list, inline=True)
        embed.set_field_at(1, name=f"⚕️ Healers ({len(self.heals)}/{self.max_heals})", value=h_list, inline=True)
        embed.set_field_at(2, name=f"⚔️ DPS ({len(self.dps)}/{self.max_dps})", value=d_list, inline=True)

        if len(embed.fields) > 3:
            embed.set_field_at(3, name="⏳ Waiting List", value=w_list, inline=False)
        else:
            embed.add_field(name="⏳ Waiting List", value=w_list, inline=False)

        await interaction.response.edit_message(embed=embed, view=self)

    def remove_user(self, user):
        self.tanks = [u for u in self.tanks if u != user]
        self.heals = [u for u in self.heals if u != user]
        self.dps = [u for u in self.dps if u != user]
        self.waiting_list = [item for item in self.waiting_list if item[0] != user]

    async def handle_join(self, interaction, current_list, max_slots, role_name):
        user = interaction.user
        if user in current_list:
            return await interaction.response.send_message(f"You are already signed up as a {role_name}!", ephemeral=True)

        self.remove_user(user)

        if len(current_list) < max_slots:
            current_list.append(user)
        else:
            self.waiting_list.append((user, role_name))

        await self.update_embed(interaction)

    @discord.ui.button(label="Tank", style=discord.ButtonStyle.primary, emoji="🛡️")
    async def tank_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_join(interaction, self.tanks, self.max_tanks, "Tank")

    @discord.ui.button(label="Healer", style=discord.ButtonStyle.success, emoji="⚕️")
    async def heal_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_join(interaction, self.heals, self.max_heals, "Healer")

    @discord.ui.button(label="DPS", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def dps_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_join(interaction, self.dps, self.max_dps, "DPS")

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.secondary)
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.remove_user(interaction.user)
        await self.update_embed(interaction)

@bot.event
async def on_ready():
    print(f"✅ Bot logged in as {bot.user}!")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} slash commands synced.")
    except Exception as e:
        print(f"❌ Sync error: {e}")

@bot.tree.command(name="raid", description="Create a raid announcement")
async def raid(interaction: discord.Interaction, boss: str, date: str, tanks: int = 1, healers: int = 2, dps: int = 7):
    embed = discord.Embed(
        title=f"📣 RAID: {boss}",
        description=f"📅 **Date/Time:** {date}\n\n*Click a button below to join the roster!*",
        color=discord.Color.blue()
    )
    embed.add_field(name=f"🛡️ Tanks (0/{tanks})", value="Empty", inline=True)
    embed.add_field(name=f"⚕️ Healers (0/{healers})", value="Empty", inline=True)
    embed.add_field(name=f"⚔️ DPS (0/{dps})", value="Empty", inline=True)

    await interaction.response.send_message(embed=embed, view=RaidView(tanks, healers, dps))

if __name__ == "__main__":
    keep_alive()
    token = os.getenv('DISCORD_TOKEN')
    if token:
        bot.run(token)
    else:
        print("❌ ERROR: DISCORD_TOKEN not found!")