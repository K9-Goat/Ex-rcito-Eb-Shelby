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
    


    # Mapeamento do Nível de Autoridade (quanto maior o número, maior a autoridade)
HIERARQUIA_CATEGORIAS = {
    "〘🌾轮  Militares Praças": 1,
    "〘🎓轮 Militares Graduados": 2,
    "〘🪖轮 Praças Especiais": 3,
    "〘🗡️轮Oficiais Subalternos": 4,
    "〘⭐️轮Oficiais Intermediário": 5,
    "〘🏅轮Oficiais Superiores": 6,
    "〘⚔️轮Oficiais Generais": 7,
}


    # Tabela de permissão exclusiva para rebaixar (quanto maior o número, maior o poder)
CARGOS_REBAIXAR_PERMISSAO = {
    "〘⚖️〙 Secretaria-Geral do Exército": 1,
    "[L-DEV] Leader Developer": 2,
    "〘🛠️〙 Administração": 3,
    "[Sb] Sub criador": 4,
    "[Cr] Creator": 5,
}

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

@bot.tree.command(name="promover", description="Promove um militar respeitando as permissões da hierarquia.")
async def promover(interaction: discord.Interaction, membro: discord.Member, cargo_patente: discord.Role):
    await interaction.response.defer()

    nome_cargo_novo = cargo_patente.name
    config_novo = PATENTES_CONFIG.get(nome_cargo_novo)

    if not config_novo:
        await interaction.followup.send(f"❌ O cargo **{nome_cargo_novo}** não está registrado na tabela de CDP.")
        return

    # 1. Identificar a Categoria do Autor da Promoção
    nivel_autor = 0

    if interaction.user.guild_permissions.administrator:
        nivel_autor = 7
    else:
        for role in interaction.user.roles:
            if any(termo in role.name for termo in ["General", "[GEN-", "Oficiais Gerais", "⚔️"]):
                nivel_autor = max(nivel_autor, 7)
            elif "🏅" in role.name or "Superiores" in role.name:
                nivel_autor = max(nivel_autor, 6)
            elif "⭐️" in role.name or "Intermediário" in role.name:
                nivel_autor = max(nivel_autor, 5)
            elif "🗡️" in role.name or "Subalternos" in role.name:
                nivel_autor = max(nivel_autor, 4)
            elif "🪖" in role.name or "Especiais" in role.name:
                nivel_autor = max(nivel_autor, 3)
            elif "🎓" in role.name or "Graduados" in role.name:
                nivel_autor = max(nivel_autor, 2)
            elif "🌾" in role.name or "Praças" in role.name:
                nivel_autor = max(nivel_autor, 1)

    # 2. Regras de Permissão por Categoria de Autor
    cat_destino = config_novo["categoria"]
    nivel_destino = HIERARQUIA_CATEGORIAS.get(cat_destino, 0)

    if nivel_autor <= 3:
        await interaction.followup.send("❌ **PROMOÇÃO NEGADA!** Praças, Graduados e Praças Especiais não têm permissão para promover.")
        return
    elif nivel_autor == 4 and nivel_destino > 1:
        await interaction.followup.send("❌ **PROMOÇÃO NEGADA!** Oficiais Subalternos só podem promover Praças.")
        return
    elif nivel_autor == 5 and nivel_destino > 3:
        await interaction.followup.send("❌ **PROMOÇÃO NEGADA!** Oficiais Intermediários só podem promover Praças, Graduados e Praças Especiais.")
        return
    elif nivel_autor == 6 and nivel_destino > 5:
        await interaction.followup.send("❌ **PROMOÇÃO NEGADA!** Oficiais Superiores não podem promover para cargos de Oficial Superior ou General.")
        return

    # 3. Verificar CDP do Alvo
    agora = datetime.datetime.now()
    if membro.id in historico_cdp:
        liberacao = historico_cdp[membro.id]
        if agora < liberacao:
            restante = liberacao - agora
            horas = restante.seconds // 3600
            minutos = (restante.seconds % 3600) // 60
            await interaction.followup.send(
                f"❌ **PROMOÇÃO BLOQUEADA!** {membro.mention} ainda está em CDP. Falta(m) **{restante.days}d {horas}h {minutos}m**."
            )
            return

    # 4. Processar Troca de Cargos
    cargo_categoria = discord.utils.get(interaction.guild.roles, name=cat_destino)

    cargos_para_adicionar = [cargo_patente]
    if cargo_categoria:
        cargos_para_adicionar.append(cargo_categoria)

    await membro.add_roles(*cargos_para_adicionar)

    # Atualizar Apelido
    tag = config_novo["tag"]
    nome_limpo = membro.display_name.split("]")[-1].strip()
    novo_nick = f"{tag} {nome_limpo}"[:32]

    try:
        await membro.edit(nick=novo_nick)
    except Exception:
        pass

    # Registar CDP
    horas_cdp = config_novo["horas"]
    data_liberacao = agora + datetime.timedelta(hours=horas_cdp)
    historico_cdp[membro.id] = data_liberacao

    # Formatação de Embed
    texto_categoria = cargo_categoria.mention if cargo_categoria else cat_destino

    embed = discord.Embed(
        title="🏆 Promoção Realizada com Sucesso!",
        description=f"O militar {membro.mention} foi promovido a **{cargo_patente.name}**!",
        color=discord.Color.green()
    )
    embed.add_field(name="📌 Cargos Atribuídos", value=f"{cargo_patente.mention}\n{texto_categoria}", inline=False)
    embed.add_field(name="⏳ Duração da CDP", value=f"{horas_cdp} Horas", inline=True)
    embed.add_field(name="🕒 Próxima Promoção", value=data_liberacao.strftime('%d/%m/%Y às %H:%M'), inline=True)
    embed.set_footer(text=f"Promovido por {interaction.user.display_name}")

    await interaction.followup.send(embed=embed)
    

    

@bot.tree.command(name="rebaixar", description="Rebaixa um militar, atualiza os cargos, apelido e reseta a CDP.")
async def rebaixar(interaction: discord.Interaction, membro: discord.Member, cargo_patente_nova: discord.Role):
    await interaction.response.defer()

    # 1. Verificar se o Autor tem um dos 5 cargos autorizados
    nivel_autor = 0
    for role in interaction.user.roles:
        if role.name in CARGOS_REBAIXAR_PERMISSAO:
            nivel_autor = max(nivel_autor, CARGOS_REBAIXAR_PERMISSAO[role.name])
            
        if nivel_autor == 0:
            await interaction.followup.send("🚫 **REBAIXAMENTO NEGADO!** Apenas membros da Secretaria-Geral, Leader Developer, Administração, Sub Criador ou Creator podem rebaixar.")
            return

        nome_cargo_novo = cargo_patente_nova.name
        config_nova = PATENTES_CONFIG.get(nome_cargo_novo)
        
        if not config_nova:
            await interaction.followup.send(f"❌ O cargo **{nome_cargo_novo}** não está registado na tabela de CDP.")
            return

        # 2. Identificar Patente e Categoria Antigas pelo Apelido do Membro
        patente_antiga_nome = "Desconhecida"
        config_antiga = None
        cargo_patente_antigo = None
        cargo_categoria_antigo = None

        for nome_p, cfg in PATENTES_CONFIG.items():
            if cfg["tag"] in membro.display_name:
                patente_antiga_nome = nome_p
                config_antiga = cfg
                cargo_patente_antigo = discord.utils.get(interaction.guild.roles, name=nome_p)
                if cfg["categoria"]:
                    cargo_categoria_antigo = discord.utils.get(interaction.guild.roles, name=cfg["categoria"])
                break

        # 3. Remover Cargos Antigos e Adicionar Novos
        nome_cat_nova = config_nova["categoria"]
        cargo_cat_novo = discord.utils.get(interaction.guild.roles, name=nome_cat_nova)

        cargos_remover = []
        if cargo_patente_antigo:
            cargos_remover.append(cargo_patente_antigo)
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

        # 5. Resetar CDP
        agora = datetime.datetime.now()
        horas_cdp = config_nova["horas"]
        data_liberacao = agora + datetime.timedelta(hours=horas_cdp)
        historico_cdp[membro.id] = data_liberacao

        # Formatação Embed
        texto_patente_antiga = cargo_patente_antigo.mention if cargo_patente_antigo else patente_antiga_nome
        texto_cat_antiga = cargo_categoria_antigo.mention if cargo_categoria_antigo else (config_antiga["categoria"] if config_antiga else "Sem Categoria")
        texto_cat_nova = cargo_cat_novo.mention if cargo_cat_novo else nome_cat_nova

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
        await interaction.followup.send("❌ **Erro de Permissões:** O cargo do Bot precisa de estar **ACIMA** dos cargos a gerir!")
    except Exception as e:
        await interaction.followup.send(f"❌ **Ocorreu um erro interno:** `{e}`")
                                                               
@bot.tree.command(name="promover_varios", description="Promove até 5 militares de uma só vez respeitando a hierarquia e CDP.")
async def promover_varios(
    interaction: discord.Interaction, 
    cargo_patente: discord.Role,
    membro1: discord.Member,
    membro2: discord.Member = None,
    membro3: discord.Member = None,
    membro4: discord.Member = None,
    membro5: discord.Member = None
):
    await interaction.response.defer()

    try:
        nome_cargo_novo = cargo_patente.name
        config_novo = PATENTES_CONFIG.get(nome_cargo_novo)
        
        if not config_novo:
            await interaction.followup.send(f"❌ O cargo **{nome_cargo_novo}** não está registado na tabela de CDP.")
            return

        categoria_autor = None
        nivel_autor = 0

        for nome_p, cfg in PATENTES_CONFIG.items():
            if cfg["tag"] in interaction.user.display_name:
                categoria_autor = cfg["categoria"]
                nivel_autor = HIERARQUIA_CATEGORIAS.get(categoria_autor, 0)
                break

        if nivel_autor == 0:
            for role in interaction.user.roles:
                if role.name in HIERARQUIA_CATEGORIAS:
                    categoria_autor = role.name
                    nivel_autor = HIERARQUIA_CATEGORIAS[role.name]
                    break

        cat_destino = config_novo["categoria"]
        nivel_destino = HIERARQUIA_CATEGORIAS.get(cat_destino, 0)

        if nivel_autor <= 3:
            await interaction.followup.send("🚫 **PROMOÇÃO NEGADA!** Praças, Graduados e Praças Especiais não têm permissão para promover.")
            return
        elif nivel_autor == 4 and nivel_destino > 1:
            await interaction.followup.send("🚫 **PROMOÇÃO NEGADA!** Oficiais Subalternos só podem promover **Praças**.")
            return
        elif nivel_autor == 5 and nivel_destino > 2:
            await interaction.followup.send("🚫 **PROMOÇÃO NEGADA!** Oficiais Intermediários só podem promover **Praças e Graduados**.")
            return
        elif nivel_autor == 6 and nivel_destino > 4:
            await interaction.followup.send("🚫 **PROMOÇÃO NEGADA!** Oficiais Superiores não podem promover para cargos deste nível.")
            return
        elif nivel_autor == 7 and nivel_destino >= 7:
            await interaction.followup.send("🚫 **PROMOÇÃO NEGADA!** Generais não podem promover para cargos de nível General ou superior.")
            return

        membros_raw = [membro1, membro2, membro3, membro4, membro5]
        membros = list(dict.fromkeys([m for m in membros_raw if m is not None]))

        cargo_categoria = discord.utils.get(interaction.guild.roles, name=cat_destino)
        agora = datetime.datetime.now()
        horas_cdp = config_novo["horas"]
        data_liberacao = agora + datetime.timedelta(hours=horas_cdp)

        promovidos = []
        bloqueados_cdp = []

        for membro in membros:
            if membro.id in historico_cdp:
                liberacao = historico_cdp[membro.id]
                if agora < liberacao:
                    restante = liberacao - agora
                    horas = restante.seconds // 3600
                    minutos = (restante.seconds % 3600) // 60
                    bloqueados_cdp.append(f"• {membro.mention} *(Falta: {restante.days}d {horas}h {minutos}m)*")
                    continue

            cargos_para_adicionar = [cargo_patente]
            if cargo_categoria:
                cargos_para_adicionar.append(cargo_categoria)

            await membro.add_roles(*cargos_para_adicionar)

            tag = config_novo["tag"]
            nome_limpo = membro.display_name.split("]")[-1].strip()
            novo_nick = f"{tag} {nome_limpo}"[:32]
            try:
                await membro.edit(nick=novo_nick)
            except Exception:
                pass

            historico_cdp[membro.id] = data_liberacao
            promovidos.append(membro.mention)

        texto_categoria = cargo_categoria.mention if cargo_categoria else cat_destino

        embed = discord.Embed(
            title="📈 Promoção em Massa Realizada!",
            description=f"Novo Cargo: **{cargo_patente.name}**\nCategoria: {texto_categoria}",
            color=discord.Color.green()
        )

        if promovidos:
            embed.add_field(name="✅ Militares Promovidos", value="\n".join([f"• {m}" for m in promovidos]), inline=False)
        else:
            embed.add_field(name="⚠️ Militares Promovidos", value="Nenhum militar foi promovido.", inline=False)

        if bloqueados_cdp:
            embed.add_field(name="🚫 Bloqueados por CDP", value="\n".join(bloqueados_cdp), inline=False)

        embed.add_field(name="⏳ CDP Aplicada", value=f"**{horas_cdp} Horas** (até {data_liberacao.strftime('%d/%m/%Y às %H:%M')})", inline=False)
        embed.set_footer(text=f"Promovidos por: {interaction.user.display_name}")

        await interaction.followup.send(embed=embed)

    except discord.Forbidden:
        await interaction.followup.send("❌ **Erro de Permissões:** O cargo do Bot precisa de estar **ACIMA** dos cargos na lista do servidor!")
    except Exception as e:
        await interaction.followup.send(f"❌ **Ocorreu um erro interno:** `{e}`")



@bot.tree.command(name="rebaixar_varios", description="Rebaixa até 5 militares de uma só vez respeitando as permissões administrativas.")
async def rebaixar_varios(
    interaction: discord.Interaction, 
    cargo_patente_nova: discord.Role,
    membro1: discord.Member,
    membro2: discord.Member = None,
    membro3: discord.Member = None,
    membro4: discord.Member = None,
    membro5: discord.Member = None
):
    await interaction.response.defer()

    try:
        nivel_autor = 0
        for role in interaction.user.roles:
            if role.name in CARGOS_REBAIXAR_PERMISSAO:
                nivel_autor = max(nivel_autor, CARGOS_REBAIXAR_PERMISSAO[role.name])

        if nivel_autor == 0:
            await interaction.followup.send("🚫 **REBAIXAMENTO NEGADO!** Apenas membros autorizados podem usar este comando.")
            return

        nome_cargo_novo = cargo_patente_nova.name
        config_nova = PATENTES_CONFIG.get(nome_cargo_novo)
        
        if not config_nova:
            await interaction.followup.send(f"❌ O cargo **{nome_cargo_novo}** não está registado na tabela de CDP.")
            return

        membros_raw = [membro1, membro2, membro3, membro4, membro5]
        membros = list(dict.fromkeys([m for m in membros_raw if m is not None]))

        nome_cat_nova = config_nova["categoria"]
        cargo_cat_novo = discord.utils.get(interaction.guild.roles, name=nome_cat_nova)
        agora = datetime.datetime.now()
        horas_cdp = config_nova["horas"]
        data_liberacao = agora + datetime.timedelta(hours=horas_cdp)

        rebaixados = []

        for membro in membros:
            config_antiga = None
            cargo_patente_antigo = None
            cargo_categoria_antigo = None

            for nome_p, cfg in PATENTES_CONFIG.items():
                if cfg["tag"] in membro.display_name:
                    config_antiga = cfg
                    cargo_patente_antigo = discord.utils.get(interaction.guild.roles, name=nome_p)
                    if cfg["categoria"]:
                        cargo_categoria_antigo = discord.utils.get(interaction.guild.roles, name=cfg["categoria"])
                    break

            cargos_remover = []
            if cargo_patente_antigo:
                cargos_remover.append(cargo_patente_antigo)
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

            tag_nova = config_nova["tag"]
            nome_limpo = membro.display_name.split("]")[-1].strip()
            novo_nick = f"{tag_nova} {nome_limpo}"[:32]
            try:
                await membro.edit(nick=novo_nick)
            except Exception:
                pass

            historico_cdp[membro.id] = data_liberacao
            rebaixados.append(membro.mention)

        texto_cat_novo = cargo_cat_novo.mention if cargo_cat_novo else nome_cat_nova

        embed = discord.Embed(
            title="🔻 Rebaixamento em Massa Realizado!",
            description=f"Novo Cargo: **{cargo_patente_nova.name}**\nNova Categoria: {texto_cat_novo}",
            color=discord.Color.red()
        )
        embed.add_field(name="📉 Militares Rebaixados", value="\n".join([f"• {m}" for m in rebaixados]), inline=False)
        embed.add_field(name="⏳ Nova CDP Aplicada", value=f"**{horas_cdp} Horas** (até {data_liberacao.strftime('%d/%m/%Y às %H:%M')})", inline=False)
        embed.set_footer(text=f"Rebaixados por: {interaction.user.display_name}")

        await interaction.followup.send(embed=embed)

    except discord.Forbidden:
        await interaction.followup.send("❌ **Erro de Permissões:** O cargo do Bot precisa de estar **ACIMA** dos cargos na lista do servidor!")
    except Exception as e:
        await interaction.followup.send(f"❌ **Ocorreu um erro interno:** `{e}`")

@bot.tree.command(name="sincroniza-comandos", description="Força a sincronização de todos os comandos no servidor.")
async def sincroniza_comandos(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    try:
        synced = await bot.tree.sync(guild=interaction.guild)
        await interaction.followup.send(f"✅ Sincronizado com sucesso! Total de comandos ativos: **{len(synced)}**.")
    except Exception as e:
        await interaction.followup.send(f"❌ Erro ao sincronizar: `{e}`")
        



@bot.event
async def on_ready():
    print(f"Bot ligado com sucesso como {bot.user}!")
    try:
        MEU_SERVIDOR = discord.Object(id=155569528807568122)
        
        # Sincroniza diretamente todos os comandos do bot no teu servidor de forma limpa
        synced = await bot.tree.sync(guild=MEU_SERVIDOR)
        print(f"Comandos sincronizados com sucesso no servidor: {len(synced)}")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")
        
        

# Mantém o servidor web ativo e inicia o bot
keep_alive()
token = os.getenv("DISCORD_TOKEN")
bot.run(token)
