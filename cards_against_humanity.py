# =============================================================================
# TODO: 
#   pegar todos esses dados, ordenar os jogadores, colocar em matriz (?)
#   ver como cada czar se diferencia da média para cada respondente, em desvios-padrão
#   plotar melhor os dados
#   mostrar quem mais atrasa (print('leonardo e thomas'))
#   levar em conta que certos jogadores estavam ausentes (como?)
# =============================================================================

import json
import os
import numpy as np
from collections import Counter
from matplotlib import pyplot as plt

local_folder = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(local_folder, 'result.json')

# path = r'C:\Users\Gabriel\Downloads\Telegram Desktop\ChatExport_2021-06-24\result.json'

with open(path, 'r', encoding='utf8') as file:
    dados = json.load(file)

mensagens_totais = [msg for msg in dados['messages'] if msg['type']=='message']

# queremos analisar correlações entre escolhas de pessoas
# essa informação está contida nas mensagens do bot; podemos descartar as restantes

mensagens = [msg['text'] for msg in mensagens_totais if msg['from']=='Chat Against Humanity']

# antes dessa mensagem, o jogo era só Gabriel, Artur e Leo; descartei
msg_inicial = 91
mensagens = mensagens[msg_inicial:]

def crawler(mensagens):
    '''lê as mensagens em "mensagens" e registra qual czar deu vitória a que
    respondente; retorna um dicionário de czares'''
    czares = {}
    jogadores = [] # conjunto dos que mandaram ao menos uma carta
    for i, mensagem in enumerate(mensagens):
        if mensagem[:36] == 'All answers received! The honourable':
            czar_escolheu = False
            # assumindo todas as pessoas têm primeiros-nomes distintos
            czar = mensagem.split()[5]
            for j, resultado in enumerate(mensagens[i+1:]):
                # as mensagens de resultado contêm texto bold, então são listas
                # e o nome do vencedor deve estar no primeiro elemento
                candidato = resultado[0]
                if 'wins a point!' in candidato:
                    # assumindo todas as pessoas têm primeiros-nomes distintos
                    czar_escolheu = True
                    vencedor = candidato.split()[0]
                    if vencedor not in jogadores:
                        jogadores.append(vencedor)
                    break
                
            if czar_escolheu:
                if czar in czares:
                    czares[czar].append(vencedor)
                else:
                    czares[czar] = [vencedor]

    contagem = {czar: Counter(escolhas) for czar, escolhas in czares.items()}
    
    # Preencher jogadores que cada czar NÃO escolheu com 0
    for czar in contagem:
        for jogador in jogadores:
            if jogador not in contagem[czar]:
                contagem[czar][jogador] = 0
    return (contagem, jogadores)
    
    
contagem, jogadores = crawler(mensagens)

def plot_chances(contagem):
    porcentagens = {czar: {jog: val/sum(contagem[czar].values()) 
                              for jog, val in contagem[czar].items() if val != 0} 
                    for czar in contagem}
    
    for czar, escolhas in porcentagens.items():
        pontos = list(zip(*escolhas.items()))
        plt.plot(*pontos, 'o', label=czar)
    
    plt.title('Escolhas de cada czar')
    plt.ylabel('Chance de ser escolhido')
    plt.xlabel('Autor da resposta')
    plt.legend(fontsize='small')
    plt.show()

# Faz um heat map 2D das escolhas que cada czar (eixo y) fez de cada jogador (eixo x)
# Tutorial usado: https://www.pythonpool.com/matplotlib-heatmap/
def plot_heatmap(contagem, jogadores):
    czares = contagem.keys()
    matriz_escolhas = [[contagem[czar][jogador] for jogador in jogadores] for czar in czares]
    
    plt.xticks(ticks=np.arange(len(jogadores)), labels=jogadores, rotation=90)
    plt.yticks(ticks=np.arange(len(czares)), labels=czares)
    plt.xlabel('Autor da resposta')
    plt.ylabel('Czar')
    heatmap = plt.imshow(matriz_escolhas, cmap='Blues', interpolation='nearest')
    plt.colorbar(heatmap)
    
plot_chances(contagem)
plot_heatmap(contagem, jogadores)