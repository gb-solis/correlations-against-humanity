from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from random import randint
import logging

# lidar com erros
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)


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
               3*'AAAAAAAAAAAAAAAAAAAAAAAAAA',
               'cringe')
    índice = randint(0, len(frases)-1)
    mensagem = frases[índice]
    update.message.reply_text(mensagem)


def cards_against_humanity_bot(update, context):
    '''Lê a mensagem do cards-against-humanity-bot e atualiza a base de
    dados conformemente'''
    mensagem = update.message.text


def conversa(update, context):
    '''ações tomadas caso o usuário mande uma mensagem sem comandos'''
    if update.message.from_user.id == 'user171291664': # msg do CAH bot
        cards_against_humanity_bot(update, context)
    elif 'bot' in update.message.text:
        patada(update, context)
    elif update.message.text[-1] == '?':
        update.message.reply_text('sua mãe')


def erro(update, context):
    update.message.reply_text('Ocorreu um erro!')


############### corpo do programa ##################################
def main():
    # setup inicial
    updater = Updater(token, use_context=True)
    dispatcher = updater.dispatcher

    # add handlers for start and help commands
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", ajuda))

    # add a handler for normal text (not commands)
    dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command),
                                          conversa))

    # add an handler for errors
    dispatcher.add_error_handler(erro)

    # start your shiny new bot
    updater.start_polling()

    # run the bot until Ctrl-C
    updater.idle()

main()
