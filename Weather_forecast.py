# импортируем необходимые бибилиотеки
import pandas as pd
import psutil
import os
import time
import pyodbc
import subprocess
import configparser 
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options
from datetime import datetime, timedelta, date


config = configparser.ConfigParser()  # создаём объекта парсера
config.read("Setting.ini")  # читаем конфиг

# функция для обработки строк. Данные приходят в формате '10 °C'
def splt(data):
    dts = data.split()
    return dts[0]

# функция для обработки значений облачности
def clouds(cloud):
    if 75 <= cloud <= 100:
        return 1
    if 25 < cloud < 75:
        return 0.5
    else:
        return 0

# функция для удаления всех лишних символов (могут прийти различные непонятные символы)
def replace_incorrect_chars(data):
    newdata = ''.join(ch for ch in data if ch in correct_ch_lst)
    return newdata

#  основная функция для парсинга погоды
def parse(day_delta):
    for i in day_delta:
        delta = timedelta(days=i)
        future = today+delta
        future = future.strftime("%Y-%m-%d") 
        url = 'https://www.wunderground.com/hourly/fi/kuhmo/IKUHMO6/date/{}'.format(future) 

# запускаем селениум и загружаем табличку с погодой
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        table = None
        while table is None:
            try:
                table = driver.find_element_by_tag_name('tbody').get_attribute('innerHTML')
                driver.close()
            except:
                pass

# проходимся по табличку и добавляем значения в датафрейм
        data = pd.DataFrame()
        soup = BeautifulSoup(table, 'html.parser')
        weather = soup.find_all("tr")
        for tr in weather:
            row = []
            tds = tr.find_all("td")
            for td in tds:
                row.append(td.text)
            series = pd.Series(row, name='rows')
            data = data.append(series)
        data = data.rename(columns={0:"Time", 1:"Condition", 2:"Temp", 3:"Feel", 4:"Precip", 5:"Amount", 6:"Clouds", 7:"Dew", 8:"Humd", 9:"Wind", 10:"Pressure"})
        data = data[["Time", "Condition", "Temp", "Clouds", "Humd", "Wind", "Pressure"]]

# применяем функции для обработки результатов и переводим значения в систему СИ
        data["Temp"] = data["Temp"].apply(replace_incorrect_chars)
        data["Temp"] = data["Temp"].apply(splt).astype(float)
        data["Temp"] = round((data["Temp"] - 32)*(5/9), 1)

        data["Wind"] = data["Wind"].apply(replace_incorrect_chars)
        data["Wind"] = data["Wind"].apply(splt).astype(float)
        data["Wind"] = round(data["Wind"] * 0.44704)

        data["Pressure"] = data["Pressure"].apply(replace_incorrect_chars)
        data["Pressure"] = data["Pressure"].apply(splt).astype(float)
        data["Pressure"] = round(data["Pressure"] * 25.4, 1)/1000

        data["Clouds"] = data["Clouds"].apply(replace_incorrect_chars)
        data["Clouds"] = data["Clouds"].astype(float).apply(clouds)

        data["Humd"] = data["Humd"].apply(replace_incorrect_chars)
        data["Humd"] = data["Humd"].apply(splt).astype(float)/100


        data = data.reset_index()

# Блок функция для обработки погодных условий (дождь, снег, ясно)
        def rains(adata):
            Rain = [0] * len(data["Condition"])
            for i in data.index:
                if "rain" in adata["Condition"][i].lower():
                    Rain[i] = 1
                if adata["Condition"][i].lower() == "rain/snow showers" or adata["Condition"][i].lower() == "rain/snow" or adata["Condition"][i].lower() == "showers":
                    if adata["Temp"][i] >= 0:
                        Rain[i] = 1
                    else:
                        Rain[i] = 0
            return Rain


        def snows(adata):
            Snow = [0] * len(data["Condition"])
            for i in data.index:
                if "snow" in adata["Condition"][i].lower():
                    Snow[i] = 1
                if adata["Condition"][i].lower() == "rain/snow showers" or adata["Condition"][i].lower() == "rain/snow" or adata["Condition"][i].lower() == "showers":
                    if adata["Temp"][i] < 0:
                        Snow[i] = 1
                    else:
                        Snow[i] = 0
            return Snow


        def clears(adata):
            Clear = []
            for i in data.index:
                if adata["Rain"][i] == 0 and adata["Snow"][i] == 0:
                    Clear.append(1)
                else:
                    Clear.append(0)
            return Clear

# Составляем дату/время т.к в исходной табличке только время
        def times(data):
            Time = []
            for i in data["Time"]:
                Time.append("{} {}".format(future, i))
            return Time

        data["DateTime"] = times(data)
        data["DateTime"] = pd.to_datetime(data["DateTime"])

        data["Rain"] = rains(data)
        data["Snow"] = snows(data)
        data["NoPrec"] = clears(data)
        data = data.drop(["Time", "Condition", "index"], axis=1)
        print(data)

# Подключяемся к базе данных
        cnxn = pyodbc.connect('DRIVER={4};SERVER={0};DATABASE={1};UID={2};PWD={3}'.format(config["DataBaseConfig"]["serverName"],config["DataBaseConfig"]["dbName"],config["DataBaseConfig"]["Login"],config["DataBaseConfig"]["Password"],config["DataBaseConfig"]["Driver"]))#UID=SYS_PRO;PWD=wenco
        cursor = cnxn.cursor()
# Вносим данные в базу данных
        for index, row in data.iterrows():
            cursor.execute("INSERT INTO Table_weather_forecast(DateTime,Temp,Pressure,Humd,Wind,Clouds,Rain,Snow,NoPrec) values(?,?,?,?,?,?,?,?,?)", row.DateTime, row.Temp, row.Pressure, row.Humd, row.Wind, row.Clouds, row.Rain, row.Snow, row.NoPrec)
        cnxn.commit()
        cnxn.close()

# Закрываем chromedriver.exe т.к он может зависнуть
    for proc in psutil.process_iter():
        name = proc.name()
        if name == "chromedriver.exe":
            os.system("taskkill /f /im chromedriver.exe")

correct_ch_lst = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '.']

today = datetime.today()

day = today.strftime('%A') 

# запускаем парсинг, в зависимости от дня недели необходимы разные данные
if day == "Friday":
    day_delta = [2, 3, 4]
elif day == "Saturday" or  day == "Sunday":
    day_delta = None
else:
    day_delta = [2] 

if day_delta is not None:
    parse(day_delta)
else:
    pass
