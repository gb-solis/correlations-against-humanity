# =============================================================================
# TODO: 
#   separar mensagens por jogos, fazer análise por jogo
#   fazer gif cronológico do histograma
#   fazer função que trace o desempenho cronologicamente
#   ver como cada czar se diferencia da média para cada respondente, em desvios-padrão
#   plotar melhor os dados
#   mostrar quem mais atrasa (print('leonardo e thomas'))
#   levar em conta que certos jogadores estavam ausentes (como?)
# =============================================================================

import json
from collections import Counter, namedtuple
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

# objeto que representa uma rodada
rodada = namedtuple('Rodada', 
                        ('czar', 'vencedor', 'pergunta', 'resposta', 
                             'alternativas', 'recebida', 'finalizada'),
                        defaults=(None, None, None, None, None, False, False))


def parser_alternativas(mensagem):
    '''parser para mensagens do tipo "All answers received"'''
    início, fim = mensagem.split('\n\n')
    czar = início.split()[5]
    pergunta = início.splitlines()[1][10:]
    alternativas = fim.split('\n  - ')
    alternativas[0] = alternativas[0][4:]
    return {'czar': czar, 'pergunta': pergunta, 'alternativas': alternativas}


def parser_resultados(mensagem):
    ''' parser para mensagens do tipo "x wins a point!" '''
    if isinstance(mensagem, str):
        linhas = mensagem.splitlines()
        vencedor = linhas[0].rstrip(' wins a point!')
        resposta = linhas[1] # copia a resposta + enunciado! TODO: resolver
    elif isinstance(mensagem, list):
        vencedor = mensagem[0].split()[0]
        resposta = mensagem[1]['text']
    return {'vencedor': vencedor, 'resposta': resposta}


def parser(mensagem):
    '''lê a mensagem e a interpreta "o que está acontecendo", retornando uma 
    namedtuple com as informações relevantes'''
    
    if mensagem[:36] == 'All answers received! The honourable':
        dados = rodada(recebida=True, **parser_alternativas(mensagem))

    # as mensagens de resultado contêm texto bold, então são listas
    # e o nome do vencedor deve estar no primeiro elemento
    elif 'wins a point!' in mensagem[0] or 'wins a point!' in mensagem:
        dados = rodada(finalizada=True, **parser_resultados(mensagem))
    else:
        dados = rodada()
    return dados
        

def combina_dados(rodada1, rodada2):
    atributos = []
    for a, b in zip(rodada1, rodada2):
        if (any((a,b)) and not all((a,b))) or a==b:
            atributos.append(a or b)
        else:
            raise ValueError('rodadas têm elementos conflitantes!')
    return rodada(*atributos)
        

def crawler(mensagens):
    '''lê as mensagens em "mensagens" e registra qual czar deu vitória a que
    respondente; retorna um histórico dos czares e vencedores, e a lista dos
    participantes'''
    histórico = [] # lista de tuplas contendo (czar, vencedor) pra cada rodada
    jogadores = [] # lista dos que mandaram ao menos uma carta ou foram czar
    for i, mensagem in enumerate(mensagens):
        rodada_A = parser(mensagem)
        if rodada_A.recebida:
            czar = rodada_A.czar
            if czar not in jogadores:
                jogadores.append(czar)
            for j, resultado in enumerate(mensagens[i+1:]):
                rodada_B = parser(resultado)
                if rodada_B.recebida:
                    break # chegamos ao início da próxima pergunta
                elif rodada_B.finalizada:
                    vencedor = rodada_B.vencedor
                    if vencedor == czar:
                        print(f'Erro! Vencedor {vencedor} é o mesmo que o czar {czar}\n'
                              f'Ganhou para pergunta número {i}: \n\n {mensagem}\n\n\n\n'
                              f'Com a resposta \n\n {resultado}')
                        break
                    if vencedor not in jogadores:
                        jogadores.append(vencedor)
                    dados_rodada = combina_dados(rodada_A, rodada_B)
                    histórico.append(dados_rodada)
                    break
    return histórico, jogadores


def conta(histórico, jogadores):
    ''' retorna um dicionário de czares, contendo Counters com suas escolhas.
    Czares que não escolheram estão nas keys do dicionário, mas jogadores que
    não foram escolhidos não aparecem nos Counters'''
    czares = dict()
    for rodada in histórico:
        escolhidos = czares.get(rodada.czar, [])
        escolhidos.append(rodada.vencedor)
        czares.setdefault(rodada.czar, escolhidos)
        
    contagem_desordenada = {czar: Counter(escolhas) for czar, escolhas in czares.items()}
    não_czares = [jogador for jogador in jogadores if jogador not in czares]
    contagem_desordenada.update({não_czar: {} for não_czar in não_czares})
    
    # ordenaremos a contagem_desordenada
    contagem = {czar: dict(sorted(escolhas.items(), 
                                  key=lambda x: list(contagem_desordenada).index(x[0])))
                for czar, escolhas in contagem_desordenada.items()}
    return contagem
    

def plot_chances(contagem, normalizar=True):
    # remove czares que não jogaram e completa com zero jogadores faltantes em cada czar
    dados = {czar: {jog: contagem[czar].get(jog, 0) for jog in contagem if jog!=czar}
                 for czar in contagem if contagem[czar]}
    if normalizar:
        for czar in dados:
            N = max(1, sum(dados[czar].values()))
            dados[czar] = {jog: val/N for jog, val in dados[czar].items()}
    
    # plot "vazio", só para inicializar o primeiro nome no eixo x e garantir o 
    # bom-ordenamento
    primeiro = list(dados.keys())[0]
    plt.plot([primeiro], [None], color='k')

    for czar, escolhas in dados.items():
        pontos = list(zip(*escolhas.items()))
        plt.plot(*pontos, 'o:', label=czar)
        
    plt.title('Escolhas de cada czar' + normalizar*' (normalizadas)')
    plt.ylabel('Chance de ser escolhido')
    plt.xlabel('Autor da resposta')
    plt.xticks(rotation=45)
    plt.legend(fontsize='x-small')
    plt.show()


# Faz um heat map 2D das escolhas que cada czar (eixo y) fez de cada jogador (eixo x)
# Tutorial usado: https://www.pythonpool.com/matplotlib-heatmap/
def plot_heatmap(contagem, normalizar=True):
    czares = [czar for czar in contagem.keys() if contagem[czar]]
    matriz_escolhas = [[contagem[czar].get(jog, 0) for jog in contagem] 
                       for czar in czares]
    if normalizar:
        for czar in range(len(matriz_escolhas)):
            N = max(1, sum(matriz_escolhas[czar]))
            matriz_escolhas[czar] = [i/N for i in matriz_escolhas[czar]]
    plt.xticks(ticks=range(len(contagem)), labels=contagem.keys(), rotation=90)
    plt.yticks(ticks=range(len(czares)), labels=czares)
    plt.title('Escolhas de cada czar' + normalizar*' (normalizadas)')
    plt.xlabel('Autor da resposta')
    plt.ylabel('Czar')
    heatmap = plt.imshow(matriz_escolhas, cmap='Blues', interpolation='nearest')
    plt.colorbar(heatmap)
    plt.show()


def main():
    histórico, jogadores = crawler(mensagens)
    contagem = conta(histórico, jogadores)
        
    plot_chances(contagem, normalizar=True)
    plot_heatmap(contagem, normalizar=True)


if __name__=="__main__":
    main()