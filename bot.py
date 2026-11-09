import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
import datetime
import os
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- CONFIGURAÇÕES ---
ROBLOX_GROUP_ID = 674505905  # Substitui pelo ID real do grupo do Roblox

# --- HIERARQUIA E PATENTES ---
HIERARQUIA_CATEGORIAS = {
    "〘🌾〙  Militares Praças": 1,
    "〘🎓〙 Militares Graduados": 2,
    "〘🪖〙 Praças Especiais": 3,
    "〘🗡️〙Oficiais Subalternos": 4,
    "〘⭐️〙Oficiais Intermediário": 5,
    "〘🏅〙Oficiais Superiores": 6,
    "〘⚔️〙Oficiais Generais": 7,
}

CARGOS_REBAIXAR_PERMISSAO = {
    "〘⚖️〙 Secretaria-Geral do Exército": 1,
    "[L-DEV] Leader Developer": 2,
    "〘🔥〙 Administração": 3,
    "[Sb] Sub criador": 4,
    "[Cr] Creator": 5,
}

PATENTES_CONFIG = {
    # Praças
    "[REC] Recruta": {"horas": 3, "tag": "[REC]", "categoria": "〘🌾〙  Militares Praças"},
    "[SLD] Soldado": {"horas": 6, "tag": "[SLD]", "categoria": "〘🌾〙  Militares Praças"},
    "[CB] Cabo": {"horas": 12, "tag": "[CB]", "categoria": "〘🌾〙  Militares Praças"},

    # Graduados
    "[T-SGT] Terceiro-Sargento": {"horas": 15, "tag": "[T-SGT]", "categoria": "〘🎓〙 Militares Graduados"},
    "[S-SGT] Segundo-Sargento": {"horas": 20, "tag": "[S-SGT]", "categoria": "〘🎓〙 Militares Graduados"},
    "[P-SGT] Primeiro-Sargento": {"horas": 25, "tag": "[P-SGT]", "categoria": "〘🎓〙 Militares Graduados"},
    "[ST] Subtenente": {"horas": 30, "tag": "[ST]", "categoria": "〘🎓〙 Militares Graduados"},

    # Praças Especiais
    "[CDT] Cadete": {"horas": 35, "tag": "[CDT]", "categoria": "〘🪖〙 Praças Especiais"},

    # Oficiais Subalternos
    "[AAO] Aspirante a Oficial": {"horas": 40, "tag": "[AAO]", "categoria": "〘🗡️〙Oficiais Subalternos"},
    "[S-TN] Segundo-Tenente": {"horas": 45, "tag": "[S-TEN]", "categoria": "〘🗡️〙Oficiais Subalternos"},
    "[P-TN] Primeiro-Tenente": {"horas": 50, "tag": "[P-TEN]", "categoria": "〘🗡️〙Oficiais Subalternos"},

    # Oficiais Intermediários
    "[CAP] Capitão": {"horas": 55, "tag": "[CAP]", "categoria": "〘⭐️〙Oficiais Intermediário"},

    # Oficiais Superiores
    "[MJ] Major": {"horas": 60, "tag": "[MJ]", "categoria": "〘🏅〙Oficiais Superiores"},
    "[TEN-CEL] Tenente-Coronel": {"horas": 65, "tag": "[TEN-CEL]", "categoria": "〘🏅〙Oficiais Superiores"},
    "[CEL] Coronel": {"horas": 70, "tag": "[CEL]", "categoria": "〘🏅〙Oficiais Superiores"},

    # Oficiais Generais
    "[GEN-BDA] General de brigada": {"horas": 75, "tag": "[GEN-BDA]", "categoria": "〘⚔️〙Oficiais Generais"},
    "[GEN-DV] General de Divisão": {"horas": 80, "tag": "[GEN-DV]", "categoria": "〘⚔️〙Oficiais Generais"},
    "[GEN-EX] General de Exército": {"horas": 85, "tag": "[GEN-EX]", "categoria": "〘⚔️〙Oficiais Generais"},
}

contas_verificadas = {}
historico_cdp = {}

# --- EVENTO ON_READY OTIMIZADO ---
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ Bot online como {bot.user} | Comandos sincronizados: {len(synced)}")
    except Exception as e:
        print(f"❌ Erro ao sincronizar comandos: {e}")

def verificar_nivel_autor(user):
    if user.guild_permissions.administrator:
        return 7
    nivel_autor = 0
    for role in user.roles:
        if any(termo in role.name for termo in ["General", "[GEN-", "Oficiais Generais", "⚔️"]):
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
    return nivel_autor


# --- 1. COMANDO: /verificar ---
@bot.tree.command(name="verificar", description="Verifica a tua conta do Roblox e atribui os cargos correspondentes no Discord.")
@app_commands.describe(username="O teu nome de utilizador (username) no Roblox")
async def verificar(interaction: discord.Interaction, username: str):
    await interaction.response.defer(ephemeral=True)

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            url_user = "https://users.roblox.com/v1/usernames/users"
            payload = {"usernames": [username], "excludeBannedUsers": True}
            async with session.post(url_user, json=payload) as resp_user:
                if resp_user.status != 200:
                    await interaction.followup.send("❌ Erro ao comunicar com a API do Roblox. Tenta novamente mais tarde.", ephemeral=True)
                    return
                
                data_user = await resp_user.json()
                users = data_user.get("data", [])
                if not users:
                    await interaction.followup.send(f"❌ Não foi encontrada nenhuma conta no Roblox com o nome **{username}**.", ephemeral=True)
                    return
                
                roblox_user_id = users[0]["id"]
                roblox_display = users[0]["displayName"]
                roblox_name = users[0]["name"]

            url_role = f"https://groups.roblox.com/v1/users/{roblox_user_id}/groups/roles"
            async with session.get(url_role) as resp_role:
                if resp_role.status != 200:
                    await interaction.followup.send("❌ Erro ao consultar os grupos do Roblox.", ephemeral=True)
                    return
                
                roles_data = await resp_role.json()
                cargo_grupo_nome = None
                for g in roles_data.get("data", []):
                    if g["group"]["id"] == ROBLOX_GROUP_ID:
                        cargo_grupo_nome = g["role"]["name"].strip()
                        break
    except Exception:
        await interaction.followup.send("❌ O tempo limite de ligação ao Roblox esgotou-se ou ocorreu um erro. Tenta novamente.", ephemeral=True)
        return

    if not cargo_grupo_nome:
        await interaction.followup.send(f"❌ A tua conta (**{roblox_display}**) não está no grupo oficial do Exército no Roblox.", ephemeral=True)
        return

    config_patente = PATENTES_CONFIG.get(cargo_grupo_nome)
    if not config_patente:
        await interaction.followup.send(f"⚠️ O teu cargo atual no Roblox (**{cargo_grupo_nome}**) não está mapeado nas patentes do bot.", ephemeral=True)
        return

    cat_nome = config_patente["categoria"]

    contas_verificadas[interaction.user.id] = {
        "id": roblox_user_id,
        "display": roblox_display,
        "name": roblox_name
    }

    membro = interaction.user
    cargo_novo = discord.utils.get(membro.guild.roles, name=cargo_grupo_nome)
    categoria_nova = discord.utils.get(membro.guild.roles, name=cat_nome)

    cargos_para_adicionar = []
    if cargo_novo and cargo_novo not in membro.roles:
        cargos_para_adicionar.append(cargo_novo)
    if categoria_nova and categoria_nova not in membro.roles:
        cargos_para_adicionar.append(categoria_nova)

    if cargos_para_adicionar:
        try:
            await membro.add_roles(*cargos_para_adicionar)
        except Exception:
            pass

    try:
        tag = config_patente["tag"]
        await membro.edit(nick=f"{tag} {roblox_display}"[:32])
    except Exception:
        pass

    embed = discord.Embed(
        title="✅ Verificação Concluída!",
        description="A tua conta foi verificada com sucesso e os teus cargos foram atribuídos.",
        color=discord.Color.green()
    )
    embed.add_field(name="👤 Roblox", value=f"{roblox_display} (`@{roblox_name}`)", inline=True)
    embed.add_field(name="🎖️ Patente", value=cargo_grupo_nome, inline=True)
    embed.add_field(name="📂 Categoria", value=cat_nome, inline=True)
    embed.set_footer(text="Exército Brasileiro do Shelby · Sistema de Verificação")

    await interaction.followup.send(embed=embed, ephemeral=True)


# --- 2. COMANDO: /sincronizar ---
@bot.tree.command(name="sincronizar", description="Atualiza os teus cargos do Discord caso tenhas sido promovido ou rebaixado no Roblox.")
async def sincronizar(interaction: discord.Interaction):
    membro = interaction.user

    if membro.id not in contas_verificadas:
        await interaction.response.send_message(
            "❌ Ainda não estás verificado! Usa primeiro o comando `/verificar` com o teu nome do Roblox.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    dados_roblox = contas_verificadas[membro.id]
    roblox_user_id = dados_roblox["id"]
    roblox_display = dados_roblox["display"]
    roblox_name = dados_roblox["name"]

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            url_role = f"https://groups.roblox.com/v1/users/{roblox_user_id}/groups/roles"
            async with session.get(url_role) as resp_role:
                if resp_role.status != 200:
                    await interaction.followup.send("❌ Erro ao consultar a API do Roblox. Tenta novamente mais tarde.", ephemeral=True)
                    return

                roles_data = await resp_role.json()
                cargo_grupo_nome = None

                for g in roles_data.get("data", []):
                    if g["group"]["id"] == ROBLOX_GROUP_ID:
                        cargo_grupo_nome = g["role"]["name"].strip()
                        break
    except Exception:
        await interaction.followup.send("❌ O tempo limite de ligação ao Roblox esgotou-se ou ocorreu um erro. Tenta novamente.", ephemeral=True)
        return

    if not cargo_grupo_nome:
        await interaction.followup.send(f"❌ Não encontramos a tua conta (**{roblox_display}**) no grupo oficial do Exército no Roblox.", ephemeral=True)
        return

    config_patente = PATENTES_CONFIG.get(cargo_grupo_nome)
    if not config_patente:
        await interaction.followup.send(f"⚠️ O teu cargo atual no Roblox (**{cargo_grupo_nome}**) não está mapeado nas patentes do bot.", ephemeral=True)
        return

    cat_nome_nova = config_patente["categoria"]
    patentes_lista = list(PATENTES_CONFIG.keys())
    cargos_para_remover = []

    for nome_patente in patentes_lista:
        if nome_patente != cargo_grupo_nome:
            cargo_antigo = discord.utils.get(interaction.guild.roles, name=nome_patente)
            if cargo_antigo and cargo_antigo in membro.roles:
                cargos_para_remover.append(cargo_antigo)

    categorias_todas = set(cfg["categoria"] for cfg in PATENTES_CONFIG.values())
    for cat_nome in categorias_todas:
        if cat_nome != cat_nome_nova:
            cat_antiga = discord.utils.get(interaction.guild.roles, name=cat_nome)
            if cat_antiga and cat_antiga in membro.roles:
                cargos_para_remover.append(cat_antiga)

    if cargos_para_remover:
        try:
            await membro.remove_roles(*cargos_para_remover)
        except Exception:
            pass

    cargo_novo = discord.utils.get(interaction.guild.roles, name=cargo_grupo_nome)
    categoria_nova = discord.utils.get(interaction.guild.roles, name=cat_nome_nova)

    cargos_para_adicionar = []
    if cargo_novo and cargo_novo not in membro.roles:
        cargos_para_adicionar.append(cargo_novo)
    if categoria_nova and categoria_nova not in membro.roles:
        cargos_para_adicionar.append(categoria_nova)

    if cargos_para_adicionar:
        try:
            await membro.add_roles(*cargos_para_adicionar)
        except Exception:
            pass

    try:
        tag = config_patente["tag"]
        await membro.edit(nick=f"{tag} {roblox_display}"[:32])
    except Exception:
        pass

    embed = discord.Embed(
        title="🔄 Sincronização Concluída!",
        description="Os teus cargos foram atualizados com base no teu rank atual no Roblox.",
        color=discord.Color.green()
    )
    embed.add_field(name="👤 Roblox", value=f"{roblox_display} (`@{roblox_name}`)", inline=True)
    embed.add_field(name="🎖️ Patente Atribuída", value=cargo_grupo_nome, inline=True)
    embed.add_field(name="📂 Categoria Atribuída", value=cat_nome_nova, inline=True)
    embed.set_footer(text="Exército Brasileiro · Sistema de Sincronização")
    
    await interaction.followup.send(embed=embed, ephemeral=True)

# --- 3. COMANDO: /promover ---
@bot.tree.command(name="promover", description="Promove um militar respeitando as permissões da hierarquia.")
async def promover(interaction: discord.Interaction, membro: discord.Member, cargo_patente: discord.Role):
    await interaction.response.defer()

    config_novo = PATENTES_CONFIG.get(cargo_patente.name)
    if not config_novo:
        await interaction.followup.send(f"❌ O cargo **{cargo_patente.name}** não está registrado na tabela de CDP.", ephemeral=True)
        return

    nivel_autor = verificar_nivel_autor(interaction.user)
    cat_destino = config_novo["categoria"]
    nivel_destino = HIERARQUIA_CATEGORIAS.get(cat_destino, 0)

    if nivel_autor <= 3:
        await interaction.followup.send("❌ **PROMOÇÃO NEGADA!** Praças, Graduados e Praças Especiais não têm permissão para promover.", ephemeral=True)
        return
    elif nivel_autor == 4 and nivel_destino > 1:
        await interaction.followup.send("❌ **PROMOÇÃO NEGADA!** Oficiais Subalternos só podem promover Praças.", ephemeral=True)
        return
    elif nivel_autor == 5 and nivel_destino > 3:
        await interaction.followup.send("❌ **PROMOÇÃO NEGADA!** Oficiais Intermediários só podem promover Praças, Graduados e Praças Especiais.", ephemeral=True)
        return
    elif nivel_autor == 6 and nivel_destino > 5:
        await interaction.followup.send("❌ **PROMOÇÃO NEGADA!** Oficiais Superiores não podem promover para Cargos Generais.", ephemeral=True)
        return

    agora = datetime.datetime.now()
    if membro.id in historico_cdp and agora < historico_cdp[membro.id]:
        restante = historico_cdp[membro.id] - agora
        horas = restante.seconds // 3600
        minutos = (restante.seconds % 3600) // 60
        await interaction.followup.send(f"❌ **PROMOÇÃO BLOQUEADA!** {membro.mention} ainda está em CDP. Faltam {horas}h {minutos}m.", ephemeral=True)
        return

    # Remove patentes antigas e categorias diferentes da nova
    categorias_todas = set(cfg["categoria"] for cfg in PATENTES_CONFIG.values())
    cargos_para_remover = [
        r for r in membro.roles
        if (r.name in PATENTES_CONFIG and r.name != cargo_patente.name)
        or (r.name in categorias_todas and r.name != cat_destino)
    ]

    cargo_categoria = discord.utils.get(interaction.guild.roles, name=cat_destino)
    cargos_para_adicionar = []
    if cargo_patente not in membro.roles:
        cargos_para_adicionar.append(cargo_patente)
    if cargo_categoria and cargo_categoria not in membro.roles:
        cargos_para_adicionar.append(cargo_categoria)

    try:
        if cargos_para_remover:
            await membro.remove_roles(*cargos_para_remover)
        if cargos_para_adicionar:
            await membro.add_roles(*cargos_para_adicionar)
        tag = config_novo["tag"]
        nome_limpo = membro.display_name.split("]")[-1].strip()
        await membro.edit(nick=f"{tag} {nome_limpo}"[:32])
    except Exception as e:
        await interaction.followup.send(f"❌ Erro ao aplicar cargos ou apelido: {e}", ephemeral=True)
        return

    horas_cdp = config_novo["horas"]
    data_liberacao = agora + datetime.timedelta(hours=horas_cdp)
    historico_cdp[membro.id] = data_liberacao

    embed = discord.Embed(title="🛡️ Promoção Realizada com Sucesso!", description=f"O militar {membro.mention} foi promovido!", color=discord.Color.green())
    embed.add_field(name="📜 Cargos Atribuídos", value=f"{cargo_patente.mention}\n{cargo_categoria.mention if cargo_categoria else ''}", inline=False)
    embed.add_field(name="⏳ Duração do CDP", value=f"{horas_cdp} Horas", inline=True)
    embed.add_field(name="📅 Próxima Promoção", value=data_liberacao.strftime("%d/%m/%Y às %H:%M"), inline=True)
    embed.set_footer(text=f"Promovido por: {interaction.user.display_name}")

    await interaction.followup.send(embed=embed)


# --- 4. COMANDO: /promover_varios ---
@bot.tree.command(name="promover_varios", description="Promove vários militares de uma vez (mencione-os).")
async def promover_varios(interaction: discord.Interaction, mencoes: str, cargo_patente: discord.Role):
    await interaction.response.defer()

    config_novo = PATENTES_CONFIG.get(cargo_patente.name)
    if not config_novo:
        await interaction.followup.send(f"❌ O cargo **{cargo_patente.name}** não está registrado na tabela de CDP.", ephemeral=True)
        return

    nivel_autor = verificar_nivel_autor(interaction.user)
    cat_destino = config_novo["categoria"]
    nivel_destino = HIERARQUIA_CATEGORIAS.get(cat_destino, 0)

    if nivel_autor <= 3:
        await interaction.followup.send("❌ **PROMOÇÃO NEGADA!** Não tens permissão para promover.", ephemeral=True)
        return
    elif nivel_autor == 4 and nivel_destino > 1:
        await interaction.followup.send("❌ **PROMOÇÃO NEGADA!** Oficiais Subalternos só podem promover Praças.", ephemeral=True)
        return
    elif nivel_autor == 5 and nivel_destino > 3:
        await interaction.followup.send("❌ **PROMOÇÃO NEGADA!** Oficiais Intermediários só podem promover até Praças Especiais.", ephemeral=True)
        return
    elif nivel_autor == 6 and nivel_destino > 5:
        await interaction.followup.send("❌ **PROMOÇÃO NEGADA!** Oficiais Superiores não podem promover para Oficiais Generais.", ephemeral=True)
        return

    ids_membros = re.findall(r'<@!?(\d+)>', mencoes)
    if not ids_membros:
        await interaction.followup.send("❌ Nenhum militar válido foi mencionado.", ephemeral=True)
        return

    agora = datetime.datetime.now()
    sucessos, erros = [], []
    cargo_categoria = discord.utils.get(interaction.guild.roles, name=cat_destino)
    horas_cdp = config_novo["horas"]
    categorias_todas = set(cfg["categoria"] for cfg in PATENTES_CONFIG.values())

    for uid in ids_membros:
        membro = interaction.guild.get_member(int(uid))
        if not membro:
            continue
        if membro.id in historico_cdp and agora < historico_cdp[membro.id]:
            erros.append(f"{membro.mention} (Em CDP)")
            continue

        try:
            cargos_para_remover = [
                r for r in membro.roles
                if (r.name in PATENTES_CONFIG and r.name != cargo_patente.name)
                or (r.name in categorias_todas and r.name != cat_destino)
            ]
            if cargos_para_remover:
                await membro.remove_roles(*cargos_para_remover)

            cargos_add = []
            if cargo_patente not in membro.roles:
                cargos_add.append(cargo_patente)
            if cargo_categoria and cargo_categoria not in membro.roles:
                cargos_add.append(cargo_categoria)
            if cargos_add:
                await membro.add_roles(*cargos_add)

            tag = config_novo["tag"]
            nome_limpo = membro.display_name.split("]")[-1].strip()
            await membro.edit(nick=f"{tag} {nome_limpo}"[:32])

            historico_cdp[membro.id] = agora + datetime.timedelta(hours=horas_cdp)
            sucessos.append(membro.mention)
        except Exception:
            erros.append(membro.mention)

    embed = discord.Embed(title="🏆 Promoção em Massa Realizada", color=discord.Color.green())
    if sucessos:
        embed.add_field(name="✅ Promovidos com Sucesso", value=", ".join(sucessos), inline=False)
    if erros:
        embed.add_field(name="❌ Falhas / Em CDP", value=", ".join(erros), inline=False)
    embed.set_footer(text=f"Ação executada por {interaction.user.display_name}")

    await interaction.followup.send(embed=embed)


# --- 5. COMANDO: /rebaixar ---
@bot.tree.command(name="rebaixar", description="Rebaixa um militar, atualiza os cargos, apelido e reseta o CDP.")
async def rebaixar(interaction: discord.Interaction, membro: discord.Member, cargo_patente_nova: discord.Role):
    await interaction.response.defer()

    nivel_autor = 0
    for role in interaction.user.roles:
        if role.name in CARGOS_REBAIXAR_PERMISSAO:
            nivel_autor = max(nivel_autor, CARGOS_REBAIXAR_PERMISSAO[role.name])

    if nivel_autor == 0:
        await interaction.followup.send("❌ **REBAIXAMENTO NEGADO!** Apenas membros autorizados podem rebaixar.", ephemeral=True)
        return

    config_nova = PATENTES_CONFIG.get(cargo_patente_nova.name)
    if not config_nova:
        await interaction.followup.send(f"❌ O cargo **{cargo_patente_nova.name}** não está registrado na tabela.", ephemeral=True)
        return

    patentes_lista = list(PATENTES_CONFIG.keys())
    indice_atual = -1
    for i, nome_patente in enumerate(patentes_lista):
        cargo = discord.utils.get(interaction.guild.roles, name=nome_patente)
        if cargo and cargo in membro.roles:
            indice_atual = i
            break

    indice_novo = patentes_lista.index(cargo_patente_nova.name) if cargo_patente_nova.name in patentes_lista else -1

    if indice_atual != -1 and indice_novo >= indice_atual:
        await interaction.followup.send(f"❌ **REBAIXAMENTO NEGADO!** O cargo {cargo_patente_nova.mention} é igual ou superior à patente atual do militar.", ephemeral=True)
        return

    try:
        cat_nova_nome = config_nova["categoria"]
        categorias_todas = set(cfg["categoria"] for cfg in PATENTES_CONFIG.values())

        # Remove patentes antigas e categorias diferentes da nova
        cargos_para_remover = [
            r for r in membro.roles
            if (r.name in PATENTES_CONFIG and r.name != cargo_patente_nova.name)
            or (r.name in categorias_todas and r.name != cat_nova_nome)
        ]
        if cargos_para_remover:
            await membro.remove_roles(*cargos_para_remover)

        cargos_adicionar = []
        if cargo_patente_nova not in membro.roles:
            cargos_adicionar.append(cargo_patente_nova)
        cargo_cat_nova = discord.utils.get(interaction.guild.roles, name=cat_nova_nome)
        if cargo_cat_nova and cargo_cat_nova not in membro.roles:
            cargos_adicionar.append(cargo_cat_nova)

        if cargos_adicionar:
            await membro.add_roles(*cargos_adicionar)

        tag = config_nova["tag"]
        nome_limpo = membro.display_name.split("]")[-1].strip()
        await membro.edit(nick=f"{tag} {nome_limpo}"[:32])

        horas_cdp = config_nova["horas"]
        historico_cdp[membro.id] = datetime.datetime.now() + datetime.timedelta(hours=horas_cdp)

        embed = discord.Embed(title="⚠️ Rebaixamento Realizado", description=f"O militar {membro.mention} foi rebaixado para **{cargo_patente_nova.name}**.", color=discord.Color.orange())
        embed.set_footer(text=f"Rebaixado por {interaction.user.display_name}")

        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Ocorreu um erro ao rebaixar: {e}", ephemeral=True)


# --- 6. COMANDO: /rebaixar_varios ---
@bot.tree.command(name="rebaixar_varios", description="Rebaixa vários militares de uma vez (mencione-os).")
async def rebaixar_varios(interaction: discord.Interaction, mencoes: str, cargo_patente_nova: discord.Role):
    await interaction.response.defer()

    nivel_autor = 0
    for role in interaction.user.roles:
        if role.name in CARGOS_REBAIXAR_PERMISSAO:
            nivel_autor = max(nivel_autor, CARGOS_REBAIXAR_PERMISSAO[role.name])

    if nivel_autor == 0:
        await interaction.followup.send("❌ **REBAIXAMENTO NEGADO!** Apenas membros autorizados podem rebaixar.", ephemeral=True)
        return

    config_nova = PATENTES_CONFIG.get(cargo_patente_nova.name)
    if not config_nova:
        await interaction.followup.send(f"❌ O cargo **{cargo_patente_nova.name}** não está registrado na tabela.", ephemeral=True)
        return

    ids_membros = re.findall(r'<@!?(\d+)>', mencoes)
    if not ids_membros:
        await interaction.followup.send("❌ Nenhum militar válido foi mencionado.", ephemeral=True)
        return

    sucessos, erros = [], []
    cat_nova_nome = config_nova["categoria"]
    cargo_cat_nova = discord.utils.get(interaction.guild.roles, name=cat_nova_nome)
    horas_cdp = config_nova["horas"]
    patentes_lista = list(PATENTES_CONFIG.keys())
    categorias_todas = set(cfg["categoria"] for cfg in PATENTES_CONFIG.values())
    indice_novo = patentes_lista.index(cargo_patente_nova.name) if cargo_patente_nova.name in patentes_lista else -1
    agora = datetime.datetime.now()

    for uid in ids_membros:
        membro = interaction.guild.get_member(int(uid))
        if not membro:
            continue

        indice_atual = -1
        for i, nome_patente in enumerate(patentes_lista):
            cargo = discord.utils.get(interaction.guild.roles, name=nome_patente)
            if cargo and cargo in membro.roles:
                indice_atual = i
                break

        if indice_atual != -1 and indice_novo >= indice_atual:
            erros.append(f"{membro.mention} (Patente igual/inferior à selecionada)")
            continue

        try:
            cargos_para_remover = [
                r for r in membro.roles
                if (r.name in PATENTES_CONFIG and r.name != cargo_patente_nova.name)
                or (r.name in categorias_todas and r.name != cat_nova_nome)
            ]
            if cargos_para_remover:
                await membro.remove_roles(*cargos_para_remover)

            cargos_adicionar = []
            if cargo_patente_nova not in membro.roles:
                cargos_adicionar.append(cargo_patente_nova)
            if cargo_cat_nova and cargo_cat_nova not in membro.roles:
                cargos_adicionar.append(cargo_cat_nova)

            if cargos_adicionar:
                await membro.add_roles(*cargos_adicionar)

            tag = config_nova["tag"]
            nome_limpo = membro.display_name.split("]")[-1].strip()
            await membro.edit(nick=f"{tag} {nome_limpo}"[:32])

            historico_cdp[membro.id] = agora + datetime.timedelta(hours=horas_cdp)
            sucessos.append(membro.mention)
        except Exception:
            erros.append(membro.mention)

    embed = discord.Embed(title="⚠️ Rebaixamento em Massa Realizado", color=discord.Color.orange())
    if sucessos:
        embed.add_field(name="✅ Rebaixados com Sucesso", value=", ".join(sucessos), inline=False)
    if erros:
        embed.add_field(name="❌ Falhas / Inválidos", value=", ".join(erros), inline=False)
    embed.set_footer(text=f"Ação executada por {interaction.user.display_name}")

    await interaction.followup.send(embed=embed)
        

# --- 7. COMANDO: /cdp ---
@bot.tree.command(name="cdp", description="Consulta o tempo restante de CDP de um militar.")
async def cdp(interaction: discord.Interaction, membro: discord.Member = None):
    membro = membro or interaction.user
    agora = datetime.datetime.now()

    if membro.id in historico_cdp and agora < historico_cdp[membro.id]:
        liberacao = historico_cdp[membro.id]
        restante = liberacao - agora
        horas = restante.seconds // 3600
        minutos = (restante.seconds % 3600) // 60

        embed = discord.Embed(title="⏳ Status de CDP", color=discord.Color.blue())
        embed.add_field(name="Militar", value=membro.mention, inline=False)
        embed.add_field(name="Tempo Restante", value=f"**{restante.days}d {horas}h {minutos}m**", inline=True)
        embed.add_field(name="Liberação", value=liberacao.strftime('%d/%m/%Y às %H:%M'), inline=True)
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(
            title="✅ Status de CDP",
            description=f"{membro.mention} **está livre para promoção!** Nenhuma CDP ativa no momento.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)


# --- 8. COMANDO: /hierarquia ---
@bot.tree.command(name="hierarquia", description="Exibe a tabela de patentes e seus tempos de CDP.")
async def hierarquia(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎖️ Hierarquia e Tempos de CDP",
        description="Confira abaixo as patentes e a duração de CDP de cada categoria (do topo para a base):",
        color=discord.Color.gold()
    )

    embed.add_field(
        name="⚔️ Oficiais Generais",
        value="`[GEN-EX]` General de Exército – 85 horas\n`[GEN-DV]` General de Divisão – 80 horas\n`[GEN-BDA]` General de Brigada – 75 horas",
        inline=False
    )
    embed.add_field(
        name="🏅 Oficiais Superiores",
        value="`[CEL]` Coronel – 70 horas\n`[TEN-CEL]` Tenente-Coronel – 65 horas\n`[MJ]` Major – 60 horas",
        inline=False
    )
    embed.add_field(
        name="⭐️ Oficiais Intermediários",
        value="`[CAP]` Capitão – 55 horas",
        inline=False
    )
    embed.add_field(
        name="🗡️ Oficiais Subalternos",
        value="`[P-TEN]` Primeiro-Tenente – 50 horas\n`[S-TEN]` Segundo-Tenente – 45 horas\n`[AAO]` Aspirante a Oficial – 40 horas",
        inline=False
    )
    embed.add_field(
        name="🪖 Praças Especiais",
        value="`[CDT]` Cadete – 35 horas",
        inline=False
    )
    embed.add_field(
        name="🎓 Militares Graduados",
        value="`[ST]` Subtenente – 30 horas\n`[P-SGT]` Primeiro-Sargento – 25 horas\n`[S-SGT]` Segundo-Sargento – 20 horas\n`[3 SGT]` Terceiro-Sargento – 15 horas",
        inline=False
    )
    embed.add_field(
        name="🌾 Militares Praças",
        value="`[CB]` Cabo – 12 horas\n`[SLD]` Soldado – 6 horas\n`[REC]` Recruta – 3 horas",
        inline=False
    )

    embed.set_footer(text="Exército Brasileiro do Shelby • Sistema de Gestão")
    await interaction.response.send_message(embed=embed)


# --- 9. COMANDO: /regras ---
@bot.tree.command(name="regras", description="Exibe o manual oficial de regras e diretrizes do exército.")
async def regras(interaction: discord.Interaction):
    embed_principal = discord.Embed(
        title="📜 MANUAL DE DIRETRIZES E REGRAS - EXÉRCITO",
        description="O cumprimento rigoroso destas normas é obrigatório para todos os militares. A ignorância das regras não exime o infrator de punição.",
        color=discord.Color.dark_red()
    )

    embed_principal.add_field(
        name="🛡️ 1. Conduta e Respeito Geral",
        value=(
            "• **1.1** Respeite todos os membros, independente de patente ou cargo.\n"
            "• **1.2** É estritamente proibido qualquer tipo de ofensa, preconceito, racismo ou toxicidade.\n"
            "• **1.3** Mantenha um ambiente saudável e focado na disciplina militar."
        ),
        inline=False
    )

    embed_principal.add_field(
        name="⭐ 2. Hierarquia e Disciplina",
        value=(
            "• **2.1** Ordens de superiores devem ser cumpridas prontamente, dentro do bom senso.\n"
            "• **2.2** O desrespeito à cadeia de comando resultará em punição severa ou rebaixamento.\n"
            "• **2.3** Pedidos de promoção devem seguir os critérios oficiais e prazos de CDP."
        ),
        inline=False
    )

    embed_principal.add_field(
        name="🎯 3. Treinamentos e Eventos",
        value=(
            "• **3.1** Respeite os instrutores durante os treinamentos.\n"
            "• **3.2** Não interrompa instruções sem necessidade.\n"
            "• **3.3** Compareça aos eventos após confirmar presença e avise a liderança se não puder.\n"
            "• **3.4** É proibido atrapalhar intencionalmente as atividades."
        ),
        inline=False
    )

    embed_principal.add_field(
        name="💬 4. Regras de Canais e Voz",
        value=(
            "• **4.1** Utilize cada canal estritamente para a sua devida finalidade.\n"
            "• **4.2** Evite gritos ou barulhos excessivos nos canais de voz.\n"
            "• **4.3** Não envie mensagens repetidas (flood) nem marque cargos/membros sem necessidade.\n"
            "• **4.4** Proibido enviar links suspeitos ou fazer divulgação não autorizada."
        ),
        inline=False
    )

    embed_principal.set_footer(text="Exército Brasileiro • Sistema Oficial de Normas e Conduta")
    await interaction.response.send_message(embed=embed_principal)

# --- 10. COMANDO: /dicas_gramaticais ---
@bot.tree.command(name="dicas_gramaticais", description="Exibe um guia completo e organizado de dicas gramaticais e ortografia.")
async def dicas_gramaticais(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📚 GUIA DE PORTUGUÊS E DIRETRIZES GRAMATICAIS",
        description="Aprimora a tua comunicação diária com estas dicas essenciais de ortografia, concordância e gramática:",
        color=discord.Color.teal()
    )

    embed.add_field(
        name="✍️ 1. Erros Comuns do Dia a Dia",
        value=(
            "• **A gente vs. Agente:** \"A gente\" (separado) significa *nós*. \"Agente\" (junto) é uma profissão.\n"
            "• **Mas vs. Mais:** \"Mas\" indica oposição (porém). \"Mais\" indica quantidade ou adição (+).\n"
            "• **Mal vs. Mau:** \"Mal\" é o oposto de *bem*. \"Mau\" é o oposto de *bom*."
        ),
        inline=False
    )

    embed.add_field(
        name="🔍 2. Emprego dos Porquês",
        value=(
            "• **Por que:** Usado em perguntas (no início) ou sentido de *por qual razão*.\n"
            "• **Porque:** Usado em respostas e justificativas.\n"
            "• **Por quê:** Usado isolado no final de frases.\n"
            "• **O porquê:** Substantivo que significa *o motivo*, precedido de artigo."
        ),
        inline=False
    )

    embed.set_footer(text="Exército Brasileiro • Canal de Apoio Educativo e Gramatical")
    await interaction.response.send_message(embed=embed)


# --- 11. COMANDO: /informacoes ---
@bot.tree.command(name="informacoes", description="Exibe informações gerais sobre o Exército Brasileiro do Shelby no Roblox.")
async def informacoes(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🇧🇷 EXÉRCITO BRASILEIRO DO SHELBY • INFORMAÇÕES",
        description="Bem-vindo ao quartel-general oficial! Descobre mais sobre a nossa instituição e diretrizes no Roblox:",
        color=discord.Color.gold()
    )

    embed.add_field(
        name="🎮 1. Sobre a Instituição (Roblox)",
        value="O nosso exército é um projeto estruturado para proporcionar uma experiência imersiva, realista e disciplinada.",
        inline=False
    )
    embed.add_field(
        name="🎖️ 2. Hierarquia e Progressão",
        value="A nossa estrutura divide-se em 7 categorias. Respeitamos rigorosamente os tempos de CDP.",
        inline=False
    )

    embed.set_footer(text="Exército Brasileiro do Shelby • Roblox Simulation")
    await interaction.response.send_message(embed=embed)


# --- CLASSE PARA OS BOTÕES DO PAINEL ---
class PainelVerificacaoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Timeout None para os botões nunca expirarem

    # Botão 1: Sincronizar (Executa a lógica de sincronização)
    @discord.ui.button(label="Sincronizar agora", style=discord.ButtonStyle.green, emoji="🔄", custom_id="btn_sincronizar")
    async def btn_sincronizar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Aqui podes chamar diretamente a lógica do sincronizar ou avisar o user
        await interaction.response.send_message("🔄 A processar a tua sincronização...", ephemeral=True)
        # (Opcional: podes invocar a lógica do comando /sincronizar aqui se quiseres)

    # Botão 2: Vincular Conta (Link externo)
    @discord.ui.button(label="Vincular conta", style=discord.ButtonStyle.blurple, emoji="🔗", custom_id="btn_vincular")
    async def btn_vincular(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔗 Para vincular, utiliza o comando `/verificar [teu_nick_roblox]` aqui no Discord!", ephemeral=True)

    # Botão 3: Problema? (Botão de suporte)
    @discord.ui.button(label="Problema?", style=discord.ButtonStyle.red, emoji="⚠️", custom_id="btn_problema")
    async def btn_problema(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("⚠️ Se tens algum problema com a verificação, entra em contacto com a Administração ou abre um ticket.", ephemeral=True)


# --- COMANDO PARA ENVIAR O PAINEL ---
@bot.tree.command(name="painel_verificacao", description="Envia o painel oficial de verificação para o canal (Apenas Administração).")
@app_commands.checks.has_permissions(administrator=True)
async def painel_verificacao(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🪖 Verificação • Exército Brasileiro do Shelby",
        description=(
            "Vincula a tua conta do Roblox ao Discord pra receber "
            "automaticamente os cargos do seu rank (Exército, divisões, administração).\n\n"
            "🔄 **Já vinculou?** Clique em **Sincronizar agora** pra atualizar seus cargos com base no rank atual.\n\n"
            "🔗 **Primeira vez?** Utilize o comando `/verificar [seu_usuario_roblox]` para registrar a sua conta."
        ),
        color=discord.Color.dark_theme()
    )
    embed.set_footer(text="Exército Brasileiro do Shelby · Sincronização automática")

    # Envia a mensagem com os botões incorporados
    await interaction.channel.send(embed=embed, view=PainelVerificacaoView())
    await interaction.response.send_message("✅ Painel de verificação enviado com sucesso!", ephemeral=True)
    



# --- SERVIDOR WEB DUMMY PARA O RENDER (KEEP ALIVE) ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive and running!")
    def log_message(self, format, *args):
        pass

def run_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_web, daemon=True).start()

# --- INICIALIZAÇÃO DO BOT ---
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ ERRO: A variável de ambiente 'DISCORD_TOKEN não foi encontrada!")
