import requests
import json
from datetime import datetime, timedelta

headers = {"X-Auth-Token": "a7e271a9d3814fcb9aa60d908b80a5a2"} 
uri = "https://api.football-data.org/v4/competitions/2000/matches"

with open('traducoes.json', 'r', encoding='utf-8') as f:
    traducoes = json.load(f)

def traduzir_time(nome_ingles):
    """Função para traduzir nome do time"""
    return traducoes.get(nome_ingles, nome_ingles)  # Se não encontrar, mantém original

response = requests.get(uri, headers=headers)
jogos = []

if response.status_code == 200:
    dados = response.json()
    for match in dados['matches']:
        # Converter data UTC para horário de Brasília
        data_iso = match['utcDate']
        data_utc = datetime.fromisoformat(data_iso.replace('Z', '+00:00'))
        data_brasilia = data_utc - timedelta(hours=3)
        
        dia = data_brasilia.strftime('%d/%m/%Y')
        hora = data_brasilia.strftime('%H:%M')
        
        # Traduzir nomes dos times
        time_casa = traduzir_time(match['homeTeam']['name'])
        time_fora = traduzir_time(match['awayTeam']['name'])
        
        # Pegar placar
        if match['status'] == 'FINISHED':
            gols_casa = match['score']['fullTime']['home']
            gols_fora = match['score']['fullTime']['away']
        else:
            gols_casa = '-'
            gols_fora = '-'
        
        jogo = {
            'dia': dia,
            'hora': hora,
            'time_casa': time_casa,
            'gols_casa': gols_casa,
            'gols_fora': gols_fora,
            'time_fora': time_fora
        }
        jogos.append(jogo)
    
    # Salvar JSON
    with open('jogos.json', 'w', encoding='utf-8') as f:
        json.dump(jogos, f, ensure_ascii=False, indent=2)
    
    print(f"✅ {len(jogos)} jogos salvos em jogos.json")
    
    # Mostrar exemplo
    if jogos:
        print(f"\nExemplo: {jogos[0]['dia']} | {jogos[0]['hora']} | {jogos[0]['time_casa']} | {jogos[0]['gols_casa']} | x | {jogos[0]['gols_fora']} | {jogos[0]['time_fora']}")
else:
    print(f"❌ Erro: {response.status_code}")