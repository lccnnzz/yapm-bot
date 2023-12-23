from modules.database import Database
from modules.monitor import Monitor
from modules.bot import Bot
import threading
import time
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--database', type=str, help='Set the database path', required=True)
parser.add_argument('--api_token', type=str, help='Set the Telegram Bot token path', required=True)
parser.add_argument('--debug', action='store_true')
args = parser.parse_args()

if __name__ == "__main__":
    db = Database(args.database)
    lock = threading.Lock()
    bot = Bot(args.api_token, db, lock, [])
    bot.run()
