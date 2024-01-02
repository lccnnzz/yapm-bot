import os
from datetime import datetime
import time
import random
import requests
from bs4 import BeautifulSoup as bs
import threading
import logging
import sqlite3
from  modules.database import Database

DEAL_THRSH = 0.15
PRICE_THRSH = 0.03
MIN_VARIATION = 0.03
MIN_REFRESH_TIME = 3600
BASE_URL = 'https://www.amazon.it/dp/'

# Class Monitor
class Monitor(threading.Thread):
    data = {}

    def __init__(self, id:str, owner:str, thread_lock, database:Database):
        super().__init__()
        self.id = id
        self.owner = owner
        self.lock = thread_lock
        self.db = database
        self.__refresh_time = 21600
        self.min_variation = MIN_VARIATION
        self.deal_threshold = DEAL_THRSH
        self.__stop_req = False
        self.__create_user()
    
    def __create_user(self):
        with self.lock:
            self.db.add_user(self.id, self.owner)

    @property
    def refresh_time(self):
        return self.__refresh_time

    def set_refreshtime(self, refresh_t:int):
        if refresh_t < MIN_REFRESH_TIME:
            return False
        else:
            self.__refresh_time = refresh_t
            return True

    def add_item(self, item_id:str, item_name:str):
        with self.lock:
            self.db.add_item(self.id, item_id, item_name)   
    
    def remove_item(self, item_id:str):
        with self.lock:
            self.db.remove_item(self.id, item_id)

    def get_price(self, item_id:str, user_agent:str):
        url = f'https://www.amazon.it/dp/{item_id}'
        resp = requests.get(url, headers={'User-Agent' : user_agent})
        if resp.status_code == requests.codes.OK:
            page = bs(resp.content, features='html.parser')
            try:
                center_col = page.find('div', attrs={'id' : 'centerCol'})
                curr_price_whole = center_col.find('span', attrs={'class' : 'a-price-whole'}).text.replace(',', '')
                curr_price_fraction = center_col.find('span', attrs={'class' : 'a-price-fraction'}).text
                curr_price = float(f'{curr_price_whole}.{curr_price_fraction}')
                return curr_price
            except AttributeError as e:
                pass
        return None
 
    def get_useragent(self):
        with self.lock:
            agents = self.db.get_useragents()
            return agents[random.randint(0, len(agents))]['ua']

    def get_prices(self):
        agent = self.get_useragent()
        with self.lock:
            for item in self.db.user_items(self.id):
                price = self.get_price(item['item_id'], agent)
                if price:
                    self.db.add_price(item['item_id'], price)
                time.sleep(random.randint(4,12))

    def items(self):
        return self.db.user_items(self.id)
    
    def item_prices(self, item_id:str):
        return self.db.item_prices(user_id=self.id, item_id=item_id)
    
    def last_prices(self):
        prices = []
        for item in self.items():
            if item_prices := self.item_prices(item['item_id']):
                prices.append({
                    'id' : item['item_id'],
                    'name' : item['item_name'],
                    'price' : item_prices[0]['price']
                })
        return prices

    def run(self):
        while not self.__stop_req:
            self.get_prices()
            time.sleep(self.__refresh_time)
        self.__stop_req = False

    def stop(self):
        if self.is_alive() and not self.__stop_req:
            self.__stop_req = True
