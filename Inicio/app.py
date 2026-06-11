from flask import Flask, request, jsonify, send_from_directory
import os
import json
from datetime import datetime, timedelta

CAMINHO_RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
app = Flask(__name__, static_folder=CAMINHO_RAIZ, static_url_path='')

# Arquivo onde os palpites serão guardados
ARQUIVO_PALPITES = os.path.join(CAMINHO_RAIZ, 'palpites.json')
ARQUIVO_JOGOS = os.path.join(CAMINHO_RAIZ, 'jogos.json')

USUARIOS_PERMITIDOS = {
    "maria": "copa2026", "lais": "bolaonacopa", "participante3": "senha123",
    "participante4": "senha456", "participante5": "senha789",
    "participante6": "senhaabc", "participante7": "senhaxyz"
}

def carregar_dados(arquivo, padrao=[]):
    if not os.path.exists(arquivo):
        return padrao
    with open(arquivo, 'r', encoding='utf-8') as f:
        return json.load(f)

def salvar_dados(arquivo, dados):
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

@app.route('/')
def index():
    return send_from_directory(CAMINHO_RAIZ, 'login.html')

@app.route('/<path:path>')
def servir_arquivos(path):
    return send_from_directory(CAMINHO_RAIZ, path)

@app.route('/api/login', methods=['POST'])
def login():
    dados = request.get_json()
    usuario = dados.get('usuario', '').strip().lower()
    senha = dados.get('senha', '')
    if usuario in USUARIOS_PERMITIDOS and USUARIOS_PERMITIDOS[usuario] == senha:
        return jsonify({"sucesso": True, "usuario": usuario}), 200
    return jsonify({"sucesso": False, "erro": "Usuário ou senha incorretos."}), 401

# --- NOVA ROTA: SALVAR PALPITE ---
@app.route('/api/palpite', methods=['POST'])
def salvar_palpite():
    dados = request.get_json()
    usuario = dados.get('usuario')
    id_jogo = str(dados.get('id_jogo'))
    gols_time1 = dados.get('gols_time1')
    gols_time2 = dados.get('gols_time2')
    
    # 1. Buscar o horário do jogo no seu jogos.json para validar os 15 minutos
    jogos = carregar_dados(ARQUIVO_JOGOS, {})
    jogo = jogos.get(id_jogo)
    
    if not jogo:
        return jsonify({"erro": "Jogo não encontrado"}), 404
        
    # Exemplo de formato esperado no JSON: "2026-06-15 15:00"
    horario_jogo = datetime.strptime(jogo['data_hora'], "%Y-%m-%d %H:%M")
    limite_aposta = horario_jogo - timedelta(minutes=15)
    
    if datetime.now() > limite_aposta:
        return jsonify({"erro": "As apostas para este jogo fecharam (limite de 15 min antes)."}), 400

    # 2. Gravar o palpite
    palpites = carregar_dados(ARQUIVO_PALPITES, {})
    
    if usuario not in palpites:
        palpites[usuario] = {}
        
    palpites[usuario][id_jogo] = {
        "gols_time1": int(gols_time1),
        "gols_time2": int(gols_time2),
        "data_palpite": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    salvar_dados(ARQUIVO_PALPITES, palpites)
    return jsonify({"sucesso": True, "mensagem": "Palpite registrado!"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)