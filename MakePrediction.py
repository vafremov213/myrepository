# Загружаем необходимые модули и библиотеки
import pickle
import pandas as pd
import numpy as np

# данные подгружаются напрямую из базы данных. скрипт выполняется в MS SQL через sp_execute_external_script

# обрабатываем данные и создаем недостающие столбцы
prediction = pd.DataFrame()
prediction["DateTime"] = data["DateTime"]
prediction["Current"] = np.round(data["GM_cumsum"], 2)

data = data.set_index("DateTime")
data["sin_hour"] = np.sin(2 * np.pi * data["Hour"] / 24)
data["cos_hour"] = np.cos(2 * np.pi * data["Hour"] / 24)
data = data.drop("Hour", axis=1)

 
# Загружаем модель из базы данных 
model = pickle.loads(model)

# Делаем прогноз
prediction["GM_prediction"] = np.round(model.predict(data), 2)
print(prediction)