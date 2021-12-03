# =============================================================================
# TODO:
#   fazer gif cronológico do histograma
#   ver como cada czar se diferencia da média para cada respondente, em desvios-padrão
#   plotar melhor os dados
#   mostrar quem mais atrasa (print('leonardo e thomas'))
#   levar em conta que certos jogadores estavam ausentes (como?)
# =============================================================================
'''
TODO: transição para objetos

[ ] criar lista "definitiva" do que ocorreu;

    [X] obter lista de objetos-mensagem "literais" do bot
    
    [ ] pensar arquitetura dos dados...
        vou criar uma lista de objetos-rodada?
        e depois, como cada função usa e extrai os dados?
        acho que os delta-pontos são os mais úteis
        
    [/] passar tudo pra deltas?
    
    [/] contabilizar mudanças de pontos
        [X] contar pontos absolutos pré-mudança
        [X] contabilizar mudanças de ponto em um só jogo
        [/] transformar em deltas 
        [X] combinar mudanças de pontos entre jogos
        [/] lidar com mudanças múltiplas seguidas
        
    [ ] estabelecer vencedores por rodada
        [ ] adicionar vencedores extra?
            [ ] checar se resposta daquele cujos pontos estão sendo alterados
                é semelhante à resposta vencedora...? usando fuzzy string matching?
            [ ] alternativamente, criar na mão uma lista dos ids das rodadas
                que tiveram mais de um vencedor; uma lista de ids de mensagens
                bugadas talvez tenha que ser criada também, eventualmente
        [ ] trocar vencedores errôneos: se o vencedor da última rodada tiver seus
            pontos diminuídos de 1 e os outra pessoa +1, assumir vencedor errôneo
            
'''
import json
from collections import Counter
from matplotlib import pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.ticker import MaxNLocator
import numpy as np
from scipy.interpolate import pchip_interpolate
from itertools import accumulate, chain

from classes import (Mensagem, AlteraPonto, Recebida, Finalizada, Rodada,
                     PerdePonto, Atraso, HurryUp, HurryJudge, Entrou, Início)

verbose = False

######################### Funções utilidade ###################################


# Print only if verbose is True
def printv(*args, **kwargs):
    if verbose: print(*args, **kwargs)


def formata_nomes(nomes, tipo='formal'):
    def formata(nome):
        partes = nome.split()
        if len(partes)==1:
            return nome
        else:
            if tipo=='formal': return f'{partes[0][0]}. {partes[-1]}'
            elif tipo=='informal': return partes[0]
    return list(map(formata, nomes))


########################### Funções auxiliares ################################


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


def parser(mensagem):
    '''lê a mensagem e a interpreta "o que está acontecendo", retornando uma
    Mensagem com as informações relevantes'''
    
    texto = mensagem['text']
    
    if texto[:36] == 'All answers received! The honourable' or \
    texto[0][:36] == 'All answers received! The honourable':
        evento = Recebida
    elif 'wins a point!' in texto[0] or 'wins a point!' in texto:
        evento = Finalizada
    elif "'s score has been changed" in texto or \
    "'s score has been changed" in texto[2]:
        evento = AlteraPonto
    elif 'Judge was too slow,' in texto[0]:
        evento = PerdePonto
    elif 'to hurry up! Tick-tock...' in texto[-1] or \
    'to hurry up! Tick-tock...' in texto:
        evento = HurryUp
    elif 'can suck it for not answering in time:' in texto[-1] or \
    'can suck it for not answering in time:' in texto:
        evento = Atraso
    elif 'Judgy Judgerson!' in texto[0] or 'Judgy Judgerson!' in texto:
        evento = HurryJudge
    elif 'has joined the game' in texto:
        evento = Entrou
    elif 'is starting a new game of xyzzy!' in texto[0]:
        evento = Início
    else:
        evento = Mensagem

    return evento.from_dict(mensagem)


def crawler(mensagens):
    ata = [] # lista dos eventos ocorridos
    jogadores = [] # lista dos participantes
    recebida = finalizada = None # rodada é composta pelo par recebida + finalizada
    for evento in map(parser, mensagens):
        if isinstance(evento, Recebida):
            recebida = evento
        elif isinstance(evento, Finalizada) and recebida is not None: 
            finalizada = evento
            if recebida.czar != finalizada.vencedor:
                rodada = Rodada.from_pair(recebida, finalizada)
                ata.append(rodada)
                recebida = finalizada = None
            else:
                printv(f'Erro! Vencedor {finalizada.vencedor} é também o czar.'
                       ' Descartei')
        elif isinstance(evento, (Início, Entrou)):
            if evento.jogador not in jogadores:
                jogadores.append(evento.jogador)
            ata.append(evento)
        else:
            ata.append(evento)
    return ata, jogadores


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


######################### Classe partida ######################################


class Partida:
    def __init__(self, jogo):
        self.jogo = jogo
        self.ata, self.jogadores = crawler(jogo)
        self.histórico = [rod for rod in self.ata if isinstance(rod, Rodada)]
        self.contagem = conta(self.histórico, self.jogadores)
        self.pontos = self.pontos_()
        self.vitórias = self.vitórias_()
    
    def __repr__(self):
        return f'Jogo de {len(self.jogo)} rodadas, iniciado em dd/mm/yy, '\
               f'entre {self.jogadores}'
               
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
    
    ############################# Métodos #####################################
    
    def pontos_(self):
        '''corrige a pontuação baseado nas mudanças de ponto'''
        dados = dict.fromkeys(self.jogadores, [0])
        for evento in self.ata:
            if isinstance(evento, Início):
                pts_início = {jog: val[-1] for jog, val in dados.items()}
            if isinstance(evento, Rodada):
                dados = {jogador: pontos + [(pontos[-1] or 0)]
                         for jogador, pontos in dados.items()}
                dados[evento.vencedor][-1] += 1
            if isinstance(evento, AlteraPonto):
                pontos_atuais = dados[evento.jogador][-1] - pts_início[evento.jogador]
                delta_pontos = evento.pontos - pontos_atuais
                evento.delta = delta_pontos
                dados[evento.jogador][-1] += delta_pontos
            if isinstance(evento, PerdePonto):
                # dados = {jog: pts + [(pts[-1] or 0)] for jog, pts in dados.items()}
                dados[evento.czar][-1] -= 1
        return {jogador: pontos for jogador, pontos in dados.items()}
    
    
    def vitórias_(self):
        pontos = self.pontos_()
        def diff_segura(a,b):
            if a is None and b is None:
                return None
            elif None in (a,b):
                return a or b
            else:
                return a - b
        vits = {jog: [diff_segura(pts[i], pts[i-1]) for i in range(1,len(pts))] 
                for jog, pts in pontos.items()}
        return vits    
    
    
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


    # Tutorial usado: https://www.pythonpool.com/matplotlib-heatmap/
    @não_vazio
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
        
        plt.xticks(ticks=range(len(self.contagem)), labels=formata_nomes(self.contagem.keys()), rotation=90)
        plt.yticks(ticks=range(len(czares)), labels=formata_nomes(czares))
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
    
    
    def matrizes_preferências(self):
        n = len(self.jogadores)
        brutos = []
        preferências = []
        n_escolhas_czar = np.zeros((n,))
        n_jogos_jogador = np.zeros((n,))
        matriz = np.zeros((n,n))
        for i, rodada in enumerate(self.histórico):
            N = len(rodada.jogadores)
            i_czar = self.jogadores.index(rodada.czar)
            n_escolhas_czar[i_czar] += 1
            for jogador, vitórias in self.vitórias.items():
                i_jog = self.jogadores.index(jogador)
                n_jogos_jogador[i_jog] += 1
                vit = vitórias[i]
                matriz[i_czar][i_jog] += N*vit
            brutos.append(matriz.copy())
            matriz_peso = matriz.copy()
            matriz_peso = np.divide(matriz_peso, np.maximum(n_escolhas_czar,1)[np.newaxis].T)
            matriz_peso = np.divide(matriz_peso, np.maximum(n_jogos_jogador, 1))
            preferências.append(matriz_peso)
        return preferências, brutos
    
    
    def plota_preferências(self, matriz, i):
        jogadores = self.jogadores
        plt.xticks(ticks=range(len(matriz)), labels=formata_nomes(jogadores), rotation=90)
        plt.yticks(ticks=range(len(matriz)), labels=formata_nomes(jogadores))
        plt.title('Escolhas de cada czar (normalizadas)')
        plt.xlabel('Autor da resposta')
        plt.ylabel('Czar')
        
        n_max = max(max(i) for i in matriz)
        cmap = plt.cm.get_cmap('Blues')#, n_max+1)
        heatmap = plt.imshow(matriz, cmap=cmap, interpolation='nearest')#, norm=LogNorm())
        plt.colorbar(heatmap)
        # if salvar: 
        plt.savefig(f'heatmap_{i}.png', dpi=320, bbox_inches='tight')
        plt.show()
    
    
    @não_vazio
    def plot_histórico(self, espalhar=True, suavizar=True, mostrar_pontos=False,
                       salvar=False, normalizar=False, bokeh=False):
        '''plota o histórico de pontos de cada jogador'''
        
        deltaV = 0.07 if not normalizar else 0.01 # Valor mágico
        # Se temos n pontos de mesmo valor, espalhamos o valor para melhor visualização
        def espalhar_pontos(valor, n):
            return np.linspace(valor+(n-1)*deltaV/2, valor-(n-1)*deltaV/2, n)

        # Interpolar dados com Bspline (300 pontos) em vez de linhas retas
        def suaviza(x, y):
            xsuave = np.linspace(x.min(), x.max(), len(x)*10)
            ysuave= pchip_interpolate(x, y, xsuave)
            return xsuave, ysuave
        
        def bokeh_plot(dados, salvar=False, mostrar=True):
            from bokeh.plotting import figure, output_file, save
            from bokeh.io import show
            from bokeh.palettes import Spectral10 as cor
            from bokeh.models import HoverTool
            X = dados[0]
            p = figure(width=1000, height=700, title='Histórico de Pontos')
            p.xaxis.axis_label = 'Rodada'
            p.yaxis.axis_label = 'Pontos'
            
            for n, Y in enumerate(dados[1].transpose()):
                plot = p.line(X, Y, 
                              line_width=2.5,
                              line_color=cor[n],
                              name=self.jogadores[n],
                              legend_label=self.jogadores[n])
            p.add_tools(HoverTool(tooltips='$name',))
            
            p.multi_line([X]*10, list(dados[1].transpose()),
                          line_width=2.5,
                          line_color=cor,
                          nonselection_alpha=0.2,
                          hover_line_color='black',
                          hover_line_width=4)
            # p.legend.location = "bottom_left"
            p.add_layout(p.legend[0], 'left')
            # p.legend.click_policy="hide"
            if salvar:
                output_file('pontos.html')
                save(p)
            if mostrar:
                show(p)

        curvas = []
        for jogador, pontos in self.vitórias.items():
            lista = pontos
            curva = list(accumulate(lista, initial=0))
            if normalizar:
                jogou = [0] + [1 if jogador in rodada.jogadores #and jogador not in rodada.chumps
                         else 0 for rodada in self.histórico]
                pesos = [len(rod.jogadores) for rod in self.histórico]
                curva = list(accumulate([i*p for i,p in zip(lista, pesos)], initial=0))
                n_jogos = list(accumulate(jogou))
                curva = [1 if (vit,jog)==(0,0) else vit/max(1,jog) for vit, jog in zip(curva, n_jogos)]
                curva = [2*i/(i+1)-1 for i in curva]
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
            dados = suaviza(np.arange(0,len(curvasTarr)), curvasTarr)
            plt.plot(*dados, '-')
            if bokeh: bokeh_plot(dados)
            
        else:
            plt.plot(curvasTarr, '-')
            if bokeh: bokeh_plot(curvasTarr)
        plt.title('Histórico de pontos' + normalizar*' (normalizado)')
        plt.legend(formata_nomes(self.jogadores), fontsize='x-small')
        plt.xlabel('Rodada')
        plt.ylabel('Pontos' if not normalizar else 'coeficiente de vitórias')
        if salvar: plt.savefig('histórico de pontos.png', dpi=320)
        plt.show()

    
    @não_vazio
    def plot_distribuição_pontos(self, salvar=False):
        # pontos_finais = Counter(rodada.vencedor for rodada in self.histórico)
        pontos_finais = {jog: pontos[-1] for jog, pontos in self.pontos.items()}
        # jogadores, pontos = zip(*pontos_finais.most_common())
        jogadores, pontos = zip(*sorted(pontos_finais.items(), 
                                        key=lambda d: d[1], reverse=True))
        plt.plot(formata_nomes(jogadores), pontos, 'o-')
        plt.title('Distribuição final de pontos')
        plt.ylabel('Pontos')
        plt.xticks(rotation=45)
        if salvar: plt.savefig('distribuição_pontos.png', dpi=320, bbox_inches='tight')
        plt.show()


    @não_vazio
    def horários(self, tipo='grupo', salvar=False):
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
            raise ValueError(f'"{tipo}" não é um nome ou categoria válido')
        
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
        if salvar: 
            plt.savefig('horários.png', dpi=320, bbox_inches='tight')
        plt.show()

    
    @não_vazio
    def demora(self, salvar=False):
        czar2num = dict(zip(self.jogadores, range(len(self.jogadores))))
        tempos = []
        czares = []
        for rodada in self.histórico:
            delta = rodada.data_finalizada - rodada.data_recebida
            delta = delta.seconds/3600
            num = czar2num[rodada.czar]
            tempos.append(delta)
            czares.append(num)
        
        cores = plt.get_cmap('plasma')
        hist = plt.hist2d(czares, tempos, bins=(10, 13), cmin=1, cmap=cores,
                          range=((0,10),(0,13)), norm=LogNorm())

        plt.colorbar(hist[3], format='%d', 
                     ticks=range(0, int(np.nanmax(hist[0]))+1),
                     label = 'número de ocorrências')
        plt.title('Tempo de escolha por czar')
        plt.ylabel('Tempo até escolher (horas)')
        plt.xticks(range(10), labels='', rotation=45)
        
        ax = plt.gca()
        # Customize minor tick labels
        ax.set_xticks([i+0.5 for i in range(10)], minor=True)
        ax.set_xticklabels(formata_nomes(self.jogadores), minor=True, rotation=45)
        
        for tick in ax.xaxis.get_minor_ticks():
            tick.tick1line.set_markersize(0)
            tick.tick2line.set_markersize(0)
        if salvar:
            plt.savefig('demora.png', dpi=320, bbox_inches='tight')
        plt.show()
    
    def atrasos(self, salvar=False):
        def plota_dados(tipo, título):
            dados = chain(*[msg.atrasados for msg in self.ata if isinstance(msg, tipo)])
            conta_dados = Counter(dados)
            pessoas, atrasos = zip(*conta_dados.most_common())
            pessoas = formata_nomes(pessoas)
            plt.bar(pessoas, atrasos, width=0.9, label=título)
            plt.title('Pontualidade por jogador')
            plt.ylabel('número de ocorrências')
            ax = plt.gca()
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            plt.xticks(rotation=45)
        
        plota_dados(HurryUp, 'demoras')
        plota_dados(Atraso, 'atrasos')
        plt.legend()
        if salvar:
            plt.savefig('pontualidade.png', dpi=320, bbox_inches='tight')
        plt.show()
    

def análise_individual(jogo, salvar=False):
    jogo.plot_heatmap(normalizar=False, salvar=salvar)
    jogo.plot_distribuição_pontos(salvar=salvar)
    jogo.horários(salvar=salvar)
    jogo.demora(salvar=salvar)
    jogo.plot_histórico(normalizar=False, espalhar=True, salvar=salvar)
    jogo.atrasos(salvar=salvar)

def main():
    path = 'result.json'

    partidas = Partida.from_json(path)
    última = partidas[-1]
    todas = sum(partidas[4:], start=Partida([]))
    cah = sum(partidas[-1:], start=Partida([]))
    
    análise_individual(cah, salvar=True)

if __name__=="__main__":
    main()
