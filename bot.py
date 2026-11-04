import datetime
import discord
from discord import app_commands
import os
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
@bot.tree.command(name="hierarquia", description="Exibe a hierarquia oficial e tabela de CDP do Exército do Shelby.")
async def hierarquia(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎖️ Hierarquia Oficial & CDP - Exército do Shelby",
        description="Escala de patentes e tempo de capacitação exigido:",
        color=discord.Color.gold()
    )
    
    embed.add_field(
        name="⭐ Oficiais Gerais",
        value="• `[GEN EX]` General de Exército – 85 horas\n• `[GEN DV]` General de Divisão – 80 horas\n• `[GEN BDA]` General de Brigada – 75 horas",
        inline=False
    )
    
    embed.add_field(
        name="⭐ Oficiais Superiores",
        value="• `[CEL]` Coronel – 70 horas\n• `[TEN-CEL]` Tenente Coronel – 65 horas\n• `[MAJ]` Major – 60 horas",
        inline=False
    )
    
    embed.add_field(
        name="⭐ Oficiais Intermediários",
        value="• `[CAP]` Capitão – 55 horas",
        inline=False
    )
    
    embed.add_field(
        name="⭐ Oficiais Subalternos",
        value="• `[1º TEN]` Primeiro Tenente – 50 horas\n• `[2º TEN]` Segundo Tenente – 45 horas\n• `[AAO]` Aspirante a Oficial – 40 horas",
        inline=False
    )
    
    embed.add_field(
        name="🛡️ Praças Especiais",
        value="• `[CT]` Cadete – 35 horas",
        inline=False
    )
    
    embed.add_field(
        name="🎖️ Graduados",
        value="• `[ST]` Subtenente – 30 horas\n• `[1º SGT]` Primeiro Sargento – 25 horas\n• `[2º SGT]` Segundo Sargento – 20 horas\n• `[3º SGT]` Terceiro Sargento – 15 horas",
        inline=False
    )
    
    embed.add_field(
        name="🎖️ Praças",
        value="• `[CB]` Cabo – 12 horas\n• `[SLD]` Soldado – 6 horas\n• `[REC]` Recruta – 3 horas",
        inline=False
    )
    
    embed.set_footer(text="Exército Brasileiro do Shelby • Sistema de Gestão")
    await interaction.response.send_message(embed=embed)
    


# Tabela de Patentes com Horas de CDP, Tag e Categoria com Emojis
PATENTES_CONFIG = {
    # Praças
    "[REC] Recruta": {"horas": 3, "tag": "[REC]", "categoria": "🌾 Militares Praças"},
    "[SLD] Soldado": {"horas": 6, "tag": "[SLD]", "categoria": "🌾 Militares Praças"},
    "[CB] Cabo": {"horas": 12, "tag": "[CB]", "categoria": "🌾 Militares Praças"},
    
    # Graduados
    "[T-SGT] Terceiro-Sargento": {"horas": 15, "tag": "[3º SGT]", "categoria": "🎓 Militares Graduados"},
    "[S-SGT] Segundo-Sargento": {"horas": 20, "tag": "[2º SGT]", "categoria": "🎓 Militares Graduados"},
    "[P-SGT] Primeiro-Sargento": {"horas": 25, "tag": "[1º SGT]", "categoria": "🎓 Militares Graduados"},
    "[ST] Subtenente": {"horas": 30, "tag": "[ST]", "categoria": "🎓 Militares Graduados"},
    
    # Praças Especiais
    "[CDT] Cadete": {"horas": 35, "tag": "[CT]", "categoria": "🪖 Praças Especiais"},
    
    # Oficiais Subalternos
    "[AAO] Aspirante a Oficial": {"horas": 40, "tag": "[AAO]", "categoria": "🗡️ Oficiais Subalternos"},
    "[S-TN] Segundo-Tenente": {"horas": 45, "tag": "[2º TEN]", "categoria": "🗡️ Oficiais Subalternos"},
    "[P-TN] Primeiro-Tenente": {"horas": 50, "tag": "[1º TEN]", "categoria": "🗡️ Oficiais Subalternos"},
    
    # Oficiais Intermediários
    "[CAP] Capitão": {"horas": 55, "tag": "[CAP]", "categoria": "⭐ Oficiais Intermediário"},
    
    # Oficiais Superiores
    "[MAJ] Major": {"horas": 60, "tag": "[MAJ]", "categoria": "🏅 Oficiais Superiores"},
    "[TN-COL] Tenente-Coronel": {"horas": 65, "tag": "[TEN-CEL]", "categoria": "🏅 Oficiais Superiores"},
    "[COL] Coronel": {"horas": 70, "tag": "[CEL]", "categoria": "🏅 Oficiais Superiores"},
    
    # Oficiais Generais
    "[GEN-BDA] General de Brigada": {"horas": 75, "tag": "[GEN BDA]", "categoria": "⚔️ Oficiais Gerais"},
    "[GEN-DV] General de Divisão": {"horas": 80, "tag": "[GEN DV]", "categoria": "⚔️ Oficiais Gerais"},
    "[GEN-EX] General de Exército": {"horas": 85, "tag": "[GEN EX]", "categoria": "⚔️ Oficiais Gerais"},
}

# Guarda o histórico de CDP dos membros em memória
historico_cdp = {}

@bot.tree.command(name="promover", description="Promove um militar, atribui os cargos automaticamente e ativa a CDP.")
async def promover(interaction: discord.Interaction, membro: discord.Member, cargo_patente: discord.Role):
    # AVISA O DISCORD QUE O BOT ESTÁ A PROCESSAR
    await interaction.response.defer()

    try:
        nome_cargo = cargo_patente.name
        config = PATENTES_CONFIG.get(nome_cargo)
        
        if not config:
            await interaction.followup.send(f"❌ O cargo **{nome_cargo}** não está registado na tabela de CDP.")
            return

        # Verificar CDP
        agora = datetime.datetime.now()
        if membro.id in historico_cdp:
            liberacao = historico_cdp[membro.id]
            if agora < liberacao:
                restante = liberacao - agora
                horas = restante.seconds // 3600
                minutos = (restante.seconds % 3600) // 60
                await interaction.followup.send(
                    f"🚫 **PROMOÇÃO BLOQUEADA!**\n{membro.mention} ainda está em CDP.\nFalta(m) **{restante.days}d {horas}h {minutos}m** para poder ser promovido novamente."
                )
                return

        # Procurar o cargo da Categoria de forma flexível (procura por parte do nome se necessário)
        nome_categoria = config["categoria"]
        cargo_categoria = discord.utils.get(interaction.guild.roles, name=nome_categoria)
        
        # Se não encontrar pelo nome exato com emoji, tenta procurar apenas pelo nome principal (ex: "Militares Praças")
        if not cargo_categoria:
            for r in interaction.guild.roles:
                if nome_categoria.lower() in r.name.lower():
                    cargo_categoria = r
                    break
        
        # Lista de cargos a adicionar
        cargos_para_adicionar = [cargo_patente]
        if cargo_categoria:
            cargos_para_adicionar.append(cargo_categoria)

        # Adiciona os cargos no servidor
        await membro.add_roles(*cargos_para_adicionar)

        # Atualizar Apelido
        tag = config["tag"]
        nome_limpo = membro.display_name.split("]")[-1].strip()
        novo_nick = f"{tag} {nome_limpo}"[:32]
        
        try:
            await membro.edit(nick=novo_nick)
        except Exception:
            pass

        # Registar CDP
        horas_cdp = config["horas"]
        data_liberacao = agora + datetime.timedelta(hours=horas_cdp)
        historico_cdp[membro.id] = data_liberacao

        # Definir texto da categoria para o Embed (com menção se encontrar, ou texto normal se não encontrar)
        texto_categoria = cargo_categoria.mention if cargo_categoria else nome_categoria

        # Resposta de Sucesso
        embed = discord.Embed(
            title="📈 Promoção Realizada com Sucesso!",
            description=f"O militar {membro.mention} foi promovido a **{cargo_patente.name}**!",
            color=discord.Color.green()
        )
        embed.add_field(name="🎖️ Cargos Atribuídos", value=f"• {cargo_patente.mention}\n• {texto_categoria}", inline=False)
        embed.add_field(name="⏳ Duração da CDP", value=f"**{horas_cdp} Horas**", inline=True)
        embed.add_field(name="🔓 Próxima Promoção", value=data_liberacao.strftime("%d/%m/%Y às %H:%M"), inline=False)
        embed.set_footer(text=f"Promovido por: {interaction.user.display_name}")

        await interaction.followup.send(embed=embed)

    except discord.Forbidden:
        await interaction.followup.send("❌ **Erro de Permissões:** O cargo do Bot no Discord precisa de estar **ACIMA** das patentes na lista de Cargos do Servidor!")
    except Exception as e:
        await interaction.followup.send(f"❌ **Ocorreu um erro interno:** `{e}`")
        


# Inicia o servidor web de suporte e o bot
keep_alive()
token = os.getenv("DISCORD_TOKEN")
bot.run(token)
