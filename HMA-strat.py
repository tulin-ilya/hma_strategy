# https://github.com/tulin-ilya/hma_strategy.git

# pip install websocket-client
# pip install pandas-ta
# pip install ccxt

import websocket
import ccxt
import json
import pandas as pd
import pandas_ta as ta
from datetime import datetime

# Настроойки
# Настройки индикатора
slow_len            = 50            # Длина медленной HMA
slow_index          = 5             # Индекс медленной HMA 
fast_len            = 10            # Длина быстрой HMA
fast_index          = 1             # Индекс быстрой HMA

# Настройки торговли
ticker              = 'BTCUSDT'     # Тикер
timeframe           = '1m'          # Таймфрейм {1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M}
pos_size            = 10            # размер позиции в $ без учета плеча (плечо выставлять на бирже!)
sl_offset_perc      = 0,5           # % базового stop-loss от цены входа
tsl_init_perc       = 0,2           # % инициации трейлинг stop-loss от цены входа
tsl_offset_perc     = 0,2           # % отставания трейлинг stop-loss от цены текущего high/low

# обозначаем перечень необходимых списков для расчета индикатора
time_list       = []
open_list       = []
high_list       = []
low_list        = []
close_list      = []

# обозначаем перечень необходимых списков для торговли
sl_long_list                = []
tsl_long_init_price_list    = []
entry_list                  = []

# преобразование настроек для подключения к сокету binance и модулю ccxt
limit           = slow_len * 2
ws_ticker       = ticker.lower()
split_ticker    = ticker.split('USDT')
ccxt_ticker     = split_ticker[0] + '/' + 'USDT'

# указываем адрес сокета биржи
socket      = f'wss://fstream.binance.com/ws/{ws_ticker}@kline_{timeframe}'

# указываем данные, для подключения к серверу биржи через ccxt
exchange = ccxt.binance({
    'options': {
        'defaultType': 'future',
    },
})

# через модуль ccxt получаем данные исторических свечей
bars = exchange.fetch_ohlcv(ccxt_ticker, timeframe = timeframe, limit = limit)

# вносим данные исторических свечей в списки для расчета индикатора
for i in bars:
    time_list.append(i[0])
    open_list.append(i[1])
    high_list.append(i[2])
    low_list.append(i[3])
    close_list.append(i[4])

# удаляем последнюю запись из списков, т.к. их мы получим из сокета
time_list.pop()
open_list.pop()
high_list.pop()
low_list.pop()
close_list.pop()

def on_message(ws, message):
    global time_list, open_list, high_list, low_list, close_list
    # распарсим данные с сокета binance
    json_message        = json.loads(message)                           
    time                = json_message['E']
    candle              = json_message['k']
    open                = float(candle['o'])
    high                = float(candle['h'])
    low                 = float(candle['l'])
    close               = float(candle['c'])
    is_candle_closed    = candle['x']

    # если свеча закрылась
    if is_candle_closed:
        # добавляем данные по свече в список, чтобы использовать для расчета индикатора
        time_list.append(time)
        open_list.append(open)
        high_list.append(high)
        low_list.append(low)
        close_list.append(close)

        # сводим записанные данные свечи в таблицу 
        df = pd.DataFrame(list(zip(time_list, open_list, high_list, low_list, close_list)), columns = ['Timestamp', 'Open', 'High', 'Low', 'Close'])
        # изменяем формат отображения даты и времени
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit = 'ms')

        # на основании данных из таблицы строим индикаторы HMA
        df['Slow HMA'] = ta.hma(df['Close'], slow_len)
        df['Fast HMA'] = ta.hma(df['Close'], fast_len)

        # преобразуем вводные данные по индексам, чтобы можно было ссылаться с их помощью к данным в таблице
        last_index_value = limit - 1
        slow_index_value = last_index_value - slow_index
        fast_index_value = last_index_value - fast_index
        
        # обозначаем условия для окрашивания линий в зеленый цвет
        slow_green_cond = df['Slow HMA'][last_index_value] > df['Slow HMA'][slow_index_value]
        fast_green_cond = df['Fast HMA'][last_index_value] > df['Fast HMA'][fast_index_value]
       
        # задаем значение переменной market_position исходя из текущего цвета линий
        market_position = 'Flat'
        if slow_green_cond and fast_green_cond:
            market_position = 'Long'
        elif not slow_green_cond and not fast_green_cond:
            market_position = 'Short'
        else:
            market_position = 'Flat'

        # выводим информацию в лог
        if slow_green_cond:
            print('Slow HMA is GREEN')
        else:
            print('Slow HMA is   RED')

        if fast_green_cond:
            print('Fast HMA is GREEN')
        else:
            print('Fast HMA is   RED')

        print(df['Timestamp'][last_index_value])            
        print(f'{market_position} condition', '\n')

        # удаляем первую строку из таблицы
        time_list.pop(0)
        open_list.pop(0)
        high_list.pop(0)
        low_list.pop(0)
        close_list.pop(0)

def on_open(ws):
    print('Connection Opened', '\n')

def on_close(ws):
    print('Connection Closed', '\n')

ws = websocket.WebSocketApp(socket, on_open = on_open, on_message = on_message, on_close = on_close)

ws.run_forever()