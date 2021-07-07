# =============================================================================
# TODO: 
#   ver como cada czar se diferencia da média para cada respondente, em desvios-padrão
#   plotar melhor os dados
#   mostrar quem mais atrasa (print('leonardo e thomas'))
#   levar em conta que certos jogadores estavam ausentes (como?)
# =============================================================================

import json
import numpy as np
from collections import Counter
from matplotlib import pyplot as plt


path = 'result.json'

with open(path, 'r', encoding='utf8') as file:
    dados = json.load(file)

mensagens_totais = [msg for msg in dados['messages'] if msg['type']=='message']

# queremos analisar correlações entre escolhas de pessoas
# essa informação está contida nas mensagens do bot; podemos descartar as restantes
mensagens = [msg['text'] for msg in mensagens_totais 
             if msg['from']=='Chat Against Humanity']

# antes dessa mensagem, o jogo era só Gabriel, Artur e Leo; descartei
msg_inicial = 91
mensagens = mensagens[msg_inicial:]

def crawler(mensagens):
    '''lê as mensagens em "mensagens" e registra qual czar deu vitória a que
    respondente; retorna um dicionário de czares'''
    czares = {}
    jogadores = [] # conjunto dos que mandaram ao menos uma carta ou foram czar
    for i, mensagem in enumerate(mensagens):
        if mensagem[:36] == 'All answers received! The honourable':
            # assumindo todas as pessoas têm primeiros-nomes distintos
            czar = mensagem.split()[5]
            if czar not in jogadores:
                jogadores.append(czar)
            for j, resultado in enumerate(mensagens[i+1:]):
                if resultado[:36] == 'All answers received! The honourable':
                    break
                # as mensagens de resultado contêm texto bold, então são listas
                # e o nome do vencedor deve estar no primeiro elemento
                candidato = resultado[0]
                if 'wins a point!' in candidato:
                    # assumindo todas as pessoas têm primeiros-nomes distintos
                    vencedor = candidato.split()[0]
                    if vencedor == czar:
                        print(f'Erro! Vencedor {vencedor} é o mesmo que o czar {czar}')
                        print(f'Ganhou para pergunta número {i}: \n\n {mensagem}')
                        print(f'Com a resposta de número {j} \n\n {resultado}')
                    if vencedor not in jogadores:
                        jogadores.append(vencedor)
                    if czar in czares:
                        czares[czar].append(vencedor)
                    else:
                        czares[czar] = [vencedor]
                    break

    contagem_desord = {czar: Counter(escolhas) for czar, escolhas in czares.items()}
    não_czares = [jogador for jogador in jogadores if jogador not in czares]
    contagem_desord.update({não_czar: {} for não_czar in não_czares})
    
    contagem = {czar: dict(sorted(escolhas.items(), 
                                  key=lambda x: list(contagem_desord).index(x[0])))
                for czar, escolhas in contagem_desord.items()}
    return contagem


def plot_chances(contagem):
    porcentagens = {czar: {jog: val/sum(contagem[czar].values()) 
                              for jog, val in contagem[czar].items()}
                    for czar in (czar for czar in contagem if contagem[czar])}
    
    # plot "vazio", só para inicializar o primeiro nome no eixo x e garantir o 
    # bom-ordenamento
    primeiro = list(porcentagens.keys())[0]
    plt.plot([primeiro], [None], color='k')

    for czar, escolhas in porcentagens.items():
        pontos = list(zip(*escolhas.items()))
        plt.plot(*pontos, 'o:', label=czar)
        
    plt.title('Escolhas de cada czar')
    plt.ylabel('Chance de ser escolhido')
    plt.xlabel('Autor da resposta')
    plt.legend(fontsize='x-small')
    plt.show()


# Faz um heat map 2D das escolhas que cada czar (eixo y) fez de cada jogador (eixo x)
# Tutorial usado: https://www.pythonpool.com/matplotlib-heatmap/
def plot_heatmap(contagem):
    czares = [czar for czar in contagem.keys() if contagem[czar]]
    matriz_escolhas = [[contagem[czar].get(jog, 0) for jog in contagem] 
                       for czar in czares]
    plt.xticks(ticks=range(len(contagem)), labels=contagem.keys(), rotation=90)
    plt.yticks(ticks=range(len(czares)), labels=czares)
    plt.title('Escolhas de cada czar')
    plt.xlabel('Autor da resposta')
    plt.ylabel('Czar')
    heatmap = plt.imshow(matriz_escolhas, cmap='Blues', interpolation='nearest')
    plt.colorbar(heatmap)
    plt.show()
    
    
contagem = crawler(mensagens)
    
plot_chances(contagem)
plot_heatmap(contagem)