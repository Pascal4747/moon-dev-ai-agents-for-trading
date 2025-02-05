import asyncio
import json
import os 
from datetime import datetime
import pytz
from websockets import connect 
from termcolor import cprint
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# lIst of sysmbols I want to track  
sysmbols = ['btcusdt', 'ethusdt', 'solusdt', 'dogeusdt', 'wifusdt']

websocket_url_base = 'wss://fstream.binance.com/ws/'

trades_filename = 'trades.csv'

# Check if  the csv file existt
if not os.path.exists(trades_filename):
    with open(trades_filename, 'w') as f:
        f.write('Event Time, Symbol, Aggregate Trade ID, Price, Quantity, First Trade ID, Trade Time, Is Buyer Maker, X\n')


class TradeAggregatetor:
    def __init__(self):
        self.trade_buckets = {}
         
    async def add_trade(self, sysmbol, second, usd_size, is_buyer_maker):
        trade_key = (sysmbol, second, is_buyer_maker)
        self.trade_buckets[trade_key] = self.trade_buckets.get(trade_key, 0) + usd_size
    
    async def check_and_print_trades(self):
        timestamp_now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        deletetions = []
        for trade_key, total_usd in self.trade_buckets.items():
            sysmbol, second, is_buyer_maker = trade_key
            if second < timestamp_now and total_usd > 5000000:
                attrs = ['bold']
                back_color = 'on_blue' if not is_buyer_maker else 'on_magenta'
                trade_type = "BUY" if not is_buyer_maker else "SELL"
                if total_usd >= 3000000:
                    display_usd = total_usd / 1000000
                    cprint(f"\033[5m{trade_type} {sysmbol} {second} ${display_usd:.2f}m\033[0m", 'white', back_color, attrs=attrs)
                else:
                    display_usd = total_usd / 1000000
                    cprint(f"{trade_type} {sysmbol} {second} ${display_usd:.2f}m", 'white', back_color, attrs=attrs)
                deletetions.append(trade_key)
                
        for key in deletetions:
            del self.trade_buckets[key]

trade_aggregator = TradeAggregatetor()

async def binance_trade_stream(uri, sysmbol, filename, aggregator):
    stream_url = f"{uri}{sysmbol}@aggTrade"
    logger.info(f"Connecting to {stream_url}")
    
    async with connect(stream_url) as ws:
        logger.info(f"Connected to {sysmbol} trade stream")
        while True:
            try:
                message = await ws.recv()
                data = json.loads(message)
                price = float(data['p'])
                quantity = float(data['q'])
                usd_size = price * quantity
                is_buyer_maker = data['m']
                
                # use kenyan timezone
                trade_time = datetime.fromtimestamp(data['E'] / 1000, pytz.timezone('Africa/Nairobi'))
                readable_time = trade_time.strftime('%Y-%m-%d %H:%M:%S')
                display_sysmbol = sysmbol.upper().replace('USDT', '')

                # Show trades above $500,000
                if usd_size > 500000:
                    trade_type = 'SELL' if is_buyer_maker else 'BUY'
                    display_usd = usd_size / 1000000
                    
                    # Different formatting for trades over 1M
                    if usd_size > 1000000:
                        color = 'magenta' if trade_type == 'SELL' else 'blue'
                        output = f"** {trade_type} {display_sysmbol} {readable_time} ${display_usd:.2f}M"
                    else:
                        color = 'red' if trade_type == 'SELL' else 'green'
                        output = f"* {trade_type} {display_sysmbol} {readable_time} ${display_usd:.2f}M"
                    
                    cprint(output, 'white', 'on_' + color, attrs=['bold'])
                
                # Still aggregate for huge trades
                await aggregator.add_trade(display_sysmbol, readable_time, usd_size, is_buyer_maker)
                
            except Exception as e:
                logger.error(f"Error processing {sysmbol} trade: {str(e)}")
                await asyncio.sleep(5)

async def print_aggregator_trades_every_sec(aggregator):
    while True:
        await asyncio.sleep(1)
        await aggregator.check_and_print_trades()
    

async def main():
    filename = "trades_big.csv"
    # Fix URL construction - don't include symbol in base URL
    trade_stream_tasks = [binance_trade_stream(websocket_url_base, sysmbol, filename, trade_aggregator) for sysmbol in sysmbols]
    print_tasks = asyncio.create_task(print_aggregator_trades_every_sec(trade_aggregator))
    
    logger.info("Starting trade monitoring...")
    await asyncio.gather(*trade_stream_tasks, print_tasks)

if __name__ == "__main__":
    try:
        print("🐋 Starting whale trade tracking...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        

            


            
            
                
        
