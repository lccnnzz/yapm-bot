import sqlite3
import json
import requests
from datetime import datetime
from multipledispatch import dispatch
DB_SCHEMA = 'config/schema.sql'

class Database(object):
    def __init__(self, db:str):
        self.path = db
        self.__connection = sqlite3.connect(self.path, check_same_thread=False)
        self.__connection.row_factory = self.dict_factory
        self.__cursor = self.__connection.cursor()
        self.__load_schema(DB_SCHEMA)
        try:
            self.__load_useragents()
        except:
            pass
    
    def close(self):
        self.__connection.close()
    
    def dict_factory(self, column, row):
        fields = [column[0] for column in self.__cursor.description]
        return {key: value for key, value in zip(fields, row)}

    def users(self):
        return self.__cursor.execute(f"SELECT * FROM Users").fetchall()

    def user_items(self, user_id):
        try:
            return self.__cursor.execute(f"SELECT * FROM UserItems WHERE user_id='{user_id}'").fetchall()
        except:
            return []

    def user_refresht(self, user_id):
        return self.__cursor.execute(f"SELECT refresh_time FROM Users WHERE id='{user_id}'").fetchone()['refresh_time']
    
    def user_minvar(self, user_id):
        return self.__cursor.execute(f"SELECT min_variation FROM Users WHERE id='{user_id}'").fetchone()['min_variation']

    def user_dealvar(self, user_id):
        return self.__cursor.execute(f"SELECT deal_variation FROM Users WHERE id='{user_id}'").fetchone()['deal_variation']

    @dispatch(str)
    def item_prices(self, item_id):
        try:
            return self.__cursor.execute(f"SELECT * FROM Prices WHERE item_id='{item_id}' ORDER BY timestamp DESC").fetchall()
        except:
            return []

    @dispatch(str, int)
    def item_prices(self, item_id, user_id):
        query = f"""
            SELECT P.timestamp, P.item_id, P.price, UI.item_name
            FROM Prices AS P 
            JOIN UserItems AS UI ON P.item_id = UI.item_id
            WHERE P.item_id='{item_id}' AND UI.user_id='{user_id}'
            ORDER BY timestamp DESC
        """
        try:
            return self.__cursor.execute(query).fetchall()
        except:
            return []

    def get_useragents(self):
        return self.__cursor.execute(f"SELECT * FROM UserAgents").fetchall()

    def user_exists(self, user_id):
        res = self.__cursor.execute(f"SELECT * FROM Users WHERE id='{user_id}'").fetchall()
        return True if res else False

    def item_exists(self, user_id, item_id):
        res = self.__cursor.execute(f"SELECT * FROM UserItems WHERE item_id='{item_id}'").fetchall()
        return True if res else False

    def ua_exists(self, user_agent):
        res = self.__cursor.execute(f"SELECT * FROM UserAgents WHERE ua='{user_agent}'").fetchall()
        return True if res else False
    
    def add_user(self, user_id, user_name):
        if not self.user_exists(user_id):
            self.__cursor.execute(f"INSERT INTO Users('id', 'name') VALUES('{user_id}', '{user_name}');")
            self.__connection.commit()

    def add_item(self, user_id, item_id, item_name):
        if not self.item_exists(user_id, item_id):
            self.__cursor.execute(f"INSERT INTO UserItems VALUES ('{user_id}', '{item_id}', '{item_name}', '{datetime.now().astimezone().isoformat()}')")
            self.__connection.commit()
            # TODO: ritorna esito dell'operazione
     
    def add_price(self, item_id, price):
        self.__cursor.execute(f"INSERT INTO Prices VALUES ('{datetime.now().astimezone().isoformat()}','{item_id}', '{price}')")
        self.__connection.commit()
    
    def add_useragent(self, user_agent):
        if not self.ua_exists(user_agent):
            self.__cursor.execute(f"INSERT INTO UserAgents (ua, added) VALUES ('{user_agent}', '{datetime.now().astimezone().isoformat()}')")
            self.__connection.commit()
    
    def upd_refreshtime(self, user_id, refresh_t):
        self.__cursor.execute(f"UPDATE Users SET refresh_time={refresh_t} WHERE id={user_id}")
        self.__connection.commit()

    def remove_user(self, user_id):
        pass

    def remove_item(self, user_id, item_id):
        self.__cursor.execute(f"DELETE FROM UserItems WHERE user_id = '{user_id}' AND item_id = '{item_id}'")
        self.__connection.commit()
    
    def __load_schema(self, schema):
    	with open(schema, 'r') as query:
    		self.__cursor.executescript(query.read())

    def __load_useragents(self):
        res = requests.get('https://www.useragents.me/api').json()
        for item in res['data']:
            self.add_useragent(item['ua'])

    def increment_useragent(self, ua_id):
        pass