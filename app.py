import os
import json
import hashlib
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, session, send_from_directory

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = 'copa2026_bolao_dos_amigos_secreto_gols'

JOGOS_JSON = 'Inicio/jogos.json'
PALPITES_JSON = 'palpites.json'
USUARIOS_JSON = 'usuarios.json'
CLASSIFICACAO_JSON = 'classificacao.json'

def carregar_json(caminho, padrao=[]):
    if not os.path.exists(caminho):
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(padrao, f, ensure_ascii=False, indent=2)
        return padrao
    with open(caminho, 'r', encoding='utf-8') as f:
        return json.load(f)

def salvar_json(caminho, dados):
    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def calcular_pontos_jogo(gols_casa_real, gols_fora_real, gols_casa_palpite, gols_fora_palpite):
    if gols_casa_real == '-' or gols_fora_real == '-':
        return 0, 0, 0
    try:
        real_c, real_f = int(gols_casa_real), int(gols_fora_real)
        palp_c, palp_f = int(gols_casa_palpite), int(gols_fora_palpite)
    except (ValueError, TypeError):
        return 0, 0, 0

    if real_c == palp_c and real_f == palp_f:
        return 2, 1, 0  # Placar exato
    if (real_c > real_f and palp_c > palp_f) or \
       (real_f > real_c and palp_f > palp_c) or \
       (real_c == real_f and palp_c == palp_f):
        return 1, 0, 1  # Vencedor ou Empate
    return 0, 0, 0

def gerar_hash_senha(senha_padrão):
    return hashlib.sha256(senha_padrão.encode('utf-8')).hexdigest()

# --- ROTAS DE SERVIÇO DE ARQUIVOS ESTÁTICOS ---
@app.route('/')
def index():
    return send_from_directory('.', 'login.html')

@app.route('/<path:path>')
def servir_arquivos(path):
    return send_from_directory('.', path)

# --- VERIFICAÇÃO DE SESSÃO ATIVA ---
@app.route('/api/usuario_atual', methods=['GET'])
def usuario_atual():
    if 'usuario' in session:
        return jsonify({"logado": True, "nome": session['nome']})
    return jsonify({"logado": False})

# --- ROTA DE LOGOUT ---
@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"sucesso": True})

# --- LOGIN TOTALMENTE INDEPENDENTE DO GITHUB ---
# --- LOGIN TOTALMENTE IMUNE A ERROS DE CASING (MAIÚSCULAS/MINÚSCULAS) ---
@app.route('/api/login', methods=['POST'])
def login():
    dados = request.json
    usuario_input = dados.get('usuario', '').strip().lower()
    senha_input = dados.get('senha', '')

    # Gera os dois formatos possíveis de hash para garantir o cruzamento de dados
    hash_minusculo = gerar_hash_senha(senha_input).lower()
    hash_maiusculo = gerar_hash_senha(senha_input).upper()

    # Seus usuários reservas (Todos como completo por padrão)
    usuarios_fallback = [
        {"usuario": "maria", "senha_hash": "228f645851de956b60700d389a9f244199df3da3ff0c62e5200f682859f13885", "nome": "Maria Isabel", "modalidade": "completo"},
        {"usuario": "bruno", "senha_hash": "b2f6ef38fb978d462db1dbb2fa41fb00282662c1d37fcfefd7764d603e91129b", "nome": "Bruno", "modalidade": "completo"},
        {"usuario": "rodrigo", "senha_hash": "5be789fcfda7428f731a54776602cf98b1ecf8b5490e0c8b3fbba75498ff0eb3", "nome": "Rodrigo", "modalidade": "completo"},
        {"usuario": "luciana", "senha_hash": "692c817294025178051772186835a0928e8334465d64be931f6e2f18378546b4", "nome": "Luciana", "modalidade": "completo"},
        {"usuario": "claudia", "senha_hash": "959e1c251f28b76fc1eb7054f066b57917f9e8a5a4176840742d6211758c0c97", "nome": "Cláudia", "modalidade": "completo"},
        {"usuario": "manuela", "senha_hash": "63a2fa80b271d46797db1386762be71f28e21757a3e2158866dd36d7560da42b", "nome": "Manuela", "modalidade": "completo"},
        {"usuario": "daniel", "senha_hash": "997b6932a9390a82772589578166c4bf9f2b87fcf3008447da0bda4ff0507a21", "nome": "Daniel", "modalidade": "completo"},
        {"usuario": "lais", "senha_hash": "9360814980a37c959775f0a0a56391a1372702be97782ee418be9687e35b7191", "nome": "Lais Garcia", "modalidade": "completo"}
    ]

    usuarios = carregar_json(USUARIOS_JSON, padrao=usuarios_fallback)
    user = next((u for u in usuarios if u['usuario'] == usuario_input), None)

    if user:
        autenticado = False
        
        # Puxa o valor da senha gravada no banco (pode estar como 'senha' ou 'senha_hash')
        banco_senha_hash = str(user.get('senha_hash', '')).strip()
        banco_senha_limpa = str(user.get('senha', '')).strip()

        # SUPER VALIDAÇÃO: Testa contra todas as combinações possíveis
        if banco_senha_hash:
            if banco_senha_hash.lower() == hash_minusculo:
                autenticado = True
            elif banco_senha_hash.upper() == hash_maiusculo:
                autenticado = True
            elif banco_senha_hash == senha_input: # Se o hash gravado for a senha limpa por engano
                autenticado = True
                
        if banco_senha_limpa and banco_senha_limpa == senha_input:
            autenticado = True

        if autenticado:
            session['usuario'] = user['usuario']
            session['nome'] = user['nome']
            session['modalidade'] = user.get('modalidade', 'completo')
            return jsonify({"sucesso": True, "nome": user['nome']})

    return jsonify({"sucesso": False, "mensagem": "Usuário ou senha incorretos."}), 401
# --- LISTA DE JOGOS DISPONÍVEIS PARA PALPITE ---
@app.route('/api/jogos_por_escolha', methods=['GET'])
def jogos_por_escolha():
    escolha = request.args.get('tipo', 'geral')
    jogos = carregar_json(JOGOS_JSON)
    agora = datetime.now()

    jogos_filtrados = []
    for idx, jogo in enumerate(jogos):
        if "A definir" in jogo['time_casa'] or "A definir" in jogo['time_fora']:
            continue
        if escolha == 'brasil' and jogo['tipo'] != 'brasil':
            continue

        data_jogo = datetime.fromisoformat(jogo['data_iso'])
        bloqueado = (jogo['status'] == 'FINISHED' or agora >= (data_jogo - timedelta(minutes=15)))

        jogo_copia = jogo.copy()
        jogo_copia['id_jogo'] = idx
        jogo_copia['bloqueado'] = bloqueado
        jogos_filtrados.append(jogo_copia)

    return jsonify(jogos_filtrados)

# --- SALVAR PALPITES ---
@app.route('/api/palpites', methods=['POST'])
def salvar_palpites():
    if 'usuario' not in session:
        return jsonify({"erro": "Não autorizado."}), 401

    usuario_actual = session['usuario']
    novos_palpites = request.json
    jogos = carregar_json(JOGOS_JSON)
    todos_palpites = carregar_json(PALPITES_JSON, padrao={})

    palpites_usuario = todos_palpites.get(usuario_actual, {})
    agora = datetime.now()

    for idx_str, palpite in novos_palpites.items():
        idx = int(idx_str)
        if idx >= len(jogos): continue

        jogo = jogos[idx]
        data_jogo = datetime.fromisoformat(jogo['data_iso'])

        if jogo['status'] == 'FINISHED' or agora >= (data_jogo - timedelta(minutes=15)):
            return jsonify({"sucesso": False, "erro": "Apostas encerradas para este jogo!"}), 400

        palpites_usuario[idx_str] = {
            "casa": int(palpite['casa']),
            "fora": int(palpite['fora'])
        }

    todos_palpites[usuario_actual] = palpites_usuario
    salvar_json(PALPITES_JSON, todos_palpites)
    return jsonify({"sucesso": True, "mensagem": "Palpites salvos!"})

@app.route('/api/meus_palpites_salvos', methods=['GET'])
def obter_palpites_usuario():
    if 'usuario' not in session: return jsonify({"erro": "Não autorizado."}), 401
    todos_palpites = carregar_json(PALPITES_JSON, padrao={})
    return jsonify(todos_palpites.get(session['usuario'], {}))

# --- ROTA DO HISTÓRICO ---
@app.route('/api/historico_jogos', methods=['GET'])
def obter_historico_jogos():
    jogos = carregar_json(JOGOS_JSON)
    todos_palpites = carregar_json(PALPITES_JSON, padrao={})
    usuarios = carregar_json(USUARIOS_JSON)

    historico_filtrado = []
    for idx, jogo in enumerate(jogos):
        if jogo['gols_casa'] == '-' or jogo['gols_fora'] == '-':
            continue

        palpites_do_jogo = {}
        for u in usuarios:
            user_id = u['usuario']
            palp_usuario = todos_palpites.get(user_id, {}).get(str(idx), None)

            if palp_usuario:
                pts, _, _ = calcular_pontos_jogo(jogo['gols_casa'], jogo['gols_fora'], palp_usuario['casa'], palp_usuario['fora'])
                palpites_do_jogo[u['nome']] = f"{palp_usuario['casa']} x {palp_usuario['fora']} ({pts} pts)"
            else:
                palpites_do_jogo[u['nome']] = "Não apostou (0 pts)"

        jogo_info = {
            "data": f"{jogo['dia']} - {jogo['hora']}",
            "confronto": f"⚽ {jogo['time_casa']} {jogo['gols_casa']} x {jogo['gols_fora']} {jogo['time_fora']}",
            "palpites": palpites_do_jogo
        }
        historico_filtrado.append(jogo_info)

    return jsonify({"jogos": historico_filtrado, "participantes": [u['nome'] for u in usuarios]})

# --- RANKING EM TEMPO REAL ---
@app.route('/api/ranking_e_historico', methods=['GET'])
def obter_ranking_e_historico():
    jogos = carregar_json(JOGOS_JSON)
    todos_palpites = carregar_json(PALPITES_JSON, padrao={})
    usuarios = carregar_json(USUARIOS_JSON)

    rank_completo_dict = {}
    rank_brasil_dict = {}

    for u in usuarios:
        base = {"nome": u['nome'], "pontos": 0, "placares_exatos": 0, "vencedores": 0}
        if u['modalidade'] == 'completo':
            rank_completo_dict[u['usuario']] = base.copy()
        rank_brasil_dict[u['usuario']] = base.copy()

    for usuario, palpites in todos_palpites.items():
        for idx_str, palpite in palpites.items():
            idx = int(idx_str)
            if idx >= len(jogos): continue

            jogo = jogos[idx]
            pontos, exato, vencedor = calcular_pontos_jogo(jogo['gols_casa'], jogo['gols_fora'], palpite['casa'], palpite['fora'])

            if jogo['tipo'] == 'brasil' and usuario in rank_brasil_dict:
                rank_brasil_dict[usuario]["pontos"] += pontos
                rank_brasil_dict[usuario]["placares_exatos"] += exato
                rank_brasil_dict[usuario]["vencedores"] += vencedor

            if usuario in rank_completo_dict:
                rank_completo_dict[usuario]["pontos"] += pontos
                rank_completo_dict[usuario]["placares_exatos"] += exato
                rank_completo_dict[usuario]["vencedores"] += vencedor

    ordenado_completo = sorted(rank_completo_dict.values(), key=lambda x: x['pontos'], reverse=True)
    ordenado_brasil = sorted(rank_brasil_dict.values(), key=lambda x: x['pontos'], reverse=True)

    for i, item in enumerate(ordenado_completo): item['posicao'] = f"{i+1}º"
    for i, item in enumerate(ordenado_brasil): item['posicao'] = f"{i+1}º"

    return jsonify({"ranking_geral": ordenado_completo, "ranking_brasil": ordenado_brasil})

# --- CLASSIFICAÇÃO DOS GRUPOS ---
@app.route('/api/grupos_copa', methods=['GET'])
def obter_grupos_copa():
    dados_originais = carregar_json(CLASSIFICACAO_JSON, padrao=[])
    grupos_formatados = {}
    for item in dados_originais:
        nome_grupo_original = item.get('grupo', 'Grupo Desconhecido')
        nome_amigavel = nome_grupo_original.replace('GROUP_', 'Grupo ')
        grupos_formatados[nome_amigavel] = item.get('times', [])
    return jsonify(grupos_formatados)

if __name__ == '__main__':
    app.run(debug=True, port=5000)