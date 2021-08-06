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
    '''Lê a mensagem do cards-against-humanity-bot e atualiza a base de
    dados conformemente'''
    path_mensagens = 'mensagens.txt'
    path_histórico = 'histórico.txt'
    
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


def conversa(update, context):
    '''ações tomadas caso o usuário mande uma mensagem sem comandos'''
    if update.message.from_user.id == 'user171291664': # msg do CAH bot
        cards_against_humanity_bot(update, context)
    elif 'bot' in update.message.text.lower():
        patada(update, context)
    elif update.message.text[-1] == '?':
        update.message.reply_text('sua mãe')

def erro(update, context):
    update.message.reply_text('Ocorreu um erro!')



################################# menu ########################################

# uma finite-state machine
MENU, ESCOLHA, FIM = range(3)

def início(update, context):
    '''mensagem de boas-vindas ao usuário. Resposta ao comando /start'''
    nome = update.message.from_user.first_name
    update.message.reply_text(f"Yoo {nome}, fala ae")
    print('mandei pro menu')
    return MENU


def menu(update, context):
    print('menu')
    entradas = (('chutar vencedor',), ('reclamar do último czar',),)
    update.message.reply_text('O que quer de mim?',
        reply_markup=ReplyKeyboardMarkup(entradas, one_time_keyboard=True,))
    return ESCOLHA
    

def chutar(update, context):
    opções = (('1. sua mãe',), ('2. minha carta',), ('3. nenhuma',),)
    update.message.reply_text('Que carta você acha que vai ganhar?',
        reply_markup=ReplyKeyboardMarkup(opções, one_time_keyboard=True,))
    return FIM


def reclamar(update, context):
    update.message.reply_text('Pode desabafar')
    return MENU
    # return ConversationHandler.END
    

def fim(update, context):
    path_chutes = 'chutes.txt'
    chute = update.message.text
    print(chute)
    nome = update.message.from_user.first_name
    print(nome)
    with open(path_chutes, 'a') as file:
        file.write(f'{nome}: {chute}\n')
    return MENU
    # return ConversationHandler.END


def cancelar(update, context):
    update.message.reply_text('#cancelado')
    return ConversationHandler.END


menu_handler = ConversationHandler(
    entry_points=[CommandHandler('menu', menu)],
    # entry_points=[CommandHandler('start', início)],
    states={#MENU: MessageHandler(Filters.all, menu)],
            ESCOLHA: [MessageHandler(Filters.regex(r'chutar'), chutar),
                      MessageHandler(Filters.regex(r'reclamar'), reclamar)],
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
