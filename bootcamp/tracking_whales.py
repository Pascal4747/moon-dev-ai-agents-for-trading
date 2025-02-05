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
websocket_url = 'wss://fstream.binance.com/ws/'

trades_filename = 'trades.csv'

# Check if the csv file exists
if not os.path.exists(trades_filename):
    with open(trades_filename, 'w') as f:
        f.write('Event Time, Symbol, Aggregate Trade ID, Price, Quantity, First Trade ID, Trade Time, Is Buyer Maker, X\n')

async def subscribe_to_streams(ws):
    """Subscribe to multiple streams in a single connection"""
    # Format stream names correctly for futures
    stream_names = [f"{symbol}@aggTrade" for symbol in symbols]
    
    # Send subscription message
    subscribe_msg = {
        "method": "SUBSCRIBE",
        "params": stream_names,
        "id": 1
    }
    
    logger.info(f"Subscribing to streams: {stream_names}")
    await ws.send(json.dumps(subscribe_msg))
    
    # Wait for subscription confirmation
    response = await ws.recv()
    logger.info(f"Subscription response: {response}")

async def process_trade(message, filename):
    """Process a single trade message"""
    try:
        # Parse the message
        if not message:
            return
            
        data = json.loads(message)
        
        # Skip non-trade messages
        if not isinstance(data, dict) or 'e' not in data or data['e'] != 'aggTrade':
            return
            
        # Extract trade data
        symbol = data['s'].lower()
        event_time = int(data['E'])
        agg_trade_id = int(data['a'])
        price = float(data['p'])
        quantity = float(data['q'])
        is_buyer_maker = data['m']
        
        est = pytz.timezone('Africa/Nairobi')
        readable_time = datetime.fromtimestamp(event_time / 1000, est).strftime('%Y-%m-%d %H:%M:%S')
        usd_size = price * quantity
        display_symbol = symbol.upper().replace('USDT', '')
        
        if usd_size > 14999:
            trade_type = 'SELL' if is_buyer_maker else 'BUY'
            color = 'red' if trade_type == 'SELL' else 'green'
            
            stars = ''
            attrs = ['bold'] if usd_size >= 500000 else []
            if usd_size >= 500000:
                stars = '*' * 2
                if trade_type == 'SELL':
                    color = 'magenta'
                else:
                    color = 'blue'
            elif usd_size >= 100000:
                stars = '*'
            
            output = f"{stars} {trade_type} {display_symbol} {readable_time} ${usd_size:,.0f}"
            cprint(output, 'white', 'on_' + color, attrs=attrs)
            
            # log to csv
            with open(filename, 'a') as f:
                f.write(f"{event_time}, {symbol}, {agg_trade_id}, {price}, {quantity}, {is_buyer_maker}, {readable_time}, {event_time}, {is_buyer_maker}\n")
    except Exception as e:
        logger.error(f"Error processing trade: {str(e)}")

async def handle_websocket():
    """Handle the WebSocket connection and message processing"""
    reconnect_delay = 5  # Start with 5 seconds delay
    max_reconnect_delay = 300  # Maximum delay of 5 minutes
    
    while True:
        try:
            logger.info("Connecting to Binance Futures WebSocket...")
            async with connect(websocket_url) as ws:
                # Subscribe to all streams
                await subscribe_to_streams(ws)
                logger.info("Successfully subscribed to all streams!")
                
                # Reset reconnect delay after successful connection
                reconnect_delay = 5
                
                # Start ping task
                ping_task = asyncio.create_task(send_ping(ws))
                
                while True:
                    try:
                        message = await ws.recv()
                        
                        # Process the message
                        await process_trade(message, trades_filename)
                            
                    except Exception as e:
                        logger.error(f"Error handling message: {str(e)}")
                        if "connection closed" in str(e).lower():
                            raise  # Break inner loop to reconnect
                        continue
                        
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
            await asyncio.sleep(reconnect_delay)
            # Implement exponential backoff
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
            continue

async def send_ping(ws):
    """Send periodic pings to keep connection alive"""
    while True:
        try:
            await asyncio.sleep(20)  # Send ping every 20 seconds
            await ws.send(json.dumps({
                "method": "PING",
                "id": 1
            }))
            logger.debug("Sent ping")
        except Exception as e:
            logger.error(f"Ping error: {str(e)}")
            break  # Stop ping task if connection is lost

async def main():
    logger.info("Starting trade monitoring...")
    await handle_websocket()

if __name__ == "__main__":
    try:
        print("🚀 Starting whale tracking...")
        logger.info("Initializing whale tracking system...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        logger.error(f"Fatal error: {str(e)}")