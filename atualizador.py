import os
import json
import requests

JOGOS_JSON = 'jogos.json'
CLASSIFICACAO_JSON = 'classificacao.json'
TRADUCOES_JSON = 'traducoes.json'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.365scores.com/'
}

def carregar_json(caminho):
    if os.path.exists(caminho):
        with open(caminho, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {} if 'traducoes' in caminho or 'classificacao' in caminho else []

def salvar_json(caminho, dados):
    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def atualizar_jogos(tradutor):
    print("🔄 1. Buscando resultados no servidor estável do 365Scores...")
    url = "https://champs.365scores.com/data/games/?competitions=5930"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        print(f"📡 Status da Resposta (Jogos): {response.status_code}")
        
        if response.status_code != 200:
            print("❌ Erro ao acessar a API do 365Scores.")
            return

        dados_api = response.json().get('games', [])
        jogos_locais = carregar_json(JOGOS_JSON)
        
        if not jogos_locais:
            print("⚠️ jogos.json local não encontrado ou vazio.")
            return

        jogos_atualizados_count = 0

        for jogo_api in dados_api:
            home_api = jogo_api.get('homeCompetitor', {}).get('name', '')
            away_api = jogo_api.get('awayCompetitor', {}).get('name', '')

            home_traduzido = tradutor.get(home_api, home_api)
            away_traduzido = tradutor.get(away_api, away_api)
            game_status = jogo_api.get('status', {}).get('id')
            
            for jogo in jogos_locais:
                if str(jogo.get('time_casa')).lower() == home_traduzido.lower() and \
                   str(jogo.get('time_fora')).lower() == away_traduzido.lower():
                    
                    g_casa = jogo_api.get('homeCompetitor', {}).get('score')
                    g_fora = jogo_api.get('awayCompetitor', {}).get('score')

                    if g_casa is not None and g_fora is not None and g_casa != -1:
                        jogo['gols_casa'] = str(int(g_casa))
                        jogo['gols_fora'] = str(int(g_fora))
                        
                        if game_status == 3:
                            jogo['status'] = 'FINISHED'
                        else:
                            jogo['status'] = 'LIVE'
                            
                        jogos_atualizados_count += 1
                        print(f"  ⚽ Placar Sincronizado: {jogo['time_casa']} {jogo['gols_casa']} x {jogo['gols_fora']} {jogo['time_fora']}")
                    break

        salvar_json(JOGOS_JSON, jogos_locais)
        print(f"✨ Sucesso: {jogos_atualizados_count} placares atualizados!")

    except Exception as e:
        print(f"💥 Erro ao processar jogos: {e}")

def atualizar_classificacao(tradutor):
    print("\n🔄 2. Buscando tabela de classificação dos grupos...")
    url = "https://champs.365scores.com/data/standings/?competitions=5930"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        print(f"📡 Status da Resposta (Classificação): {response.status_code}")
        
        if response.status_code != 200:
            return

        dados_api = response.json().get('standings', [])
        nova_classificacao = []

        for item in dados_api:
            nome_grupo_en = item.get('name', 'Group Unknown')
            nome_grupo_pt = nome_grupo_en.upper().replace('GROUP ', 'GROUP_').replace(' ', '_')

            times_formatados = []
            for linha in item.get('rows', []):
                nome_time_en = linha.get('competitor', {}).get('name', '')
                nome_time_pt = tradutor.get(nome_time_en, nome_time_en)

                stats = linha.get('stats', [])
                jogos = next((s.get('value') for s in stats if s.get('id') == 1), 0)
                vitorias = next((s.get('value') for s in stats if s.get('id') == 2), 0)
                saldo = next((s.get('value') for s in stats if s.get('id') == 5), 0)
                pontos = next((s.get('value') for s in stats if s.get('id') == 8), 0)

                times_formatados.append({
                    "nome": nome_time_pt,
                    "pontos": int(float(pontos)),
                    "jogos": int(float(jogos)),
                    "vitorias": int(float(vitorias)),
                    "saldogols": int(float(saldo))
                })

            nova_classificacao.append({
                "grupo": nome_grupo_pt,
                "times": times_formatados
            })

        salvar_json(CLASSIFICACAO_JSON, nova_classificacao)
        print("✨ Arquivo classificacao.json atualizado com sucesso!")

    except Exception as e:
        print(f"💥 Erro ao processar classificação: {e}")

if __name__ == "__main__":
    dici_traducoes = carregar_json(TRADUCOES_JSON)
    atualizar_jogos(dici_traducoes)
    atualizar_classificacao(dici_traducoes)
