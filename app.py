import os
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, session, send_from_directory

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = 'copa2026_bolao_dos_amigos_secreto_gols'

JOGOS_JSON = 'Inicio/jogos.json'
PALPITES_JSON = 'palpites.json'
USUARIOS_JSON = 'usuarios.json'
CLASSIFICACAO_JSON = 'classificação/classificacao.json'

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
       (real_f > real_c and palp_f > palp_f) or \
       (real_c == real_f and palp_c == palp_f):
        return 1, 0, 1  # Vendedor/Empate
    return 0, 0, 0

# --- LOGIN COM NOMES COMPLETOS CORRIGIDOS ---
@app.route('/api/login', methods=['POST'])
def login():
    dados = request.json
    usuario_input = dados.get('usuario')
    senha_input = dados.get('senha')
    
    # IMPORTANTE: Nomes corrigidos para aparecerem completos nas tabelas!
    usuarios_padrao = [
        {"usuario": "maria", "senha": "maria123", "nome": "Maria Isabel", "modalidade": "completo"},
        {"usuario": "bruno", "senha": "bruno123", "nome": "Bruno", "modalidade": "completo"},
        {"usuario": "rodrigo", "senha": "rodrigo123", "nome": "Rodrigo", "modalidade": "brasil_apenas"},
        {"usuario": "luciana", "senha": "luciana123", "nome": "Luciana", "modalidade": "completo"},
        {"usuario": "claudia", "senha": "claudia123", "nome": "Cláudia", "modalidade": "brasil_apenas"},
        {"usuario": "manuela", "senha": "manuela123", "nome": "Manuela", "modalidade": "completo"},
        {"usuario": "daniel", "senha": "daniel123", "nome": "Daniel", "modalidade": "completo"}
    ]
    
    # Se o seu usuarios.json antigo existir, delete-o para carregar essa lista nova!
    usuarios = carregar_json(USUARIOS_JSON, padrao=usuarios_padrao)
    user = next((u for u in usuarios if u['usuario'] == usuario_input and u['senha'] == senha_input), None)
    
    if user:
        session['usuario'] = user['usuario']
        session['nome'] = user['nome']
        session['modalidade'] = user.get('modalidade', 'completo')
        return jsonify({"sucesso": True, "nome": user['nome']})
    return jsonify({"sucesso": False, "mensagem": "Usuário ou senha incorretos."}), 401

# --- ROTA PARA CONSEGUIR LISTA DE JOGOS FILTRADA ---
@app.route('/api/jogos_por_escolha', methods=['GET'])
def jogos_por_escolha():
    escolha = request.args.get('tipo', 'geral') # 'geral' ou 'brasil'
    jogos = carregar_json(JOGOS_JSON)
    agora = datetime.now()
    
    jogos_filtrados = []
    for idx, jogo in enumerate(jogos):
        # Ignora jogos não definidos administrativamente pela FIFA
        if "A definir" in jogo['time_casa'] or "A definir" in jogo['time_fora']:
            continue
            
        # Filtra caso a escolha seja apenas os jogos do Brasil
        if escolha == 'brasil' and jogo['tipo'] != 'brasil':
            continue
            
        data_jogo = datetime.fromisoformat(jogo['data_iso'])
        # Verifica se o jogo está bloqueado para apostas (menos de 15 minutos do início ou finalizado)
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
            continue # Bloqueia gravação se violar o limite de tempo

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

# --- ROTA OFICIAL: CLASSIFICAÇÃO DE TODOS OS GRUPOS DA COPA 2026 ---
# --- ROTA CORRIGIDA: LÊ DIRETAMENTE O JSON DO SEU SCRIPT DE CLASSIFICAÇÃO ---
@app.route('/api/grupos_copa', methods=['GET'])
def obter_grupos_copa():
    # Caminho do ficheiro que o seu grupos_classifica.py gera
    caminho_classificacao = 'classificacao.json'
    
    dados_originais = carregar_json(caminho_classificacao, padrao=[])
    
    grupos_formatados = {}
    
    for item in dados_originais:
        # Transforma o padrão da API "GROUP_A" em "Grupo A"
        nome_grupo_original = item.get('grupo', 'Grupo Desconhecido')
        nome_amigavel = nome_grupo_original.replace('GROUP_', 'Grupo ')
        
        # O seu script já salva uma lista de 'times' com position, team e points
        grupos_formatados[nome_amigavel] = item.get('times', [])
        
    return jsonify(grupos_formatados)

if __name__ == '__main__':
    app.run(debug=True, port=5000)