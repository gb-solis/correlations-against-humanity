import logging
from random import randint
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from cards_against_humanity import parser

# lidar com erros
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)

# pegar token
with open('token.txt', 'r') as file:
    token = file.read()


################### funções associadas a commandos ###################
def start(update, context):
    '''mensagem de boas-vindas ao usuário. Resposta ao comando /start'''
    print('start' + 30*'#')
    nome = update.message.from_user.first_name
    update.message.reply_text(f"Yo {nome}, fala ae")


def ajuda(update, context):
    '''ajuda o usuário. Resposta ao comando /help'''
    update.message.reply_text('Vou ajudar porra nenhuma')


def patada(update, context):
    '''responde a mensagem com uma patada. Função temporária?'''
    user = update.message.from_user
    nome = user.first_name
    sobrenome = user.last_name
    frases = ('Faz favor, n me dirige a palavra naum',
               f'Fica de boa ai {nome}',
               f'cansou de desapontar a família {sobrenome} e veio encher o saco',
               f'{nome} {sobrenome}: um contrargumento para a liberdade de expressão',
               2*'AAAAAAAAAAAAAAAAAAAAAAAAAA',
               'cringe',
               'cringe')
    índice = randint(0, len(frases)-1)
    mensagem = frases[índice]
    update.message.reply_text(mensagem)


def cards_against_humanity_bot(update, context):
    print('cards against humanity bot' + 30*'#')
    '''Lê a mensagem do cards-against-humanity-bot e atualiza a base de
    dados conformemente'''
    path_mensagens = 'mensagens.txt'
    path_histórico = 'histórico.txt'
    
    print('Recebi mensagem do bot!')
    mensagem = update.message.text
    rodada = parser(mensagem)
    # anota o vencedor (deveríamos anotar o czar também...)
    if rodada.finalizada:
        vencedor = rodada.vencedor
        with open(path_histórico, 'a') as file:
            file.write(vencedor + '\n')
    # salva as mensagens do bot para análise posterior
    if rodada.finalizada or rodada.recebida:
        with open(path_mensagens, 'a') as file:
            file.write(mensagem + '\n\n')
    else:
        with open('rejeitadas.txt', 'a') as file:
            file.write(mensagem + '\n\n\n\n')


def conversa(update, context):
    print('conversa' + 30*'#')
    '''ações tomadas caso o usuário mande uma mensagem sem comandos'''
    if 'bot' in update.message.text.lower():
        patada(update, context)
    elif update.message.text[-1] == '?':
        update.message.reply_text('sua mãe')

def erro(update, context):
    update.message.reply_text('Ocorreu um erro!')



################################# menu ########################################

# uma finite-state machine
MENU, ESCOLHA, DESABAFO, FIM, *_ = range(10)

def menu(update, context):
    print('menu fim')
    entradas = (('chutar vencedor',), ('reclamar do último czar',),)
    update.message.reply_text('O que quer de mim?',
        reply_markup=ReplyKeyboardMarkup(entradas, one_time_keyboard=True,))
    return ESCOLHA
    

def início(update, context):
    print('início' + 30*'#')
    '''mensagem de boas-vindas ao usuário. Resposta ao comando /start'''
    nome = update.message.from_user.first_name
    update.message.reply_text(f"Yoo {nome}, fala ae")
    print('mandei pro menu')
    return menu(update, context)


def pegar_opções():
    '''retorna lista das cartas jogadas na última rodada, e o czar'''
    print('pegar opções' + 30*'#')
    with open('mensagens.txt', 'r', encoding='utf8') as file:
        dados = file.read()
    rodadas = dados.split('\n\n' + 80*'_' + '\n\n')
    mensagens = [rodada.split('\n\n' + 80*'-' + '\n\n') for rodada in rodadas]
    última = mensagens[-1][0]
    escolhas = última.split('\n\n')[-1].split('\n  - ')
    escolhas[0] = escolhas[0][4:]

    czar = parser(última).czar
    # print(escolhas)
    return [[e] for e in escolhas], czar


def pegar_resultado():
    '''retorna a última resposta escolhida e seu autor'''
    with open('mensagens.txt', 'r', encoding='utf8') as file:
        dados = file.read()
    rodadas = dados.split('\n\n' + 80*'_' + '\n\n')
    mensagens = [rodada.split('\n\n' + 80*'-' + '\n\n') for rodada in rodadas]
    última = mensagens[-1][1]
    linhas = última.splitlines()
    vencedor = linhas[0].split()[:-3]
    


def pegar_contexto():
    '''retorna czar e vencedor (se houver) da última rodada'''
    _, czar = pegar_opções()
    resposta, vencedor = 0,0
    


def chutar(update, context):
    print('chutar' + 30*'#')
    opções, czar = pegar_opções()
    # opções = [[1],[2]]
    update.message.reply_text(f'Que carta você acha que {czar} vai escolher?',
        reply_markup=ReplyKeyboardMarkup(opções, one_time_keyboard=True,))
    return FIM


def opinar(update, context):
    # opções = pegar_opções()
    update.message.reply_text('Você concordou com a escolha do czar?')
    


def reclamar(update, context):
    update.message.reply_text('Pode desabafar')
    return DESABAFO
    # return ConversationHandler.END
    
def empatizar(update, context):
    usuário = update.message.from_user
    nome = usuário.first_name + ' ' + usuário.last_name
    desabafo = update.message.text
    with open('desabafos.txt', 'a') as file:
        file.write(f'{nome}: {desabafo}\n\n')
    
    respostas = ('uhum, uhum, põe pra fora', 'nossa, muito válida sua reclamação',)
    índice = randint(0, len(respostas)-1)
    update.message.reply_text(respostas[índice])
    return menu(update, context)

def fim(update, context):
    path_chutes = 'chutes.txt'
    chute = update.message.text
    print(chute)
    nome = update.message.from_user.first_name
    print(nome)
    with open(path_chutes, 'a') as file:
        file.write(f'{nome}: {chute}\n')
    return menu(update, context)
    # return ConversationHandler.END


def cancelar(update, context):
    update.message.reply_text('#cancelado')
    return menu()


menu_handler = ConversationHandler(
    # entry_points=[CommandHandler('menu', menu)],
    entry_points=[CommandHandler('start', início)],
    states={MENU: [MessageHandler(Filters.all, menu)],
            ESCOLHA: [MessageHandler(Filters.regex(r'chutar'), chutar),
                      MessageHandler(Filters.regex(r'reclamar'), reclamar)],
            DESABAFO: [MessageHandler(Filters.all, empatizar)],
            FIM: [MessageHandler(Filters.all, fim)]},
    fallbacks=[CommandHandler('cancelar', cancelar)]
    )



############### corpo do programa #############################################
def main():
    # setup inicial, só aceita
    updater = Updater(token, use_context=True)
    dispatcher = updater.dispatcher

    # comandos "start" e "help"
    # dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", ajuda))

    # comando "chute"
    dispatcher.add_handler(CommandHandler("chutar", chutar))
    
    # menu
    dispatcher.add_handler(menu_handler)
    
    # handler para mensagens do bot
    dispatcher.add_handler(MessageHandler(Filters.via_bot(
        '@chat_against_humanity_bot'), cards_against_humanity_bot))
    
    # handler pra texto normal, sem comandos
    dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command),
                                          conversa))
    
    # add a handler for errors
    dispatcher.add_error_handler(erro)

    # start bot
    updater.start_polling()
    # run the bot until Ctrl-C
    updater.idle()

if __name__=="__main__":
    main()
