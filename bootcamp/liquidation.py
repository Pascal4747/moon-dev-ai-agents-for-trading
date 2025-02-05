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

websocket_url = 'wss://fstream.binance.com/ws/'
filename = 'binance.csv'


if not os.path.isfilename(filename):
    with open(filename, 'w') as f:
        f.write(",".join([
            'sysmbol', 'side', 'order_type', 'time_in_force',
            'original_quantity', 'price', 'average_price', 'order_status',
            'order_last_filled_quantity', 'order_filled_accumulated_quantity',
            'order_trade_time', 'usd_size'
        ]) + "\n")
        
        

async def binance_liquidations(uri, filename):
    async with connect(uri) as websocket:
        while True:
            try:
                msg = await websocket.recv()
                order_data = json.loads(msg)['o']
                symbol = order_data['s'].replace('USDT', '')
                side = order_data['S']
                timestamp = int(order_data['z'])
                filled_quantity = float(order_data['z'])
                price = float(order_data['p'])
                usd_size = filled_quantity * price
                #Use kenyan time
                est = pytz.timezone("Africa/Nairobi")
                time_est = datetime.fromtimestamp(timestamp / 1000, est).strftime('%H:%M:%S')
                if usd_size > 3000:
                    liquidation_type = 'L LIQ' if side == 'SELL' else 'S LIQ'
                    symbol = symbol[:4]
                    output = f"{liquidation_type} {symbol} {time_est} {usd_size:.0f}"
                    color = 'green' if side == 'SELL' else 'red'
                    attrs = ['bold'] if usd_size > 1000 else []
                    
                    if usd_size > 25000:
                        stars = '*' * 3
                        attrs.append('blink')
                        output = f'{stars}{output}'
                        for  _ in range(4):
                            cprint(output, 'white', f'on_{color}', attrs=attrs)
                    elif usd_size > 100000:
                        starts = '*' *1
                        attrs.append('blink')
                        output = f'{stars}{output}'
                        for  _ in range(2):
                            cprint(output, 'white', f'on_{color}', attrs=attrs)
                    elif usd_size > 25000:
                        cprint(output, 'white', f'on_{color}')
                    
                    print('')
                    
                msg_values = [str(order_data.get(key) for key in ['s', 'S', 'o', 'f', 'q', 'p', 'ap', 'X', 'l', 'z'])]
                
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await asyncio.sleep(5)
                
                
                

