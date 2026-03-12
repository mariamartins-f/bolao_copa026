import requests
import json

headers = {"X-Auth-Token": "a7e271a9d3814fcb9aa60d908b80a5a2"}
uri = "https://api.football-data.org/v4/competitions/2000/standings"

# Carregar traduções
with open('traducoes.json', 'r', encoding='utf-8') as f:
    traducoes = json.load(f)

def traduzir_time(nome_ingles):
    return traducoes.get(nome_ingles, nome_ingles)

response = requests.get(uri, headers=headers)

if response.status_code == 200:
    dados = response.json()
    
    classificacao = []
    
    for grupo in dados['standings']:
        nome_grupo = grupo.get('group', 'Grupo Desconhecido')
        times_grupo = []
        
        # Loop pelos times deste grupo
        for time in grupo['table']:
            times_grupo.append({
                'position': time['position'],
                'team': traduzir_time(time['team']['name']),
                'points': time['points']
            })
        
        
        classificacao.append({
            'grupo': nome_grupo,
            'times': times_grupo
        })
        
# SALVAR FORA DO LOOP - UMA VEZ SÓ
    with open('classificacao.json', 'w', encoding='utf-8') as f:
        json.dump(classificacao, f, ensure_ascii=False, indent=2)
    
    print(f"\n🎉 TOTAL: {len(classificacao)} grupos salvos em classificacao.json")
else:
    print(f"Erro: {response.status_code}")