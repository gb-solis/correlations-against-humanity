import json
from collections import Counter
from matplotlib import pyplot as plt

path = r'C:\Users\Gabriel\Downloads\Telegram Desktop\ChatExport_2021-06-24\result.json'

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
    for i, mensagem in enumerate(mensagens):
        if mensagem[:36] == 'All answers received! The honourable':
            # assumindo todas as pessoas têm primeiros-nomes distintos
            czar = mensagem.split()[5]
            for j, resultado in enumerate(mensagens[i+1:]):
                # as mensagens de resultado contêm texto bold, então são listas
                # e o nome do vencedor deve estar no primeiro elemento
                candidato = resultado[0]
                if 'wins a point!' in candidato:
                    # assumindo todas as pessoas têm primeiros-nomes distintos
                    vencedor = candidato.split()[0]
                    break
            escolhas = czares.get(czar, [])
            escolhas.append(vencedor)
            czares.setdefault(czar, escolhas)
    contagem = {czar: Counter(escolhas) for czar, escolhas in czares.items()}
    return contagem
    
    
contagem = crawler(mensagens)
porcentagens = {czar: {jog: val/sum(contagem[czar].values()) 
                          for jog, val in contagem[czar].items()} 
                for czar in contagem}

for czar, escolhas in porcentagens.items():
    pontos = zip(*escolhas.items())
    plt.plot(*pontos, 'o', label=czar)
    
# =============================================================================
# TODO: 
#   pegar todos esses dados, ordenar os jogadores, colocar em matriz (?)
#   ver como cada czar se diferencia da média para cada respondente, em desvios-padrão
#   plotar melhor os dados
#   mostrar quem mais atrasa (print('leonardo e thomas'))
#   levar em conta que certos jogadores estavam ausentes (como?)
# =============================================================================

plt.title('Escolhas de cada czar')
plt.ylabel('Chance de ser escolhido')
plt.xlabel('Autor da resposta')
plt.legend(fontsize='small')
plt.show()