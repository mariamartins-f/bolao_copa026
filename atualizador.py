import os
import json
import requests

# Arquivos locais do repositório
JOGOS_JSON = 'jogos.json'
CLASSIFICACAO_JSON = 'classificacao.json'
TRADUCOES_JSON = 'traducoes.json'

# Configurações da API-Football (v3)
# O token será puxado de forma segura das Secrets do GitHub
API_KEY = os.environ.get('API_FOOTBALL_KEY') 
ID_COPA = 1 # ID oficial da Copa do Mundo na v3

headers = {
    'x-rapidapi-host': 'v3.football.api-sports.io',
    'x-rapidapi-key': API_KEY
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
    url = f"https://v3.football.api-sports.io/fixtures?league={ID_COPA}&season=2026"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Erro na API de Jogos: Status {response.status_code}")
            return
        
        dados_api = response.json().get('response', [])
        jogos_locais = carregar_json(JOGOS_JSON)

        if not jogos_locais:
            print("Arquivo jogos.json local não encontrado ou vazio.")
            return

        for partida in dados_api:
            teams = partida.get('teams', {})
            home_api = teams.get('home', {}).get('name', '')
            away_api = teams.get('away', {}).get('name', '')

            # Traduz os nomes vindos da API usando seu traducoes.json
            home_traduzido = tradutor.get(home_api, home_api)
            away_traduzido = tradutor.get(away_api, away_api)

            # Procura o jogo equivalente no seu jogos.json
            for jogo in jogos_locais:
                if str(jogo.get('time_casa')).lower() == home_traduzido.lower() and \
                   str(jogo.get('time_fora')).lower() == away_traduzido.lower():
                    
                    fixture = partida.get('fixture', {})
                    status_short = fixture.get('status', {}).get('short')
                    goals = partida.get('goals', {})
                    
                    g_casa = goals.get('home')
                    g_fora = goals.get('away')

                    # Se o jogo já começou ou terminou e tem gols válidos
                    if g_casa is not None and g_fora is not None:
                        jogo['gols_casa'] = str(g_casa)
                        jogo['gols_fora'] = str(g_fora)
                        
                        if status_short in ['FT', 'AET', 'PEN']:
                            jogo['status'] = 'FINISHED'
                        elif status_short in ['1H', '2H', 'HT', 'LIVE']:
                            jogo['status'] = 'LIVE'
                    break

        salvar_json(JOGOS_JSON, jogos_locais)
        print("✅ jogos.json atualizado com sucesso!")
    except Exception as e:
        print(f"Erro ao processar jogos: {e}")

def atualizar_classificacao(tradutor):
    url = f"https://v3.football.api-sports.io/standings?league={ID_COPA}&season=2026"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Erro na API de Classificação: Status {response.status_code}")
            return

        dados_api = response.json().get('response', [])
        if not dados_api:
            return

        league_data = dados_api[0].get('league', {})
        standings_grupos = league_data.get('standings', [])

        nova_classificacao = []

        for grupo in standings_grupos:
            if not grupo: continue
            # Pega o nome do grupo ex: "Group A"
            nome_grupo_en = grupo[0].get('group', 'Group Unknown')
            nome_grupo_pt = nome_grupo_en.replace('Group ', 'GROUP_')

            times_formatados = []
            for item in grupo:
                nome_time_en = item.get('team', {}).get('name', '')
                nome_time_pt = tradutor.get(nome_time_en, nome_time_en)

                all_stats = item.get('all', {})
                
                times_formatados.append({
                    "nome": nome_time_pt,
                    "pontos": item.get('points', 0),
                    "jogos": all_stats.get('played', 0),
                    "vitorias": all_stats.get('win', 0),
                    "saldogols": item.get('goalsDiff', 0)
                })

            nova_classificacao.append({
                "grupo": nome_grupo_pt,
                "times": times_formatados
            })

        salvar_json(CLASSIFICACAO_JSON, nova_classificacao)
        print("✅ classificacao.json atualizada com sucesso!")
    except Exception as e:
        print(f"Erro ao processar classificação: {e}")

if __name__ == "__main__":
    dici_traducoes = carregar_json(TRADUCOES_JSON)
    atualizar_jogos(dici_traducoes)
    atualizar_classificacao(dici_traducoes)
