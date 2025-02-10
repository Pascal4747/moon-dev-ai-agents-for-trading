# connect exchange site
import ccxt
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

phemex = ccxt.phemex({
    'enableRateLimit': True,
    'apiKey': os.getenv('PHEMEX_API_KEY'),
    'secret': os.getenv('PHEMEX_SECRET_KEY')
})

bal = phemex.fetch_balance()
print(bal)

# making an order
symbol = 'UBTUSD'
size = 1
bid = 30000
params = {'timeInForce': 'PostOnly'}

order = phemex.creat_limit_buy_order(symbol, size, bid, params, )
print(order)

# cancelling an order
order_id = order['id']
phemex.cancel_order(order_id)


