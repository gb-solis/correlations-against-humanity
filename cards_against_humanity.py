# =============================================================================
# TODO:
#   fazer gif cronológico do histograma
#   ver como cada czar se diferencia da média para cada respondente, em desvios-padrão
#   plotar melhor os dados
#   mostrar quem mais atrasa (print('leonardo e thomas'))
#   levar em conta que certos jogadores estavam ausentes (como?)
# =============================================================================

import json
from collections import Counter, namedtuple
from matplotlib import pyplot as plt
import numpy as np
from scipy.interpolate import pchip_interpolate

verbose = False

# Print only if verbose is True
def printv(*args, **kwargs):
    if verbose: print(*args, **kwargs)


# objeto que representa uma rodada
Rodada = namedtuple('Rodada',
                    ('czar', 'vencedor', 'pergunta', 'resposta', 'alternativas',
                     'recebida', 'finalizada'),
                    defaults=(None, None, None, None, None, False, False))


def abre_dados(path):
    with open(path, 'r', encoding='utf8') as file:
        dados = json.load(file)
    # queremos analisar mensagens do bot
    mensagens_bot = [msg['text'] for msg in dados['messages'] 
                     if msg['type']=='message' 
                     and msg['from']=='Chat Against Humanity']
    # separar as mensagens em jogos
    jogos = [[]]
    for msg in mensagens_bot:
        # msg de início contém texto formatado, então é uma lista
        if 'is starting a new game of xyzzy!' in msg[0]:
            jogos.append([msg])
        else:
            jogos[-1].append(msg)
    return jogos


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
        dados = Rodada(recebida=True, **parser_alternativas(mensagem))
    # as mensagens de resultado contêm texto bold, então são listas
    elif 'wins a point!' in mensagem[0] or 'wins a point!' in mensagem:
        dados = Rodada(finalizada=True, **parser_resultados(mensagem))
    else:
        dados = Rodada()
    return dados


def combina_dados(rodada1, rodada2):
    '''combina os dados de duas namedtuples, dando erro se forem inconsistentes'''
    atributos = []
    for a, b in zip(rodada1, rodada2):
        if (any((a,b)) and not all((a,b))) or a==b:
            atributos.append(a or b)
        else:
            raise ValueError('rodadas têm elementos conflitantes!')
    return Rodada(*atributos)


def crawler(mensagens):
    '''lê as mensagens em "mensagens" e registra qual czar deu vitória a que
    respondente; retorna um histórico dos czares e vencedores, e a lista dos
    participantes'''
    histórico = [] # lista de tuplas contendo informações sobre cada rodada
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
                        printv(f'Erro! Vencedor {vencedor} é também o czar\n'
                                f'Ganhou para pergunta número {i}: \n\n'
                                f'{mensagem}\n\n\n\n'
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


class CAH:
    def __init__(self, jogo):
        self.jogo = jogo
        self.histórico, self.jogadores = crawler(jogo)
        self.contagem = conta(self.histórico, self.jogadores)
    
    
    def __repr__(self):
        return f'Jogo de {len(self.jogo)} rodadas, iniciado em dd/mm/yy, '\
               f'entre {sorted(self.jogadores)}'
               
    
    def não_vazio(método):
        '''decorator pra evitar que rodemos funções em jogos vazios'''
        def método_corrigido(self, *args, **kwargs):
            if not self.histórico:
                print(f'Jogo vazio! Não posso {método.__name__}. ({self})')
                return
            else:
                return método(self, *args, **kwargs)
        return método_corrigido
            
        
    @não_vazio
    def plot_chances(self, normalizar=True):
        # remove czares que não jogaram e completa com zero jogadores faltantes
        # em cada czar
        dados = {czar: {jog: self.contagem[czar].get(jog, 0) 
                        for jog in self.contagem if jog!=czar}
                 for czar in self.contagem if self.contagem[czar]}
        if normalizar:
            for czar in dados:
                N = max(1, sum(dados[czar].values()))
                dados[czar] = {jog: val/N for jog, val in dados[czar].items()}

        # plot "vazio", só para inicializar o primeiro nome no eixo x e 
        # garantir o bom-ordenamento
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

    @não_vazio
    # Tutorial usado: https://www.pythonpool.com/matplotlib-heatmap/
    def plot_heatmap(self, normalizar=True):
        '''Faz um heat map 2D das escolhas que cada czar (eixo y) fez de cada 
        jogador (eixo x)'''
        czares = [czar for czar in self.contagem.keys() if self.contagem[czar]]
        matriz_escolhas = [[self.contagem[czar].get(jog, 0) for jog in self.contagem]
                           for czar in czares]
        if normalizar:
            for czar in range(len(matriz_escolhas)):
                N = max(1, sum(matriz_escolhas[czar]))
                matriz_escolhas[czar] = [i/N for i in matriz_escolhas[czar]]
        plt.xticks(ticks=range(len(self.contagem)), labels=self.contagem.keys(), rotation=90)
        plt.yticks(ticks=range(len(czares)), labels=czares)
        plt.title('Escolhas de cada czar' + normalizar*' (normalizadas)')
        plt.xlabel('Autor da resposta')
        plt.ylabel('Czar')
        
        if normalizar:
            heatmap = plt.imshow(matriz_escolhas, cmap='Blues', interpolation='nearest')
            plt.colorbar(heatmap)
        else:
            n_max = max(max(i) for i in matriz_escolhas)
            cmap = plt.cm.get_cmap('Blues')#, n_max+1)
            heatmap = plt.imshow(matriz_escolhas, cmap=cmap, interpolation='nearest')
            plt.colorbar(heatmap, format='%d', ticks=range(n_max+1))
        plt.show()

    
    @não_vazio
    def plot_histórico(self, espalhar=True, suavizar=True):
        '''plota o histórico de pontos de cada jogador'''
        
        deltaV = 0.07 # Valor mágico
        # Se temos n pontos de mesmo valor, espalhamos o valor para melhor visualização
        def espalhar_pontos(valor, n):
            return np.linspace(valor+(n-1)*deltaV/2, valor-(n-1)*deltaV/2, n)

        # Interpolar dados com Bspline (300 pontos) em vez de linhas retas
        def suavizar(x, y):
            xsuave = np.linspace(x.min(), x.max(), len(x)*10)
            ysuave= pchip_interpolate(x, y, xsuave)
            return xsuave, ysuave

        vitórias = {jogador: [1 if jogador==rodada.vencedor else 0
                              for rodada in self.histórico] 
                    for jogador in self.jogadores}
        curvas = []
        for jogador, lista in vitórias.items():
            soma = 0
            curva = [0] + [(soma:=soma+venceu) for venceu in lista]
            curvas.append(curva)
        curvasTarr = np.transpose(np.array(curvas, dtype=float))
        if espalhar:
            for rodada in curvasTarr:
                pontosDict = {}
                for ind, ponto in enumerate(rodada):
                    if ponto in pontosDict:
                        pontosDict[ponto].append(ind)
                    else:
                        pontosDict[ponto] = [ind]
                for valor in pontosDict:
                    inds = pontosDict[valor]
                    rodada[inds] = espalhar_pontos(valor, len(inds))
        plt.plot(curvasTarr, '.')
        if suavizar:
            plt.plot(*suavizar(np.arange(0,len(curvasTarr)), curvasTarr), '-')
        else:
            plt.plot(curvasTarr, '-')
        plt.title('Histórico de pontos')
        plt.legend(self.jogadores, fontsize='x-small')
        plt.xlabel('Rodada')
        plt.ylabel('Pontos')
        plt.show()

    
    @não_vazio
    def plot_histórico_percent(self):
        vitórias = {jogador: [1 if jogador==rodada.vencedor else 0
                              for rodada in self.histórico] for jogador in self.jogadores}
        curvas = []
        for jogador, lista in vitórias.items():
            soma = 0
            curva = [0] + [(soma:=soma+venceu) for venceu in lista]
            curvas.append(curva)
        pesos = [sum([curva[i] for curva in curvas]) for i in range(len(curvas[0]))]
        curvas = [[curva[i]/max(pesos[i],1) for i in range(len(curva))] for curva in curvas]
        plt.stackplot(range(len(curva)), curvas, label=jogador)
        plt.title('Histórico percentual de vitórias')
        plt.xlabel('Rodada')
        plt.ylabel('Vitórias (%)')
        plt.show()

    
    @não_vazio
    def plot_distribuição_pontos(self):
        pontos_finais = Counter(rodada.vencedor for rodada in self.histórico)
        jogadores, pontos = zip(*pontos_finais.most_common())
        plt.plot(jogadores, pontos, 'o-')
        plt.title('Distribuição final de pontos')
        plt.ylabel('Pontos')
        plt.xticks(rotation=45)
        plt.show()


def abre_CAHs(path):
    return list(map(lambda jogo: CAH(jogo), abre_dados(path)))


def main():
    path = 'result.json'

    cahs = abre_CAHs(path)
    último_cah = cahs[1]
    
    último_cah.plot_chances(normalizar=False)
    último_cah.plot_heatmap(normalizar=False)
    último_cah.plot_histórico(suavizar=False)
    último_cah.plot_distribuição_pontos()


if __name__=="__main__":
    main()
