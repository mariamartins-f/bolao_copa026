import requests
import json
import os
import time
from datetime import datetime, timedelta

# Importa o dicionário de traduções que você já possui
with open('traducoes.json', 'r', encoding='utf-8') as f:
    traducoes = json.load(f)

def traduzir_time(nome_en):
    return traducoes.get(nome_en, nome_en)

def atualizar_dados_copa():
    uri = "https://api.football-data.org/v4/competitions/2000/matches"
    headers = { "X-Auth-Token": "a7e271a9d3814fcb9aa60d908b80a5a2" } # Seu Token Oficial
    
    try:
        response = requests.get(uri, headers=headers)
        if response.status_code != 200:
            print("Erro ao acessar API externa.")
            return

        dados = response.json()
        jogos_processados = []

        for match in dados.get('matches', []):
            time_casa_en = match['homeTeam']['name']
            time_fora_en = match['awayTeam']['name']
            
            # Pula jogos onde os times ainda não foram definidos administrativamente pela FIFA
            if not time_casa_en or not time_fora_en:
                continue
                
            time_casa = traduzir_time(time_casa_en)
            time_fora = traduzir_time(time_fora_en)

            # Ajuste de Fuso Horário para Brasília (UTC-3)
            data_utc = datetime.strptime(match['utcDate'], "%Y-%m-%dT%H:%M:%SZ")
            data_brasilia = data_utc - timedelta(hours=3)

            # Captura os gols se o jogo já aconteceu ou está acontecendo
            gols_casa = match['score']['fullTime']['home']
            gols_fora = match['score']['fullTime']['away']

            # Verifica se envolve a seleção do Brasil para marcar a categoria
            e_jogo_brasil = (time_casa.lower() == 'brasil' or time_fora.lower() == 'brasil')

            jogos_processados.append({
                "dia": data_brasilia.strftime("%d/%m/%Y"),
                "hora": data_brasilia.strftime("%H:%M"),
                "data_iso": data_brasilia.isoformat(), # Usado para validar o bloqueio de 15 minutos
                "time_casa": time_casa,
                "time_fora": time_fora,
                "gols_casa": gols_casa if gols_casa is not None else '-',
                "gols_fora": gols_fora if gols_fora is not None else '-',
                "status": match['status'], # FINISHED, IN_PLAY, TIMED...
                "tipo": "brasil" if e_jogo_brasil else "geral"
            })

        # Salva o resultado atualizado na pasta correta
        os.makedirs('Inicio', exist_ok=True)
        with open('Inicio/jogos.json', 'w', encoding='utf-8') as f:
            json.dump(jogos_processados, f, ensure_ascii=False, indent=2)
        print(f"Banco de jogos atualizado em: {datetime.now().strftime('%H:%M:%S')}")

    except Exception as e:
        print(f"Falha na sincronização automatizada: {e}")

if __name__ == "__main__":
    # Quando executado de forma independente, roda em loop atualizando a cada 10 minutos
    print("Iniciando monitoramento automático do Bolão...")
    while True:
        atualizar_dados_copa()
        time.sleep(600) # 600 segundos = 10 minutos