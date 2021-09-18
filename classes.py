from dataclasses import dataclass
from datetime import datetime
import re

@dataclass
class Mensagem:
    texto: str
    data: datetime
    id_: int
    
    def __str__(self):
        return f'Mensagem enviada às {self.data:%H:%M de %d/%m/%y}'
               
    @classmethod
    def from_dict(cls, dic):
        return cls(texto=dic['text'], data=datetime.fromisoformat(dic['date']),
                   id_=dic['id'])
    

@dataclass
class AlteraPonto(Mensagem):
    # o __init__ de um dataclass automaticamente roda o init do ancestral,
    # então deixei e criei um post_init pra incializar os atributos derivados.
    # Isso tem o benefício adicional de permitir que todas as classes derivadas
    # de Mensagem usem o método .from_dict sem mudanças adicionais.
    def __post_init__(self):
        self.jogador, self.pontos = self.parser().values()
        self.delta = None
        
    def __str__(self):
        return super().__str__() + '\n'\
        + f'{self.jogador} agora tem {self.pontos} pontos'
        
    def parser(self):
        '''le o texto em self.texto e retorna os atributos relevantes'''
        mensagem = self.texto
        jogador = ' '.join(mensagem[0].split()[1:-1])
        pontos = int(mensagem[-1].split()[-1])
        return {'jogador': jogador, 'pontos': pontos}


@dataclass
class Recebida(Mensagem):
    def __post_init__(self):
        # self.czar, self.pergunta, self.alternativas, self.chumps
        for attr, val in self.parser().items():
            setattr(self, attr, val)
        
    def __str__(self):
        return super().__str__() + '\n' \
        + f'{self.czar} pergunta: "{self.pergunta}"'   
    
    def parser(self, mensagem=None):
        mensagem = mensagem or self.texto
        if isinstance(mensagem, str):
            match = re.match(r'All answers received! The honourable '
                             r'(?P<czar>.*) presiding.\nQuestion: '
                             r'(?P<pergunta>.*)\n'
                             r'(?P<alternativas>(?:\n  - .*)*)'
                             r'(?:\nSkipped these chumps: \n - '
                             r'(?P<chumps>.*))?', mensagem)
            dados = match.groupdict()
            dados['czar'] = dados['czar'].strip()
            dados['alternativas'] = dados['alternativas'].split('\n  - ')[1:]
            dados['chumps'] = dados['chumps'] or {}
            return dados
        elif isinstance(mensagem, list):
            texto = ''.join(txt if isinstance(txt, str) else txt['text'] 
                            for txt in mensagem)
            return self.parser(texto)
        else:
            raise TypeError(f'mensagem não pode ser do tipo {type(mensagem)}')


@dataclass
class Finalizada(Mensagem):
    def __post_init__(self):
        # self.vencedor, self.resposta, self.jogadores
        for attr, val in self.parser().items():
            setattr(self, attr, val)
    
    def __str__(self):
        return super().__str__() + '\n' + \
        f'{self.vencedor} ganhou com a resposta "{self.resposta}"'
    
    def parser(self):
        mensagem = self.texto
        # if not isinstance(mensagem, list):
        #     print('\n\n mensagem não é lista? Erro!\n\n')
        #     return
        match = re.match('(?P<vencedor>.+) wins a point!\n', mensagem[0])
        if match is None:
            match = re.match('(?P<vencedor>.+) wins a point!\n', mensagem)
        dados = match.groupdict()
        dados['vencedor'] = dados['vencedor'].strip()
        jogadores = [msg.split(' - ') for msg in mensagem[-1].split('\n')[1:]]
        jogadores = {j[0].strip(): j[1].rstrip(' points.') for j in jogadores}
        try:
            resposta = mensagem[1]['text']
            return {'resposta': resposta, 'jogadores': jogadores, **dados}
        except:
            # caso em que resposta está contida em vários dicionários
            resposta = None
        return {'resposta': resposta, 'jogadores': jogadores, **dados}
        
               
@dataclass        
class PerdePonto(Mensagem):
    def __post_init__(self):
        self.czar = self.parser()['czar']
    
    def __str__(self):
        return super().__str__() + '\n' + \
        f'{self.czar} moscou e perdeu um ponto'
    
    def parser(self):
        mensagem = self.texto
        dados = re.match('Judge was too slow,  (?P<czar>.*) \(', mensagem[0])
        return dados.groupdict()

@dataclass
class HurryUp(Mensagem):
    def __post_init__(self):
        self.atrasados = self.parser()
    
    def __str__(self):
        return super().__str__() + '\n' + \
        f'{", ".join(self.atrasados)} precisam responder!'
        
    def parser(self):
        mensagem = self.texto
        if isinstance(mensagem, list):
            nomes = [i.strip(' ()') for i in mensagem[:-1] if isinstance(i,str)]
            nomes = sum((i.split(', ') for i in nomes), start=[])
            nomes = [i.strip() for i in nomes]
            return nomes
        elif isinstance(mensagem, str):
            nomes = mensagem[:-len('needs to hurry up! Tick-tock...')] # pode ser need se plural
            return [nomes]
        
@dataclass
class Atraso(Mensagem):
    def __post_init__(self):
        self.atrasados = self.parser()
        
    def __str__(self):
        return super().__str__() + '\n' + \
        f'{", ".join(self.atrasados)} atrasaram' 
      
    def parser(self):
        return [''] # TODO


@dataclass
class HurryJudge(Mensagem):
    def __post_init__(self):
        self.atrasado = self.parser()
        
    def __str__(self):
        return super().__str__() + '\n' + \
        f'o juiz {self.atrasado} está atrasado' 
        
    def parser(self):
        return self.texto # todo


@dataclass
class Entrou(Mensagem):
    def __post_init__(self):
        self.jogador = self.parser()
    
    def __str__(self):
        return super().__str__() + '\n' + \
        f'{self.jogador} entrou no jogo'
      
    def parser(self):
        nome = self.texto[:-len(' has joined the game')]
        return nome.strip()
    
@dataclass
class Início(Mensagem):
    def __post_init__(self):
        self.jogador = self.parser()
    
    def __str__(self):
        return super().__str__() + '\n' + \
        f'{self.jogador} iniciou o jogo'

    def parser(self):
        nome = self.texto[0][:-len(' is starting a new game of xyzzy! Type ')]
        return nome.strip()



class Rodada(Recebida, Finalizada):
    def __init__(self, czar=None, vencedor=None, pergunta=None, resposta=None,
                 alternativas=None, data_recebida=None, data_finalizada=None, 
                 texto_recebida=None, texto_finalizada=None, id_recebida=None, 
                 id_finalizada=None, chumps=None, jogadores=None):
                 
        self.czar = czar
        self.vencedor = vencedor
        self.pergunta = pergunta
        self.resposta = resposta
        self.alternativas = alternativas
        self.data_recebida = data_recebida
        self.data_finalizada = data_finalizada
        self.texto_recebida = texto_recebida
        self.texto_finalizada = texto_finalizada
        self.id_recebida = id_recebida
        self.id_finalizada = id_finalizada
        self.chumps = chumps
        self.jogadores = jogadores
        self.participantes = set(self.jogadores).difference(set(self.chumps))
        # self.texto = 'Rodada do czar {self.czar} perguntando {self.pergunta}, vencida por {self.vencedor}'
        
    def __repr__(self):
        return f'Rodada(czar={self.czar}, pergunta={self.pergunta}, vencedor={self.vencedor})'
    
    @classmethod
    def from_pair(cls, recebida, finalizada):
        assert isinstance(recebida, Recebida), f'primeiro argumento não é Recebida, é {recebida!r}\n Segundo é {finalizada!r}'
        assert isinstance(finalizada, Finalizada), 'segundo argumento não é Finalizada'
        dic_rec = {a:b for a,b in recebida.__dict__.items() if a not in ('data', 'id_', 'texto')}
        dic_fin = {a:b for a,b in finalizada.__dict__.items() if a not in ('data', 'id_', 'texto')}
        return cls(data_recebida=recebida.data, id_recebida = recebida.id_,
                   data_finalizada=finalizada.data, id_finalizada = finalizada.id_,
                   texto_recebida=recebida.texto, texto_finalizada=finalizada.texto,
                   **dic_rec, **dic_fin)

'''
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
'''