import discord
from discord.ext import commands
import datetime
import os
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

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


# --- 1. COMANDO: /promover ---
@bot.tree.command(name="promover", description="Promove um militar respeitando as permissões da hierarquia.")
async def promover(interaction: discord.Interaction, membro: discord.Member, cargo_patente: discord.Role):
    config_novo = PATENTES_CONFIG.get(cargo_patente.name)
    if not config_novo:
        await interaction.response.send_message(f"❌ O cargo **{cargo_patente.name}** não está registrado na tabela de CDP.", ephemeral=True)
        return

    nivel_autor = verificar_nivel_autor(interaction.user)
    cat_destino = config_novo["categoria"]
    nivel_destino = HIERARQUIA_CATEGORIAS.get(cat_destino, 0)

    # Validações de hierarquia
    if nivel_autor <= 3:
        await interaction.response.send_message("❌ **PROMOÇÃO NEGADA!** Praças, Graduados e Praças Especiais não têm permissão para promover.", ephemeral=True)
        return
    elif nivel_autor == 4 and nivel_destino > 1:
        await interaction.response.send_message("❌ **PROMOÇÃO NEGADA!** Oficiais Subalternos só podem promover Praças.", ephemeral=True)
        return
    elif nivel_autor == 5 and nivel_destino > 3:
        await interaction.response.send_message("❌ **PROMOÇÃO NEGADA!** Oficiais Intermediários só podem promover Praças, Graduados e Praças Especiais.", ephemeral=True)
        return
    elif nivel_autor == 6 and nivel_destino > 5:
        await interaction.response.send_message("❌ **PROMOÇÃO NEGADA!** Oficiais Superiores não podem promover para Cargos Generais.", ephemeral=True)
        return

    # Verificação de CDP
    agora = datetime.datetime.now()
    if membro.id in historico_cdp and agora < historico_cdp[membro.id]:
        restante = historico_cdp[membro.id] - agora
        horas = restante.seconds // 3600
        minutos = (restante.seconds % 3600) // 60
        await interaction.response.send_message(f"❌ **PROMOÇÃO BLOQUEADA!** {membro.mention} ainda está em CDP. Faltam {horas}h {minutos}m.", ephemeral=True)
        return

    # --- NOVO: Encontra e Remove a Patente Anterior Automaticamente ---
    patentes_lista = list(PATENTES_CONFIG.keys())
    for nome_patente in patentes_lista:
        if nome_patente != cargo_patente.name: # Se for outra patente da tabela que o membro tem
            cargo_velho = discord.utils.get(interaction.guild.roles, name=nome_patente)
            if cargo_velho and cargo_velho in membro.roles:
                await membro.remove_roles(cargo_velho)

    # Adiciona os novos cargos (Patente + Categoria)
    cargo_categoria = discord.utils.get(interaction.guild.roles, name=cat_destino)
    cargos_para_adicionar = [cargo_patente]
    if cargo_categoria:
        cargos_para_adicionar.append(cargo_categoria)

    await membro.add_roles(*cargos_para_adicionar)

    # Atualiza o Nickname com a nova Tag
    tag = config_novo["tag"]
    nome_limpo = membro.display_name.split("]")[-1].strip()
    try:
        await membro.edit(nick=f"{tag} {nome_limpo}"[:32])
    except Exception:
        pass

    # Registra o novo CDP
    horas_cdp = config_novo["horas"]
    data_liberacao = agora + datetime.timedelta(hours=horas_cdp)
    historico_cdp[membro.id] = data_liberacao

    # Mensagem Embed
    embed = discord.Embed(title="🛡️ Promoção Realizada com Sucesso!", description=f"O militar {membro.mention} foi promovido!", color=discord.Color.green())
    embed.add_field(name="📜 Cargos Atribuídos", value=f"{cargo_patente.mention}\n{cargo_categoria.mention if cargo_categoria else ''}", inline=False)
    embed.add_field(name="⏳ Duração do CDP", value=f"{horas_cdp} Horas", inline=True)
    embed.add_field(name="📅 Próxima Promoção", value=data_liberacao.strftime("%d/%m/%Y às %H:%M"), inline=True)
    embed.set_footer(text=f"Promovido por: {interaction.user.display_name}")

    await interaction.response.send_message(embed=embed)
        

# --- 2. COMANDO: /promover_varios ---
@bot.tree.command(name="promover_varios", description="Promove vários militares de uma vez (mencione-os).")
async def promover_varios(interaction: discord.Interaction, mencoes: str, cargo_patente: discord.Role):
    config_novo = PATENTES_CONFIG.get(cargo_patente.name)
    if not config_novo:
        await interaction.response.send_message(f"❌ O cargo **{cargo_patente.name}** não está registrado na tabela de CDP.", ephemeral=True)
        return

    nivel_autor = verificar_nivel_autor(interaction.user)
    cat_destino = config_novo["categoria"]
    nivel_destino = HIERARQUIA_CATEGORIAS.get(cat_destino, 0)

    if nivel_autor <= 3:
        await interaction.response.send_message("❌ **PROMOÇÃO NEGADA!** Não tens permissão para promover.", ephemeral=True)
        return
    elif nivel_autor == 4 and nivel_destino > 1:
        await interaction.response.send_message("❌ **PROMOÇÃO NEGADA!** Oficiais Subalternos só podem promover Praças.", ephemeral=True)
        return
    elif nivel_autor == 5 and nivel_destino > 3:
        await interaction.response.send_message("❌ **PROMOÇÃO NEGADA!** Oficiais Intermediários só podem promover até Praças Especiais.", ephemeral=True)
        return
    elif nivel_autor == 6 and nivel_destino > 5:
        await interaction.response.send_message("❌ **PROMOÇÃO NEGADA!** Oficiais Superiores não podem promover para Oficiais Generais.", ephemeral=True)
        return

    ids_membros = re.findall(r'<@!?(\d+)>', mencoes)
    if not ids_membros:
        await interaction.response.send_message("❌ Nenhum militar válido foi mencionado.", ephemeral=True)
        return

    agora = datetime.datetime.now()
    sucessos, erros = [], []
    cargo_categoria = discord.utils.get(interaction.guild.roles, name=cat_destino)
    horas_cdp = config_novo["horas"]
    patentes_lista = list(PATENTES_CONFIG.keys())

    for uid in ids_membros:
        membro = interaction.guild.get_member(int(uid))
        if not membro:
            continue
        if membro.id in historico_cdp and agora < historico_cdp[membro.id]:
            erros.append(f"{membro.mention} (Em CDP)")
            continue

        try:
            # Remove patentes antigas automaticamente
            for nome_pat in patentes_lista:
                if nome_pat != cargo_patente.name:
                    c_velho = discord.utils.get(interaction.guild.roles, name=nome_pat)
                    if c_velho and c_velho in membro.roles:
                        await membro.remove_roles(c_velho)

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

    await interaction.response.send_message(embed=embed)
    

    
# --- 3. COMANDO: /rebaixar ---
@bot.tree.command(name="rebaixar", description="Rebaixa um militar, atualiza os cargos, apelido e reseta o CDP.")
async def rebaixar(interaction: discord.Interaction, membro: discord.Member, cargo_patente_nova: discord.Role):
    nivel_autor = 0
    for role in interaction.user.roles:
        if role.name in CARGOS_REBAIXAR_PERMISSAO:
            nivel_autor = max(nivel_autor, CARGOS_REBAIXAR_PERMISSAO[role.name])

    if nivel_autor == 0:
        await interaction.response.send_message("❌ **REBAIXAMENTO NEGADO!** Apenas membros autorizados podem rebaixar.", ephemeral=True)
        return

    config_nova = PATENTES_CONFIG.get(cargo_patente_nova.name)
    if not config_nova:
        await interaction.response.send_message(f"❌ O cargo **{cargo_patente_nova.name}** não está registrado na tabela.", ephemeral=True)
        return

    patentes_lista = list(PATENTES_CONFIG.keys())
    
    try:
        # Remove todas as outras patentes antigas que o membro possa ter
        for nome_pat in patentes_lista:
            c_velho = discord.utils.get(interaction.guild.roles, name=nome_pat)
            if c_velho and c_velho in membro.roles:
                await membro.remove_roles(c_velho)

        # Adiciona a nova patente e respetiva categoria
        cargos_adicionar = [cargo_patente_nova]
        cat_nova_nome = config_nova["categoria"]
        cargo_cat_nova = discord.utils.get(interaction.guild.roles, name=cat_nova_nome)
        if cargo_cat_nova:
            cargos_adicionar.append(cargo_cat_nova)

        await membro.add_roles(*cargos_adicionar)

        # Atualiza a tag no Nickname
        tag = config_nova["tag"]
        nome_limpo = membro.display_name.split("]")[-1].strip()
        await membro.edit(nick=f"{tag} {nome_limpo}"[:32])

        # Reseta o CDP
        horas_cdp = config_nova["horas"]
        historico_cdp[membro.id] = datetime.datetime.now() + datetime.timedelta(hours=horas_cdp)

        embed = discord.Embed(title="⚠️ Rebaixamento Realizado", description=f"O militar {membro.mention} foi rebaixado para **{cargo_patente_nova.name}**.", color=discord.Color.orange())
        embed.set_footer(text=f"Rebaixado por {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Ocorreu um erro ao rebaixar: {e}", ephemeral=True)
        


# --- 4. COMANDO: /rebaixar_varios ---
@bot.tree.command(name="rebaixar_varios", description="Rebaixa vários militares de uma vez (mencione-os).")
async def rebaixar_varios(interaction: discord.Interaction, mencoes: str, cargo_patente_nova: discord.Role):
    nivel_autor = 0
    for role in interaction.user.roles:
        if role.name in CARGOS_REBAIXAR_PERMISSAO:
            nivel_autor = max(nivel_autor, CARGOS_REBAIXAR_PERMISSAO[role.name])

    if nivel_autor == 0:
        await interaction.response.send_message("❌ **REBAIXAMENTO NEGADO!** Apenas membros autorizados podem rebaixar.", ephemeral=True)
        return

    config_nova = PATENTES_CONFIG.get(cargo_patente_nova.name)
    if not config_nova:
        await interaction.response.send_message(f"❌ O cargo **{cargo_patente_nova.name}** não está registrado na tabela.", ephemeral=True)
        return

    ids_membros = re.findall(r'<@!?(\d+)>', mencoes)
    if not ids_membros:
        await interaction.response.send_message("❌ Nenhum militar válido foi mencionado.", ephemeral=True)
        return

    sucessos, erros = [], []
    cat_nova_nome = config_nova["categoria"]
    cargo_cat_nova = discord.utils.get(interaction.guild.roles, name=cat_nova_nome)
    horas_cdp = config_nova["horas"]
    patentes_lista = list(PATENTES_CONFIG.keys())
    agora = datetime.datetime.now()

    for uid in ids_membros:
        membro = interaction.guild.get_member(int(uid))
        if not membro:
            continue

        try:
            # Remove todas as patentes antigas
            for nome_pat in patentes_lista:
                c_velho = discord.utils.get(interaction.guild.roles, name=nome_pat)
                if c_velho and c_velho in membro.roles:
                    await membro.remove_roles(c_velho)

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
            erros.append(membro.mention)

    embed = discord.Embed(title="⚠️ Rebaixamento em Massa Realizado", color=discord.Color.orange())
    if sucessos:
        embed.add_field(name="✅ Rebaixados com Sucesso", value=", ".join(sucessos), inline=False)
    if erros:
        embed.add_field(name="❌ Falhas", value=", ".join(erros), inline=False)
    embed.set_footer(text=f"Ação executada por {interaction.user.display_name}")

    await interaction.response.send_message(embed=embed)
    


# --- 5. COMANDO: /cdp ---
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


# --- 6. COMANDO: /hierarquia ---
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
    await interaction.response.send_message(embed=embed)


# --- 7. COMANDO: /regras ---
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

# --- 8. COMANDO: /dicas_gramaticais ---
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
            "• **A gente vs. Agente:** \"A gente\" (separado) significa *nós*. \"Agente\" (junto) é uma profissão (ex: agente secreto).\n"
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

    embed.add_field(
        name="📝 3. Ortografia e Pontuação",
        value=(
            "• **Haver vs. A existir:** O verbo *haver* no sentido de existir é impessoal e fica sempre no singular (*Havia muitos soldados*).\n"
            "• **A vs. Há:** \"A\" indica tempo futuro ou distância. \"Há\" indica tempo passado (do verbo haver).\n"
            "• **Pontuação:** Use vírgulas para separar orações explicativas e evitar frases excessivamente longas."
        ),
        inline=False
    )

    embed.add_field(
        name="🎯 4. Exemplo Prático de Correção",
        value=(
            "❌ **Errado:** \"Agente vai fazer a formatura hoje mais tarde.\"\n"
            "✅ **Correto:** \"A gente vai fazer a formatura hoje mais tarde.\"\n"
            "💡 **Explicação:** Usa-se *a gente* (separado) para indicar *nós*, e *mais* (com i) para indicar o acréscimo de tempo."
        ),
        inline=False
    )

    embed.set_footer(text="Exército Brasileiro • Canal de Apoio Educativo e Gramatical")
    await interaction.response.send_message(embed=embed)
    


# --- 9. COMANDO: /informacoes (Sobre o Exército) ---
@bot.tree.command(name="informacoes", description="Exibe informações gerais sobre o Exército Brasileiro do Shelby no Roblox.")
async def informacoes(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🇧🇷 EXÉRCITO BRASILEIRO DO SHELBY • INFORMAÇÕES",
        description="Bem-vindo ao quartel-general oficial! Descobre mais sobre a nossa instituição e diretrizes no Roblox:",
        color=discord.Color.gold()
    )

    embed.add_field(
        name="🎮 1. Sobre a Instituição (Roblox)",
        value=(
            "• **Início:** O nosso exército é um projeto **novo**, estruturado para proporcionar uma experiência imersiva, realista e disciplinada de simulação militar no Roblox.\n"
            "• **Missão:** Formar militares competentes, unidos e focados no companheirismo e na hierarquia."
        ),
        inline=False
    )

    embed.add_field(
        name="🎖️ 2. Hierarquia e Progressão",
        value=(
            "• **Patentes:** A nossa estrutura divide-se em 7 categorias (desde Praças até Oficiais Generais).\n"
            "• **Promoções:** Respeitamos rigorosamente os tempos de CDP (Cool Down Period). Consulta sempre o comando `/cdp` e a tabela em `/hierarquia`."
        ),
        inline=False
    )

    embed.add_field(
        name="📜 3. Normas e Conduta",
        value=(
            "• **Disciplina:** O respeito à cadeia de comando é obrigatório.\n"
            "• **Manuais:** Consulta os comandos `/regras` para diretrizes de comportamento e `/dicas` para orientações de evolução."
        ),
        inline=False
    )

    embed.add_field(
        name="⭐ 4. Como Participar e Crescer",
        value=(
            "• **Treinamentos:** Fica atento aos canais de avisos para participares nas instruções e formaturas.\n"
            "• **Comunicação:** Usa sempre uma linguagem clara e sê ativo na comunidade."
        ),
        inline=False
    )

    embed.set_footer(text="Exército Brasileiro do Shelby • Roblox Simulation")
    await interaction.response.send_message(embed=embed)
    


# --- SERVIDOR WEB DUMMY PARA O RENDER (KEEP ALIVE) ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive and running!")

def run_web():
    server = HTTPServer(('0.0.0.0', 10000), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_web, daemon=True).start()

# --- INICIALIZAÇÃO DO BOT ---
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
