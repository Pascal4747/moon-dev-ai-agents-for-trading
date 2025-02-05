import asyncio
import json
import os 
from datetime import datetime
import pytz
from websockets import connect 
from termcolor import cprint
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# List of symbols to track  
symbols = ['btcusdt', 'ethusdt', 'solusdt', 'dogeusdt', 'wifusdt']

# Binance Futures WebSocket URL - using the correct futures endpoint
BASE_WS_URL = 'wss://fstream.binance.com/ws/'

shared_symbol_counter = {'count': 0}

print_lock = asyncio.Lock()

async def binance_funding_rates(symbol, shared_counter):
    global print_lock  
    stream_url = f'{BASE_WS_URL}{symbol}@markPrice'
    async with connect(stream_url) as websocket:
        while True:
            try:
                async with print_lock:
                    message = await websocket.recv()
                    data = json.loads(message)
                    event_time = datetime.fromtimestamp(data['E'] / 1000).strftime("%H:%M")
                    funding_rate = float(data['r'])
                    yearly_funding_rate = (funding_rate * 3 * 365) * 100
                    symbol_display = symbol.upper().replace('USDT', '')
                    if yearly_funding_rate > 50:
                        text_color, back_color = 'black', 'on_red'
                    elif yearly_funding_rate > 30:
                        text_color, back_color = 'black', 'on_yellow'
                    elif yearly_funding_rate > 5:
                        text_color, back_color = 'black', 'on_magenta'
                    elif yearly_funding_rate  < -10:
                        text_color, back_color = 'black', 'on_green'
                    else:
                        text_color, back_color = 'white', 'on_light_green'
                    
                    cprint(f"{symbol_display} funding: {yearly_funding_rate:.2f}&", text_color, back_color)
                    
                    shared_counter['count'] += 1
                    
                    if shared_counter['count'] >= len(symbol):
                        cprint(f"{event_time} yrly fund", 'white', 'on_black')
                        shared_counter['count'] = 0 
            except:
                await asyncio.sleep(5)
                

async def main():
    tasks = [binance_funding_rates(symbol, shared_symbol_counter) for symbol in symbols]
    await asyncio.gather(*tasks)
    
if __name__ == "__main__":
    asyncio.run(main())

                    
