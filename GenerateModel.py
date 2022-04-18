# загружаем необходимые модули и библиотеки
import pickle
import numpy as np
import pandas as pd
from sklearn.metrics import  mean_absolute_error, mean_absolute_percentage_error, precision_score, recall_score
from sklearn.ensemble import GradientBoostingRegressor, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, GridSearchCV

 
# данные подгружаются напрямую из базы данных. скрипт выполняется в MS SQL через sp_execute_external_script

# обрабатываем данные и создаем недостающие столбцы
data["EndDateTime"] = pd.to_datetime(data["EndDateTime"])
data = data.set_index("EndDateTime")
data["sin_hour"] = np.sin(2 * np.pi * data["Hour"] / 24)
data["cos_hour"] = np.cos(2 * np.pi * data["Hour"] / 24)
data = data.dropna()


x = data.drop(["GM_daysum", "Hour", "PlanResult", "PlanValue"], axis=1)
y = data["GM_daysum"]

# Разбиваем данные на тренировочную и тестовую части
x_train, x_test, y_train,  y_test = train_test_split(x, y, test_size=0.25)

 
# Параметры для GridSearchCV
grad_boost_params = {

                                  "learning_rate": [0.09, 0.1, 0.11, 0.12, 0.13, 0.14],
                                  "n_estimators":  [100, 200, 500, 600],
                                  "max_depth": [9, 10, 11, 12, 13, 14, 15, 16],}

 
# Ищем лучшую модель через GridSearchCV
#grad_boost_clf = GridSearchCV(GradientBoostingRegressor(), grad_boost_params, cv=5)
#grad_boost_clf.fit(x_train, y_train)
#print(grad_boost_clf.best_params_)
#model = grad_boost_clf.best_estimator_

# После определения лучших гиперпараметров обучаем модель
model = GradientBoostingRegressor(n_estimators = 250, learning_rate=0.12, max_depth=15, random_state=42)
model.fit(x_train, y_train)

# Делаем прогноз и считаем ошибку
y_pred_tst = model.predict(x_test)
y_pred_tr = model.predict(x_train)

mape_test = round(np.float(mean_absolute_percentage_error(y_test, y_pred_tst) * 100), 5)
mape_train = round(np.float(mean_absolute_percentage_error(y_train, y_pred_tr) * 100), 5)

# Сохраняем обученую модель
model = pickle.dumps(model)
