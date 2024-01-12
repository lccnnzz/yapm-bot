import requests
import logging
import threading
import sqlite3
from  modules.database import Database
from  modules.monitor import Monitor
import time
import re
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler, 
    ConversationHandler,
    CallbackContext,
    MessageHandler,
    filters,
)

logging.basicConfig(encoding='utf-8', level=logging.INFO)

MIN_REFRESH_TIME = 3600

class Bot(threading.Thread):
    # Regular Expressions
    AMZN_FULL_URL = r'^https\:\/\/www\.amazon\.it\/*.*\/dp\/(\w{10,10}).*'
    AMZN_SHORT_URL = r'(https\:\/\/amzn\.eu\/d\/\w+).*'
    AMZN_ITEM_ID = r'^(B\w{9,9})$'

    def __init__(self, token, database:Database, lock, monitors):
        super().__init__()
        self.monitors = monitors
        self.application = ApplicationBuilder().token(token).build()
        self.application.add_handler(CommandHandler('start', self.join))
        self.application.add_handler(CommandHandler('prices', self.last_prices))
        self.application.add_handler(CommandHandler('list', self.items))
        self.application.add_handler(CommandHandler('info', self.info))

        # Conversation handlers config
        self.ITEM_ID, self.ITEM_NAME, self.ITEM, self.REFRESH_TIME = range(4)
        self.application.add_handler(self.__additem_handler())
        self.application.add_handler(self.__delitem_handler())
        self.application.add_handler(self.__setrefreshtime_handler())
        
        # Database config
        self.db = database
        self.lock = lock

    async def imalive(self, application):
        for user in self.db.users():
            message = f'Ciao {user['name']}, il bot è stato riavviato!\nSeleziona il comando /start, grazie.'
            await self.application.bot.send_message(chat_id=user['id'], text=message)

    def run(self):
        self.application.post_init = self.imalive
        self.application.run_polling()

    def stop(self):
        pass
    
    def get_monitor(self, id:str):  
        if monitors := [monitor for monitor in self.monitors if monitor.id == id]:
            return monitors[0]
        else: 
            return None

    def add_monitor(self, user_id:str, user_name:str):
        mon = Monitor(user_id, user_name, self.lock, self.db)
        mon.start()
        self.monitors.append(mon)
        return mon
    
    def get_pattern(self, text:str):
        expressions = [self.AMZN_FULL_URL, self.AMZN_ITEM_ID, self.AMZN_SHORT_URL]
        for expression in expressions:
            if re.search(expression, text):
                return expression
        return ''

    def unshorten(self, url:str):
        return requests.get(url).url

    # Command Handlers
    async def join(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if monitor := self.get_monitor(user.id):   
            message = f'Ciao {user.first_name}, hai già avviato questo Bot'
        else:
            monitor = self.add_monitor(user.id, user.name)
            message = f'Ciao {user.first_name}, benvenuto!'
            context.job_queue.run_repeating(self.notify, (monitor.refresh_time + 120), chat_id=update.effective_chat.id, name=str(user.id))
        
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        
    async def info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        message = f"📦 Yet Another Price Monitor 📦\n#️⃣ Versione: 0.5\n🗓️ Rilasciato il: 22 Dic 2023\n🔓 Licenza: Copyleft\n📝 Github: lccnnzz"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)

    async def add_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text('Inserisci il codice del prodotto o il link Amazon')
        return self.ITEM_ID
    
    async def del_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        monitor = self.get_monitor(user.id)
        choices = [[f'{item["item_name"]}'] for item in monitor.items()]
        keyboard_markup = ReplyKeyboardMarkup(choices, resize_keyboard=True, one_time_keyboard=True, input_field_placeholder=f'Quale vuoi eliminare?')
        await update.message.reply_text(f'Questi sono gli articoli nella tua lista', reply_markup=keyboard_markup)
        return self.ITEM_NAME

    async def last_prices(self,  update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        monitor = self.get_monitor(user.id)
        if monitor.items():
            lines = [f'•\t{item["name"]}\t{item["price"]}€' for item in monitor.last_prices()]  
            if lines:
                await update.message.reply_text('\n'.join(lines))
            else:
                await update.message.reply_text('😞 Spiacente, non è stato ancora aggiornato il prezzo degli articoli che hai inserito')
        else:
            await update.message.reply_text('😞 Spiacente, non hai ancora inserito articoli in monitoraggio')

    async def items(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        monitor = self.get_monitor(user.id)
        lines = [f'📦 ({item["item_id"]})\t{item["item_name"]}' for item in monitor.items()]
        if lines:
            await update.message.reply_text('\n'.join(lines))
        else:
            await update.message.reply_text('😞 Spiacente, non hai ancora inserito articoli in monitoraggio')

    async def set_refreshtime(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        monitor = self.get_monitor(update.effective_user.id)
        await update.message.reply_text(f"⌛️ L'intervallo di aggiornamento attuale è {monitor.refresh_time} s.\nInserisci il nuovo intervallo in secondi (min 3600)")
        return self.REFRESH_TIME

    # Conversation Handlers
    ## Add new item
    async def item_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        monitor = self.get_monitor(update.effective_user.id)    
        match expr := self.get_pattern(update.message.text):
            case self.AMZN_FULL_URL | self.AMZN_ITEM_ID:
                monitor.data['id'] = re.search(expr, update.message.text).group(1)
                await update.message.reply_text(f'Inserisci il nome del prodotto')
                return self.ITEM_NAME
            
            case self.AMZN_SHORT_URL:
                item_url = self.unshorten(re.search(expr, update.message.text).group(1))
                item_id = re.search(self.AMZN_FULL_URL, item_url).group(1)
                await update.message.reply_text(f'Inserisci il nome del prodotto')
                return self.ITEM_NAME

            case _:
                await update.message.reply_text(f'🚫 Spiacente, il valore inserito non è valido')
                monitor.data = {}
                return ConversationHandler.END

    async def item_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        monitor = self.get_monitor(update.effective_user.id)
        monitor.data['name'] = update.message.text
        monitor.add_item(monitor.data['id'], monitor.data['name'])
        await update.message.reply_text(f'✅ Prodotto inserito correttamente! Ottengo il prezzo attuale...')
        item_price = monitor.get_price(monitor.data['id'], monitor.get_useragent())
        await update.message.reply_text(f'💰 {item_price}€')
        self.db.add_price(monitor.data['id'], item_price)
        monitor.data = {}
        return ConversationHandler.END

    ## Remove item
    async def item(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        monitor = self.get_monitor(update.effective_user.id)
        item_id = [item['item_id'] for item in monitor.items() if item['item_name'] == update.message.text][0]
        monitor.remove_item(item_id)
        await update.message.reply_text(f'✅ Prodotto è stato rimosso dalla tua lista')
        return ConversationHandler.END
    
    ## Change refresh time
    async def refresh_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        monitor = self.get_monitor(update.effective_user.id)
        if (refresh_t := int(update.message.text)) < MIN_REFRESH_TIME:
            await update.message.reply_text(f'Il tempo di aggiornamento non è stato modificato.\n🚫 Il valore inserito no è valido!')
        else:
            monitor.refresh_time = refresh_t
            for job in context.job_queue.get_jobs_by_name(update.effective_chat.id):
                job.schedule_removal()
            context.job_queue.run_repeating(self.notify, (refresh_t + 120), chat_id=update.effective_chat.id, name=str(update.effective_chat.id))
            await update.message.reply_text(f'✅ Il tempo di aggiornamento è stato modificato correttamente!')

        return ConversationHandler.END
   
    # Conversation Handler Builders
    def __additem_handler(self):
        return ConversationHandler(
            entry_points=[CommandHandler('add', self.add_item)],
            states={
                self.ITEM_ID : [MessageHandler(filters.TEXT & ~filters.COMMAND, self.item_id)],
                self.ITEM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.item_name)]
            },
            fallbacks=[]
        )
    
    def __delitem_handler(self):
        return ConversationHandler(
            entry_points=[CommandHandler('del', self.del_item)],
            states={
                self.ITEM_NAME : [MessageHandler(filters.TEXT & ~filters.COMMAND, self.item)],
            },
            fallbacks=[]
        )

    def __setrefreshtime_handler(self):
        return ConversationHandler(
            entry_points=[CommandHandler('freq', self.set_refreshtime)],
            states={
                self.REFRESH_TIME : [MessageHandler(filters.TEXT & ~filters.COMMAND, self.refresh_time)],
            },
            fallbacks=[]
        )
    
    async def notify(self, context: ContextTypes.DEFAULT_TYPE):
        monitor = self.get_monitor(context.job.chat_id)
        if monitor.items():
            lines = [f'•\t{item["name"]}\t{item["price"]}€' for item in monitor.last_prices()]  
            if lines:
                await context.bot.send_message(context.job.chat_id, text='\n'.join(lines))
            else:
                await context.bot.send_message(context.job.chat_id, text='😞 Spiacente, non è stato ancora aggiornato il prezzo degli articoli che hai inserito')
        else:
            await context.bot.send_message(context.job.chat_id, text='😞 Spiacente, non hai ancora inserito articoli in monitoraggio')    