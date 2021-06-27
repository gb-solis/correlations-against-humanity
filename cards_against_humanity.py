# =============================================================================
# TODO: 
#   ver como cada czar se diferencia da média para cada respondente, em desvios-padrão
#   plotar melhor os dados
#   mostrar quem mais atrasa (print('leonardo e thomas'))
#   levar em conta que certos jogadores estavam ausentes (como?)
# =============================================================================

import json
from collections import Counter
from matplotlib import pyplot as plt
import numpy as np


# path = r'C:\Users\Gabriel\Downloads\Telegram Desktop\ChatExport_2021-06-24\result.json'
path = 'result.json'

with open(path, 'r', encoding='utf8') as file:
    dados = json.load(file)

mensagens_totais = [msg for msg in dados['messages'] if msg['type']=='message']

# queremos analisar correlações entre escolhas de pessoas
# essa informação está contida nas mensagens do bot; podemos descartar as restantes
mensagens = [msg['text'] for msg in mensagens_totais if msg['from']=='Chat Against Humanity']

# antes dessa mensagem, o jogo era só Gabriel, Artur e Leo; descartei
msg_inicial = 91
mensagens = mensagens[msg_inicial:]


def ordena(contagem):
    '''pega um dicionário de contagem e ordena o Counter individual de cada 
    czar.'''
    # assume todos os participantes já foram czares
    output = {}
    ordem = contagem.keys()
    for czar in ordem:
        output[czar] = Counter()
        participantes = (jog for jog in ordem if jog!=czar)
        for jogador in participantes:
            output[czar][jogador] = contagem[czar][jogador]
    return output
            


def crawler(mensagens):
    '''lê as mensagens em "mensagens" e registra qual czar deu vitória a que
    respondente; retorna um dicionário de czares'''
    czares = {}
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
                    czar_escolheu = True
                    # assumindo todas as pessoas têm primeiros-nomes distintos
                    vencedor = candidato.split()[0]
                    break
            if czar_escolheu:
                escolhas = czares.get(czar, [])
                escolhas.append(vencedor)
                czares.setdefault(czar, escolhas)
    
    contagem_desord = {czar: Counter(escolhas) for czar, escolhas in czares.items()}
    contagem = ordena(contagem_desord)
    return contagem


def matriz(contagem):
    '''pega o dicionário de contagens e o converte em matriz.'''
    # assume todos os participantes já foram czares
    # linhas e colunas seguem a ordem dada em contagem.keys()
    # talvez seja inútil
    participantes = list(contagem.keys())
    n = len(participantes)
    mat = np.zeros((n,n))
    
    for c, czar in enumerate(participantes):
        for j, jogador in enumerate(participantes):
            mat[c,j] = contagem[czar].get(jogador, 0)
        # mat[c,c] = None
    return mat

        
contagem = crawler(mensagens)

porcentagens = {jogador: {jog: val/sum(contagem[jogador].values()) 
                          for jog, val in contagem[jogador].items()} 
                for jogador in contagem}


# plot "vazio", só para inicializar o primeiro nome no eixo x e garantir o bom-ordenamento
primeiro = list(porcentagens.keys())[0]
plt.plot([primeiro], [None], color='k')

for czar, escolhas in porcentagens.items():
    pontos = list(zip(*escolhas.items()))
    plt.plot(*pontos, 'o:', label=czar)
    

plt.title('Escolhas de cada czar')
plt.ylabel('Chance de ser escolhido')
plt.xlabel('Autor da resposta')
plt.legend(fontsize='small')
plt.show()