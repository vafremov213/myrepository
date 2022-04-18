# импортируем pandas
import pandas as pd 

# загружаем исходные данные
data1 = pd.read_excel('d:\\Projects\\OrePrediction\\data\\asproductivitybyunit.xlsx')
data2 = pd.read_excel('d:\\Projects\\OrePrediction\\data\\asproductivitybyunit_1.xlsx')
data3 = pd.read_excel('d:\\Projects\\OrePrediction\\data\\asproductivitybyunit_2.xlsx')
data4 = pd.read_excel('d:\\Projects\\OrePrediction\\data\\asproductivitybyunit_3.xlsx')

# объединяем данные и заполняем пустые значения нулями
data = pd.concat([data1, data2, data3, data4])
data = data.fillna(0)
data = data.reset_index(drop=True)
data["EndDateTime"] = pd.to_datetime(data["EndDateTime"])

# обрабатываем данные, удаляем ошибочные записи
data = data.loc["2019-04-10":]
data.query("Volume>0&WorkPeriod==0")
data = data.drop(data.query("Volume>0&WorkPeriod==0").index)
data = data.drop(data.query("Volume==0&WorkPeriod>0").index)
data = data.drop(data.query("WorkPeriod<0").index)

# переворачиваем табличку и дополняем пропущеные часы через resample
data = data.pivot_table(index="EndDateTime", columns="EquipmentName", values=["Volume", "WorkPeriod"])
data = data.fillna(0)
data = data.resample('1H').asfreq()

# переименовываем колонки
lst = data.columns.to_list()
names = []
for i in lst:
    names.append(i[0] + ' ' + i[1])
data = data.droplevel(0, axis=1)  
data.columns = names

# добавляем новый столбец "Смена"
data = data.reset_index()
data["hour"] = data["EndDateTime"].dt.hour
data["day"] = data["EndDateTime"].dt.date
data["Shift"] = 0
for index in data.index:  
    if 9 <= data.loc[index, "hour"] <= 20:
        data.loc[index, "Shift"] = str(data.loc[index, "day"]) + ' - 2'
    elif 21 <= data.loc[index, "hour"] <= 23:
        data.loc[index, "Shift"] = str((data.loc[index, "day"] + pd.DateOffset(days=1)).date()) + ' - 1'
    else:
        data.loc[index, "Shift"] = str(data.loc[index, "day"]) + ' - 1'


# удаляем все значения в смене, если хотя бы один час пропущен
na =[]
nulls = data[data.isna().any(axis=1)].Shift.unique()
for i in nulls:
    na.append(i)
for index in data.index:
     if data.loc[index, "Shift"] in na:
        data = data.drop(index=index)


data = data.set_index("EndDateTime")

# считаем кумулятивную сумму по каждой смене
columns = data.columns.to_list()
for column in columns[:-3]:
    data[column + 'CumSum'] = data[column].groupby(data['Shift']).cumsum()

# сохраняем полученный результат
data.to_excel('d:\\Projects\\OrePrediction\\data\\asproductivitybyunit_cum.xlsx')