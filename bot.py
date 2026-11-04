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
    "[REC] Recruta": {"horas": 3, "tag": "[REC]", "categoria": "〘🌾〙  Militares Praças"},
    "[SLD] Soldado": {"horas": 6, "tag": "[SLD]", "categoria": "〘🌾〙  Militares Praças"},
    "[CB] Cabo": {"horas": 12, "tag": "[CB]", "categoria": "〘🌾〙  Militares Praças"},
    
    # Graduados
    "[T-SGT] Terceiro-Sargento": {"horas": 15, "tag": "[3º SGT]", "categoria": "〘🎓〙 Militares Graduados"},
    "[S-SGT] Segundo-Sargento": {"horas": 20, "tag": "[2º SGT]", "categoria": "〘🎓〙 Militares Graduados"},
    "[P-SGT] Primeiro-Sargento": {"horas": 25, "tag": "[1º SGT]", "categoria": "〘🎓〙 Militares Graduados"},
    "[ST] Subtenente": {"horas": 30, "tag": "[ST]", "categoria": "〘🎓〙 Militares Graduados"},
    
    # Praças Especiais
    "[CDT] Cadete": {"horas": 35, "tag": "[CT]", "categoria": "〘🪖〙 Praças Especiais"},
    
    # Oficiais Subalternos
    "[AAO] Aspirante a Oficial": {"horas": 40, "tag": "[AAO]", "categoria": "〘🗡️〙Oficiais Subalternos"},
    "[S-TN] Segundo-Tenente": {"horas": 45, "tag": "[2º TEN]", "categoria": "〘🗡️速Oficiais Subalternos"},
    "[P-TN] Primeiro-Tenente": {"horas": 50, "tag": "[1º TEN]", "categoria": "〘🗡️〙Oficiais Subalternos"},
    
    # Oficiais Intermediários
    "[CAP] Capitão": {"horas": 55, "tag": "[CAP]", "categoria": "〘⭐️〙Oficiais Intermediário"},
    
    # Oficiais Superiores
    "[MAJ] Major": {"horas": 60, "tag": "[MAJ]", "categoria": "〘🏅〙Oficiais Superiores"},
    "[TN-COL] Tenente-Coronel": {"horas": 65, "tag": "[TEN-CEL]", "categoria": "〘🏅〙Oficiais Superiores"},
    "[COL] Coronel": {"horas": 70, "tag": "[CEL]", "categoria": "〘🏅〙Oficiais Superiores"},
    
    # Oficiais Generais
    "[GEN-BDA] General de Brigada": {"horas": 75, "tag": "[GEN BDA]", "categoria": "〘⚔️〙Oficiais Generais"},
    "[GEN-DV] General de Divisão": {"horas": 80, "tag": "[GEN DV]", "categoria": "〘⚔️〙Oficiais Generais"},
    "[GEN-EX] General de Exército": {"horas": 85, "tag": "[GEN EX]", "categoria": "〘⚔️〙Oficiais Generais"},
}

# Guarda o histórico de CDP dos membros em memória
historico_cdp = {}

@bot.tree.command(name="promover", description="Promove um militar, atribui os cargos automaticamente e ativa a CDP.")
async def promover(interaction: discord.Interaction, membro: discord.Member, cargo_patente: discord.Role):
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

        # Busca pelo nome exato do cargo de Categoria configurado
        nome_categoria = config["categoria"]
        cargo_categoria = discord.utils.get(interaction.guild.roles, name=nome_categoria)
        
        # Lista de cargos a adicionar
        cargos_para_adicionar = [cargo_patente]
        if cargo_categoria:
            cargos_para_adicionar.append(cargo_categoria)

        # Adiciona os cargos ao membro
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

        # Define o texto da categoria: se encontrar o cargo, usa a menção (@)
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
    

@bot.tree.command(name="rebaixar", description="Rebaixa um militar, atualiza os cargos, apelido e reseta a CDP.")
async def rebaixar(interaction: discord.Interaction, membro: discord.Member, cargo_patente_nova: discord.Role):
    await interaction.response.defer()

    try:
        nome_cargo_novo = cargo_patente_nova.name
        config_nova = PATENTES_CONFIG.get(nome_cargo_novo)
        
        if not config_nova:
            await interaction.followup.send(f"❌ O cargo **{nome_cargo_novo}** não está registado na tabela de CDP.")
            return

        # 1. Identificar Patente e Categoria Antigas pelo Apelido do Membro
        patente_antiga_nome = "Desconhecida"
        config_antiga = None
        cargo_patente_antigo = None
        cargo_categoria_antigo = None

        # Procurar qual tag de patente o membro possui atualmente no nick
        for nome_p, cfg in PATENTES_CONFIG.items():
            if cfg["tag"] in membro.display_name:
                patente_antiga_nome = nome_p
                config_antiga = cfg
                cargo_patente_antigo = discord.utils.get(interaction.guild.roles, name=nome_p)
                if cfg["categoria"]:
                    cargo_categoria_antigo = discord.utils.get(interaction.guild.roles, name=cfg["categoria"])
                break

        # 2. Procurar Categoria Nova
        nome_cat_nova = config_nova["categoria"]
        cargo_cat_novo = discord.utils.get(interaction.guild.roles, name=nome_cat_nova)

        # 3. Remover Cargos Antigos e Adicionar Novos
        cargos_remover = []
        if cargo_patente_antigo:
            cargos_remover.append(cargo_patente_antigo)
        # Só remove a categoria antiga se a pessoa mudar de categoria
        if cargo_categoria_antigo and config_antiga and config_antiga["categoria"] != nome_cat_nova:
            cargos_remover.append(cargo_categoria_antigo)

        if cargos_remover:
            try:
                await membro.remove_roles(*cargos_remover)
            except Exception:
                pass

        cargos_adicionar = [cargo_patente_nova]
        if cargo_cat_novo:
            cargos_adicionar.append(cargo_cat_novo)

        await membro.add_roles(*cargos_adicionar)

        # 4. Atualizar Apelido com a Nova Tag
        tag_nova = config_nova["tag"]
        nome_limpo = membro.display_name.split("]")[-1].strip()
        novo_nick = f"{tag_nova} {nome_limpo}"[:32]

        try:
            await membro.edit(nick=novo_nick)
        except Exception:
            pass

        # 5. Atualizar/Resetar CDP para o novo cargo
        agora = datetime.datetime.now()
        horas_cdp = config_nova["horas"]
        data_liberacao = agora + datetime.timedelta(hours=horas_cdp)
        historico_cdp[membro.id] = data_liberacao

        # Formatação das menções/textos para o Embed
        texto_patente_antiga = cargo_patente_antigo.mention if cargo_patente_antigo else patente_antiga_nome
        texto_cat_antiga = cargo_categoria_antigo.mention if cargo_categoria_antigo else (config_antiga["categoria"] if config_antiga else "Sem Categoria")
        texto_cat_nova = cargo_cat_novo.mention if cargo_cat_novo else nome_cat_nova

        # 6. Embed de Sucesso
        embed = discord.Embed(
            title="🔻 Rebaixamento Realizado!",
            description=f"O militar {membro.mention} foi rebaixado.",
            color=discord.Color.red()
        )
        embed.add_field(
            name="📊 Situação Anterior", 
            value=f"• **Patente:** {texto_patente_antiga}\n• **Categoria:** {texto_cat_antiga}", 
            inline=False
        )
        embed.add_field(
            name="🎖️ Nova Situação", 
            value=f"• **Patente:** {cargo_patente_nova.mention}\n• **Categoria:** {texto_cat_nova}", 
            inline=False
        )
        embed.add_field(name="⏳ Duração da CDP", value=f"**{horas_cdp} Horas**", inline=True)
        embed.add_field(name="🔓 Próxima Promoção", value=data_liberacao.strftime("%d/%m/%Y às %H:%M"), inline=False)
        embed.set_footer(text=f"Rebaixado por: {interaction.user.display_name}")

        await interaction.followup.send(embed=embed)

    except discord.Forbidden:
        await interaction.followup.send("❌ **Erro de Permissões:** O cargo do Bot precisa de estar **ACIMA** dos cargos a remover/adicionar na lista do servidor!")
    except Exception as e:
        await interaction.followup.send(f"❌ **Ocorreu um erro interno:** `{e}`")
        


# Inicia o servidor web de suporte e o bot
keep_alive()
token = os.getenv("DISCORD_TOKEN")
bot.run(token)
