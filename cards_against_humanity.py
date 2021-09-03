# =============================================================================
# TODO:
#   fazer gif cronológico do histograma
#   ver como cada czar se diferencia da média para cada respondente, em desvios-padrão
#   plotar melhor os dados
#   mostrar quem mais atrasa (print('leonardo e thomas'))
#   levar em conta que certos jogadores estavam ausentes (como?)
# =============================================================================

import json
from collections import Counter
from matplotlib import pyplot as plt
import numpy as np
from scipy.interpolate import pchip_interpolate
from datetime import datetime

verbose = False

# Print only if verbose is True
def printv(*args, **kwargs):
    if verbose: print(*args, **kwargs)


def abre_dados(path):
    with open(path, 'r', encoding='utf8') as file:
        dados = json.load(file)
    # queremos analisar mensagens do bot
    mensagens_bot = [msg for msg in dados['messages'] 
                     if msg['type']=='message' 
                     and msg['from']=='Chat Against Humanity']
    # separar as mensagens em jogos
    jogos = [[]]
    for msg in mensagens_bot:
        # msg de início contém texto formatado, então é uma lista
        if 'is starting a new game of xyzzy!' in msg['text'][0]:
            jogos.append([msg])
        else:
            jogos[-1].append(msg)
    return jogos


class Rodada:
    def __init__(self, czar=None, vencedor=None, pergunta=None, resposta=None,
                 alternativas=None, altera_pontos=None, data_recebida=None, 
                 data_finalizada=None):
                 
        self.czar = czar
        self.vencedor = vencedor
        self.pergunta = pergunta
        self.resposta = resposta
        self.alternativas = alternativas
        self.altera_pontos = altera_pontos
        self.data_recebida = data_recebida
        self.data_finalizada = data_finalizada
        # self.recebida = False
        # self.finalizada = False
    
    @property
    def recebida(self):
        return bool(self.data_recebida)
    
    @property
    def finalizada(self):
        return bool(self.data_finalizada)
    
    @classmethod
    def from_dict(cls, dict_):
        return parser(dict_)
    
    def __repr__(self):
        czar, vencedor = self.czar, self.vencedor
        pergunta, resposta = self.pergunta, self.resposta
        return f'Rodada({czar=}, {vencedor=}, {pergunta=}, {resposta=})'
    
    def __iter__(self):
        for valor in self.__dict__.values():
            yield valor
    
    def __add__(self, outro):
        args = []
        for a,b in zip(self, outro):
            if not all((a,b)) or a==b:
                args.append(a or b)
            else:
                raise ValueError('Rodadas têm elementos conflitantes')
        return Rodada(*args)
        
    def copy(self):
        return Rodada(*self)
    
    def replace(self, **kwargs):
        novos_kw = {**self.__dict__, **kwargs}
        return Rodada(**novos_kw)


def parser_alternativas(mensagem):
    '''parser para mensagens do tipo "All answers received"'''
    if isinstance(mensagem, str):
        início, fim = mensagem.split('\n\n')
        czar = início.split()[5]
        pergunta = início.splitlines()[1][10:]
        alternativas = fim.split('\n  - ')
        alternativas[0] = alternativas[0][4:]
        return {'czar': czar, 'pergunta': pergunta, 'alternativas': alternativas}
    elif isinstance(mensagem, list):
        czar = mensagem[0].split()[5]
        pergunta = None # TODO
        alternativas = None # TODO
        return {'czar': czar}


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


def parser_altera_pontos(mensagem):
    '''parser para quando pontos de jogadores são manualmente alterados.
    Altera os pontos do jogador'''
    jogador = mensagem[0][len('Player  '):].split()[0]
    pontos = int(mensagem[-1].split()[-1])
    # guardar o nome em "altera_pontos"
    return {'altera_pontos': jogador}
    

def parser(mensagem):
    '''lê a mensagem e a interpreta "o que está acontecendo", retornando uma
    Rodada com as informações relevantes'''
    
    texto = mensagem['text']
    data = datetime.fromisoformat(mensagem['date'])
    
    if texto[:36] == 'All answers received! The honourable' or \
       texto[0][:36] == 'All answers received! The honourable':
        dados = parser_alternativas(texto)
        metadados = {'data_recebida': data}
    # as mensagens de resultado contêm texto bold, então são listas
    elif 'wins a point!' in texto[0] or 'wins a point!' in texto:
        dados = parser_resultados(texto)
        metadados = {'data_finalizada': data}
    elif "'s score has been changed" in texto[2]:
        dados = parser_altera_pontos(texto)
        metadados = dict()
    else:
        dados = metadados = dict()
        
    return Rodada(**dados, **metadados)



def altera_pontos(altera_A, altera_B, histórico):
    '''Altera os pontos dos jogadores A e B. Assume que apenas um ponto é
    passado, daquele dentre os dois que por último venceu, para o outro.'''
    if altera_A.altera_pontos == altera_B.altera_pontos:
        printv(f'Pontos foram alterados de {altera_A.altera_pontos} duas vezes '
                'seguidas, sem tirar de mais ninguém. Não sei lidar com isso ainda')
    else:
        for i, rodada in enumerate(reversed(histórico)):
            candidatos = {altera_A.altera_pontos, altera_B.altera_pontos}
            if rodada.vencedor in candidatos:
                candidatos.remove(rodada.vencedor)
                novo_vencedor = candidatos.pop()
                rodada_corrigida = rodada.replace(vencedor=novo_vencedor)
                break
        histórico[-(i+1)] = rodada_corrigida


def crawler(mensagens):
    '''lê as mensagens em "mensagens" e registra qual czar deu vitória a que
    respondente; retorna um histórico dos czares e vencedores, e a lista dos
    participantes'''
    histórico = [] # lista de tuplas contendo informações sobre cada rodada
    jogadores = [] # lista dos que mandaram ao menos uma carta ou foram czar
    
    rodada_A = rodada_B = None
    altera_A = altera_B = None
    
    for mensagem in mensagens:
        rodada = parser(mensagem)
        # se é do tipo "all answers received!"
        if rodada.recebida:
            rodada_A = rodada
        # se é do tipo "X wins a point!"
        elif rodada.finalizada and rodada_A is not None:
            rodada_B = rodada
            czar, vencedor = rodada_A.czar, rodada_B.vencedor
            if czar != vencedor:
                # dados_rodada = combina_dados(rodada_A, rodada_B)
                dados_rodada = rodada_A + rodada_B
                histórico.append(dados_rodada)
                jogadores.extend(jog for jog in (czar, vencedor) 
                                 if jog not in jogadores)       
                rodada_A = rodada_B = None
            else:
                printv(f'Erro! Vencedor {vencedor} é também o czar. Descartei')
        # se está alterando os pontos de um jogador manualmente
        elif rodada.altera_pontos:
            if altera_A is None:
                altera_A = rodada
            else:
                altera_B = rodada
                altera_pontos(altera_A, altera_B, histórico)
                altera_A = altera_B = None
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


class Partida:
    def __init__(self, jogo):
        self.jogo = jogo
        self.histórico, self.jogadores = crawler(jogo)
        self.contagem = conta(self.histórico, self.jogadores)
    
    
    def __repr__(self):
        return f'Jogo de {len(self.jogo)} rodadas, iniciado em dd/mm/yy, '\
               f'entre {sorted(self.jogadores)}'
               
               
    def __add__(self, outro):
        jogo = self.jogo.copy()
        jogo.extend(outro.jogo)
        return Partida(jogo)
               
    
    @classmethod
    def from_json(cls, path):
        '''ler jogos direto de arquivo localizado em path'''
        return list(map(cls, abre_dados(path)))
    
    
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
    def plot_heatmap(self, normalizar=True, salvar=False):
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
        if salvar: plt.savefig('heatmap.png', dpi=320, bbox_inches='tight')
        plt.show()

    
    @não_vazio
    def plot_histórico(self, espalhar=True, suavizar=True, mostrar_pontos=False, salvar=False):
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
        if mostrar_pontos:
            plt.plot(curvasTarr, '.')
        if suavizar:
            plt.plot(*suavizar(np.arange(0,len(curvasTarr)), curvasTarr), '-')
        else:
            plt.plot(curvasTarr, '-')
        plt.title('Histórico de pontos')
        plt.legend(self.jogadores, fontsize='x-small')
        plt.xlabel('Rodada')
        plt.ylabel('Pontos')
        if salvar: plt.savefig('histórico de pontos.png', dpi=320)
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


    @não_vazio
    def horários(self, tipo='respostas'):
        if tipo in self.jogadores:
            horas = [rodada.data_finalizada.hour for rodada in self.histórico 
                     if rodada.czar==tipo]
        elif tipo=='respostas':
            horas = [rodada.data_recebida.hour for rodada in self.histórico]
        elif tipo=='czares':
            horas = [rodada.data_finalizada.hour for rodada in self.histórico]
        elif tipo=='grupo':
            horas = [rodada.data_recebida.hour for rodada in self.histórico] \
                    + [rodada.data_finalizada.hour for rodada in self.histórico]
        else:
            raise ValueError('Esse não é um nome ou categoria válido')
        
        barras, _ = np.histogram(horas, bins=24, range=(0,24), density=True)
        
        plt.subplot(projection='polar')
        cmap = plt.get_cmap('inferno')
        cores = [cmap((i/11)) for i in range(12)] \
                + [cmap(1.1-i/10) for i in range(1,13)]
        
        plt.bar([-np.pi/2 - np.pi/12*i for i in range(1,25)], height=barras, 
                width=0.9*(np.pi/12), bottom=0.05, align='edge', color=cores)
        plt.title(f'Atividade de {tipo}')
        plt.xticks([np.pi/6 + np.pi/3*i for i in range(6)],
                   labels=['16:00', '12:00', '8:00', '4:00', '0:00', '20:00'])
        plt.yticks(np.linspace(0.05, 0.05+max(barras), 5), labels=[])
        plt.grid(alpha=0.2)
        plt.show()


    def demora(self):
        from matplotlib.colors import LogNorm
        czar2num = dict(zip(self.jogadores, range(len(self.jogadores))))
        tempos = []
        czares = []
        for rodada in self.histórico:
            delta = rodada.data_finalizada - rodada.data_recebida
            delta = delta.seconds/3600
            if delta > 12:
                print(rodada)
            num = czar2num[rodada.czar]
            tempos.append(delta)
            czares.append(num)
        
        cores = plt.get_cmap('plasma')
        hist = plt.hist2d(czares, tempos, bins=(10, 13), cmin=1, cmap=cores,
                   range=((0,10),(0,13)), norm=LogNorm())
        plt.colorbar(hist[3])
        plt.title('Tempo de escolha por czar')
        plt.ylabel('Tempo até escolher (horas)')
        plt.xticks(range(10), labels='', rotation=45)
        
        
        ax = plt.gca()
        # Customize minor tick labels
        ax.set_xticks([i+0.5 for i in range(10)], minor=True)
        ax.set_xticklabels(self.jogadores, minor=True, rotation=45)
        
        for tick in ax.xaxis.get_minor_ticks():
            tick.tick1line.set_markersize(0)
            tick.tick2line.set_markersize(0)
        plt.show()

    
def main():
    path = 'result.json'

    cahs = Partida.from_json(path)
    último_cah = cahs[-1]
    todos = sum(cahs, start=Partida([]))
    
    último_cah.plot_chances(normalizar=False)
    último_cah.plot_heatmap(normalizar=False, salvar=False)
    último_cah.plot_histórico(suavizar=False, salvar=False)
    último_cah.plot_distribuição_pontos()
    último_cah.horários('grupo')
    último_cah.demora()
    

if __name__=="__main__":
    main()
