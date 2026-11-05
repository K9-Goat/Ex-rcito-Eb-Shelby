import discord
from discord.ext import commands
import datetime
import os
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- CONFIGURAÇÕES DE HIERARQUIA E PATENTES ---
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
    "[3 SGT] Terceiro-Sargento": {"horas": 15, "tag": "[3 SGT]", "categoria": "〘🎓〙 Militares Graduados"},
    "[2 SGT] Segundo-Sargento": {"horas": 20, "tag": "[2 SGT]", "categoria": "〘🎓〙 Militares Graduados"},
    "[1 SGT] Primeiro-Sargento": {"horas": 25, "tag": "[1 SGT]", "categoria": "〘🎓〙 Militares Graduados"},
    "[ST] Subtenente": {"horas": 30, "tag": "[ST]", "categoria": "〘🎓〙 Militares Graduados"},

    # Praças Especiais
    "[CDT] Cadete": {"horas": 35, "tag": "[CDT]", "categoria": "〘🪖〙 Praças Especiais"},

    # Oficiais Subalternos
    "[AAO] Aspirante a Oficial": {"horas": 40, "tag": "[AAO]", "categoria": "〘🗡️〙Oficiais Subalternos"},
    "[2 TEN] Segundo-Tenente": {"horas": 45, "tag": "[2 TEN]", "categoria": "〘🗡️〙Oficiais Subalternos"},
    "[1 TEN] Primeiro-Tenente": {"horas": 50, "tag": "[1 TEN]", "categoria": "〘🗡️〙Oficiais Subalternos"},

    # Oficiais Intermediários
    "[CAP] Capitão": {"horas": 55, "tag": "[CAP]", "categoria": "〘⭐️〙Oficiais Intermediário"},

    # Oficiais Superiores
    "[MAJ] Major": {"horas": 60, "tag": "[MAJ]", "categoria": "〘🏅〙Oficiais Superiores"},
    "[TEN-CEL] Tenente-Coronel": {"horas": 65, "tag": "[TEN-CEL]", "categoria": "〘🏅〙Oficiais Superiores"},
    "[COR] Coronel": {"horas": 70, "tag": "[COR]", "categoria": "〘🏅〙Oficiais Superiores"},

    # Oficiais Generais
    "[GEN-BDA] General de Brigada": {"horas": 75, "tag": "[GEN BDA]", "categoria": "〘⚔️〙Oficiais Generais"},
    "[GEN-DV] General de Divisão": {"horas": 80, "tag": "[GEN DV]", "categoria": "〘⚔️〙Oficiais Generais"},
    "[GEN-EX] General de Exército": {"horas": 85, "tag": "[GEN EX]", "categoria": "〘⚔️〙Oficiais Generais"},
}

historico_cdp = {}

@bot.event
async def on_ready():
    # Limpa comandos antigos duplicados globalmente antes de sincronizar
    bot.tree.clear_commands(guild=None)
    await bot.tree.sync()
    print(f"Bot online e sincronizado limpidamente como {bot.user}")

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


# --- 1. COMANDO: /promover ---
@bot.tree.command(name="promover", description="Promove um militar respeitando as permissões da hierarquia.")
async def promover(interaction: discord.Interaction, membro: discord.Member, cargo_patente: discord.Role):
    await interaction.response.defer()

    config_novo = PATENTES_CONFIG.get(cargo_patente.name)
    if not config_novo:
        await interaction.followup.send(f"❌ O cargo **{cargo_patente.name}** não está registrado na tabela de CDP.")
        return

    nivel_autor = verificar_nivel_autor(interaction.user)
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

    agora = datetime.datetime.now()
    if membro.id in historico_cdp and agora < historico_cdp[membro.id]:
        restante = historico_cdp[membro.id] - agora
        horas = restante.seconds // 3600
        minutos = (restante.seconds % 3600) // 60
        await interaction.followup.send(f"❌ **PROMOÇÃO BLOQUEADA!** {membro.mention} ainda está em CDP. Falta(m) **{restante.days}d {horas}h {minutos}m**.")
        return

    cargo_categoria = discord.utils.get(interaction.guild.roles, name=cat_destino)
    cargos_para_adicionar = [cargo_patente]
    if cargo_categoria:
        cargos_para_adicionar.append(cargo_categoria)

    await membro.add_roles(*cargos_para_adicionar)

    tag = config_novo["tag"]
    nome_limpo = membro.display_name.split("]")[-1].strip()
    try:
        await membro.edit(nick=f"{tag} {nome_limpo}"[:32])
    except Exception:
        pass

    horas_cdp = config_novo["horas"]
    data_liberacao = agora + datetime.timedelta(hours=horas_cdp)
    historico_cdp[membro.id] = data_liberacao

    embed = discord.Embed(title="🏆 Promoção Realizada com Sucesso!", description=f"O militar {membro.mention} foi promovido a **{cargo_patente.name}**!", color=discord.Color.green())
    embed.add_field(name="📌 Cargos Atribuídos", value=f"{cargo_patente.mention}\n{cargo_categoria.mention if cargo_categoria else cat_destino}", inline=False)
    embed.add_field(name="⏳ Duração da CDP", value=f"{horas_cdp} Horas", inline=True)
    embed.add_field(name="🕒 Próxima Promoção", value=data_liberacao.strftime('%d/%m/%Y às %H:%M'), inline=True)
    embed.set_footer(text=f"Promovido por {interaction.user.display_name}")

    await interaction.followup.send(embed=embed)


# --- 2. COMANDO: /promover_varios ---
@bot.tree.command(name="promover_varios", description="Promove vários militares de uma vez só (mencione-os).")
async def promover_varios(interaction: discord.Interaction, mencoes: str, cargo_patente: discord.Role):
    await interaction.response.defer()

    config_novo = PATENTES_CONFIG.get(cargo_patente.name)
    if not config_novo:
        await interaction.followup.send(f"❌ O cargo **{cargo_patente.name}** não está registrado na tabela de CDP.")
        return

    nivel_autor = verificar_nivel_autor(interaction.user)
    cat_destino = config_novo["categoria"]
    nivel_destino = HIERARQUIA_CATEGORIAS.get(cat_destino, 0)

    if nivel_autor <= 3:
        await interaction.followup.send("❌ **PROMOÇÃO NEGADA!** Não tens permissão para promover.")
        return
    elif nivel_autor == 4 and nivel_destino > 1:
        await interaction.followup.send("❌ **PROMOÇÃO NEGADA!** Oficiais Subalternos só podem promover Praças.")
        return
    elif nivel_autor == 5 and nivel_destino > 3:
        await interaction.followup.send("❌ **PROMOÇÃO NEGADA!** Oficiais Intermediários só podem promover até Praças Especiais.")
        return
    elif nivel_autor == 6 and nivel_destino > 5:
        await interaction.followup.send("❌ **PROMOÇÃO NEGADA!** Oficiais Superiores não podem promover para Oficiais Superiores/Generais.")
        return

    ids_membros = re.findall(r'<@!?(\d+)>', mencoes)
    if not ids_membros:
        await interaction.followup.send("❌ Nenhum militar válido foi mencionado.")
        return

    agora = datetime.datetime.now()
    sucessos, erros = [], []
    cargo_categoria = discord.utils.get(interaction.guild.roles, name=cat_destino)
    horas_cdp = config_novo["horas"]

    for uid in ids_membros:
        membro = interaction.guild.get_member(int(uid))
        if not membro:
            continue
        if membro.id in historico_cdp and agora < historico_cdp[membro.id]:
            erros.append(f"{membro.mention} (Em CDP)")
            continue

        try:
            cargos_add = [cargo_patente]
            if cargo_categoria:
                cargos_add.append(cargo_categoria)
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


# --- 3. COMANDO: /rebaixar ---
@bot.tree.command(name="rebaixar", description="Rebaixa um militar, atualiza os cargos, apelido e reseta a CDP.")
async def rebaixar(interaction: discord.Interaction, membro: discord.Member, cargo_patente_nova: discord.Role):
    await interaction.response.defer()

    nivel_autor = 0
    for role in interaction.user.roles:
        if role.name in CARGOS_REBAIXAR_PERMISSAO:
            nivel_autor = max(nivel_autor, CARGOS_REBAIXAR_PERMISSAO[role.name])

    if nivel_autor == 0:
        await interaction.followup.send("❌ **REBAIXAMENTO NEGADO!** Apenas membros autorizados podem rebaixar.")
        return

    config_nova = PATENTES_CONFIG.get(cargo_patente_nova.name)
    if not config_nova:
        await interaction.followup.send(f"❌ O cargo **{cargo_patente_nova.name}** não está registrado na tabela.")
        return

    cargo_patente_antigo, cargo_categoria_antigo, config_antiga = None, None, None
    for nome_p, cfg in PATENTES_CONFIG.items():
        if cfg["tag"] in membro.display_name:
            config_antiga = cfg
            cargo_patente_antigo = discord.utils.get(interaction.guild.roles, name=nome_p)
            if cfg["categoria"]:
                cargo_categoria_antigo = discord.utils.get(interaction.guild.roles, name=cfg["categoria"])
            break

    nome_cat_nova = config_nova["categoria"]
    cargo_cat_nova = discord.utils.get(interaction.guild.roles, name=nome_cat_nova)

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
    if cargo_cat_nova:
        cargos_adicionar.append(cargo_cat_nova)

    await membro.add_roles(*cargos_adicionar)

    tag = config_nova["tag"]
    nome_limpo = membro.display_name.split("]")[-1].strip()
    try:
        await membro.edit(nick=f"{tag} {nome_limpo}"[:32])
    except Exception:
        pass

    agora = datetime.datetime.now()
    horas_cdp = config_nova["horas"]
    historico_cdp[membro.id] = agora + datetime.timedelta(hours=horas_cdp)

    embed = discord.Embed(title="⚠️ Rebaixamento Realizado", description=f"O militar {membro.mention} foi rebaixado para **{cargo_patente_nova.name}**.", color=discord.Color.orange())
    embed.add_field(name="📌 Novo Cargo", value=cargo_patente_nova.mention, inline=False)
    embed.set_footer(text=f"Rebaixado por {interaction.user.display_name}")

    await interaction.followup.send(embed=embed)


# --- 4. COMANDO: /rebaixar_varios ---
@bot.tree.command(name="rebaixar_varios", description="Rebaixa vários militares de uma vez só (mencione-os).")
async def rebaixar_varios(interaction: discord.Interaction, mencoes: str, cargo_patente_nova: discord.Role):
    await interaction.response.defer()

    nivel_autor = 0
    for role in interaction.user.roles:
        if role.name in CARGOS_REBAIXAR_PERMISSAO:
            nivel_autor = max(nivel_autor, CARGOS_REBAIXAR_PERMISSAO[role.name])

    if nivel_autor == 0:
        await interaction.followup.send("❌ **REBAIXAMENTO NEGADO!** Apenas membros autorizados podem rebaixar.")
        return

    config_nova = PATENTES_CONFIG.get(cargo_patente_nova.name)
    if not config_nova:
        await interaction.followup.send(f"❌ O cargo **{cargo_patente_nova.name}** não está registrado na tabela.")
        return

    ids_membros = re.findall(r'<@!?(\d+)>', mencoes)
    if not ids_membros:
        await interaction.followup.send("❌ Nenhum militar válido foi mencionado.")
        return

    sucessos = []
    agora = datetime.datetime.now()
    nome_cat_nova = config_nova["categoria"]
    cargo_cat_nova = discord.utils.get(interaction.guild.roles, name=nome_cat_nova)
    horas_cdp = config_nova["horas"]

    for uid in ids_membros:
        membro = interaction.guild.get_member(int(uid))
        if not membro:
            continue

        cargo_patente_antigo, cargo_categoria_antigo, config_antiga = None, None, None
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

        try:
            if cargos_remover:
                await membro.remove_roles(*cargos_remover)
            
            cargos_adicionar = [cargo_patente_nova]
            if cargo_cat_nova:
                cargos_adicionar.append(cargo_cat_nova)
            await membro.add_roles(*cargos_adicionar)

            tag = config_nova["tag"]
            nome_limpo = membro.display_name.split("]")[-1].strip()
            await membro.edit(nick=f"{tag} {nome_limpo}"[:32])

            historico_cdp[membro.id] = agora + datetime.timedelta(hours=horas_cdp)
            sucessos.append(membro.mention)
        except Exception:
            pass

    embed = discord.Embed(title="⚠️ Rebaixamento em Massa Realizado", color=discord.Color.orange())
    if sucessos:
        embed.add_field(name="✅ Rebaixados com Sucesso", value=", ".join(sucessos), inline=False)
    embed.set_footer(text=f"Ação executada por {interaction.user.display_name}")

    await interaction.followup.send(embed=embed)


# --- 5. COMANDO: /cdp ---
@bot.tree.command(name="cdp", description="Consulta o tempo restante de CDP de um militar.")
async def cdp(interaction: discord.Interaction, membro: discord.Member = None):
    await interaction.response.defer()
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
        await interaction.followup.send(embed=embed)
    else:
        embed = discord.Embed(
            title="✅ Status de CDP",
            description=f"{membro.mention} **está livre para promoção!** Nenhuma CDP ativa no momento.",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed)


# --- 6. COMANDO: /hierarquia (Ordem correta: Generais em cima, Praças em baixo) ---
@bot.tree.command(name="hierarquia", description="Exibe a tabela de patentes e seus tempos de CDP.")
async def hierarquia(interaction: discord.Interaction):
    await interaction.response.defer()

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
        value="`[COR]` Coronel – 70 horas\n`[TEN-CEL]` Tenente-Coronel – 65 horas\n`[MAJ]` Major – 60 horas",
        inline=False
    )
    embed.add_field(
        name="⭐️ Oficiais Intermediários",
        value="`[CAP]` Capitão – 55 horas",
        inline=False
    )
    embed.add_field(
        name="🗡️ Oficiais Subalternos",
        value="`[1 TEN]` Primeiro-Tenente – 50 horas\n`[2 TEN]` Segundo-Tenente – 45 horas\n`[AAO]` Aspirante a Oficial – 40 horas",
        inline=False
    )
    embed.add_field(
        name="🪖 Praças Especiais",
        value="`[CDT]` Cadete – 35 horas",
        inline=False
    )
    embed.add_field(
        name="🎓 Militares Graduados",
        value="`[ST]` Subtenente – 30 horas\n`[1 SGT]` Primeiro-Sargento – 25 horas\n`[2 SGT]` Segundo-Sargento – 20 horas\n`[3 SGT]` Terceiro-Sargento – 15 horas",
        inline=False
    )
    embed.add_field(
        name="🌾 Militares Praças",
        value="`[CB]` Cabo – 12 horas\n`[SLD]` Soldado – 6 horas\n`[REC]` Recruta – 3 horas",
        inline=False
    )

    embed.set_footer(text="Exército Brasileiro do Shelby • Sistema de Gestão")
    await interaction.followup.send(embed=embed)


# --- SERVIDOR WEB PARA O RENDER (Evita erro de porta) ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive and running!")

def run_web():
    server = HTTPServer(('0.0.0.0', 10000), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_web, daemon=True).start()

# --- ARRANQUE DO BOT ---
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
        
