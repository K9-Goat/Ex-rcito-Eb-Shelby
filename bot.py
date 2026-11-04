import os
import discord
from discord import app_commands
from discord.ext import commands
import requests
from flask import Flask
from threading import Thread

# ---------------------------------------------------------
# SERVIDOR WEB (Para manter o bot acordado no Render)
# ---------------------------------------------------------
app = Flask('')

@app.route('/')
def home():
    return "O Bot do Exército Brasileiro do Shelby está online!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# ---------------------------------------------------------
# CONFIGURAÇÕES DO SERVIDOR
# ---------------------------------------------------------
ROBLOX_GROUP_ID = 674505905  # Substitua pelo ID numérico do seu Grupo no Roblox
NOME_CARGO_ISENCAO = "Permite Trocar Nick"

PATENT_DATA = {
    "General de Exército": {"tag": "[GEN EX]", "tempo": "85 horas"},
    "General de Divisão": {"tag": "[GEN DV]", "tempo": "80 horas"},
    "General de Brigada": {"tag": "[GEN BDA]", "tempo": "75 horas"},
    "Coronel": {"tag": "[CEL]", "tempo": "70 horas"},
    "Tenente Coronel": {"tag": "[TEN-CEL]", "tempo": "65 horas"},
    "Major": {"tag": "[MAJ]", "tempo": "60 horas"},
    "Capitão": {"tag": "[CAP]", "tempo": "55 horas"},
    "Primeiro Tenente": {"tag": "[1º TEN]", "tempo": "50 horas"},
    "Segundo Tenente": {"tag": "[2º TEN]", "tempo": "45 horas"},
    "Aspirante a Oficial": {"tag": "[AAO]", "tempo": "40 horas"},
    "Cadete": {"tag": "[CT]", "tempo": "35 horas"},
    "Subtenente": {"tag": "[ST]", "tempo": "30 horas"},
    "Primeiro Sargento": {"tag": "[1º SGT]", "tempo": "25 horas"},
    "Segundo Sargento": {"tag": "[2º SGT]", "tempo": "20 horas"},
    "Terceiro Sargento": {"tag": "[3º SGT]", "tempo": "15 horas"},
    "Cabo": {"tag": "[CB]", "tempo": "12 horas"},
    "Soldado": {"tag": "[SLD]", "tempo": "6 horas"},
    "Recruta": {"tag": "[REC]", "tempo": "3 horas"}
}

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

class ExercitoBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Comandos Slash sincronizados com sucesso!")

bot = ExercitoBot()
apelidos_oficiais = {}

@bot.tree.command(name="cdp", description="Exibe a tabela de capacitação de patentes.")
async def cdp(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎖️ Tabela de Capacitação de Patentes (CDP)",
        description="Tempo de espera regulamentar para cada patente:",
        color=discord.Color.dark_green()
    )
    for nome, dados in PATENT_DATA.items():
        embed.add_field(name=f"{dados['tag']} {nome}", value=f"⏱️ `{dados['tempo']}`", inline=True)
    embed.set_footer(text="Exército Brasileiro - The Shelby")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="sincronizar", description="Sincroniza seu cargo do Roblox com o Discord.")
@app_commands.describe(roblox_username="Seu nome de usuário exato no Roblox")
async def sincronizar(interaction: discord.Interaction, roblox_username: str):
    await interaction.response.defer(ephemeral=True)
    try:
        url_user = "https://users.roblox.com/v1/usernames/users"
        res_user = requests.post(url_user, json={"usernames": [roblox_username], "excludeBannedUsers": True}).json()
        if not res_user.get("data"):
            await interaction.followup.send("❌ Usuário do Roblox não encontrado.")
            return

        user_id = res_user["data"][0]["id"]
        roblox_real_name = res_user["data"][0]["name"]

        url_roles = f"https://groups.roblox.com/v2/users/{user_id}/groups/roles"
        res_roles = requests.get(url_roles).json()

        roblox_rank_name = None
        if "data" in res_roles:
            for group in res_roles["data"]:
                if group["group"]["id"] == ROBLOX_GROUP_ID:
                    roblox_rank_name = group["role"]["name"]
                    break

        if not roblox_rank_name:
            await interaction.followup.send("❌ Você não faz parte do grupo do Exército no Roblox.")
            return

        member = interaction.user
        tag = ""
        for patente_nome, dados in PATENT_DATA.items():
            if patente_nome.lower() in roblox_rank_name.lower():
                tag = dados["tag"]
                break

        novo_nick = f"{tag} {roblox_real_name}".strip() if tag else roblox_real_name
        role_discord = discord.utils.get(interaction.guild.roles, name=roblox_rank_name)
        if role_discord:
            await member.add_roles(role_discord)

        try:
            await member.edit(nick=novo_nick)
            apelidos_oficiais[member.id] = novo_nick
            msg_status = f"Seu apelido foi alterado para: `{novo_nick}` e travado com sucesso."
        except discord.Forbidden:
            msg_status = "⚠️ Cargo atualizado, mas sem permissão para alterar o apelido."

        embed = discord.Embed(
            title="✅ Sincronização Realizada com Sucesso",
            description=f"**Militar:** {member.mention}\n**Patente no Roblox:** `{roblox_rank_name}`\n{msg_status}",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Ocorreu um erro durante a sincronização: {e}")

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if before.nick == after.nick:
        return
    tem_permissao = any(role.name == NOME_CARGO_ISENCAO for role in after.roles)
    if tem_permissao:
        return
    if after.id in apelidos_oficiais:
        nome_correto = apelidos_oficiais[after.id]
        if after.nick != nome_correto:
            try:
                await after.edit(nick=nome_correto)
            except discord.Forbidden:
                pass

# Inicia o servidor web de suporte e o bot
keep_alive()
token = os.getenv("DISCORD_TOKEN")
bot.run(token)
