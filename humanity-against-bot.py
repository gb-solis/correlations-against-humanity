from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import logging

# lidar com erros
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)

token = '1924746621:AAEgDoTZOSjfq2ZK4pYVhsmbK2hoUHEdK8M'


################### funções associadas a commandos ###################
def start(update, context):
    nome = update.message.chat.first_name
    update.message.reply_text(f"Yo {nome}, fala ae")
    
def ajuda(update, context):
    update.message.reply_text('Vou ajudar porra nenhuma')
    
def conversa(update, context):
    # pass
    update.message.reply_text('Fica de boa pedro')

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