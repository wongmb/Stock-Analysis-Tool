import json
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import yfinance as yf
import os
from groq import Groq
from currency_converter import CurrencyConverter

c = CurrencyConverter()

client = Groq(
    api_key = st.secrets.api.key,
    )

# Define Streamlit Interface
st.set_page_config(page_title = "Stock Analysis", layout = "wide")
st.markdown("<h1 style='text-align: center;'>Stock Analysis Tool</h1>", unsafe_allow_html = True)

# Get stock price function for AI
def get_stock_price(ticker):
    try:
        stockData = yf.Ticker(ticker).history(period = "1d")
        todaysData = stockData.Close.iloc[-1]
        return todaysData
    
    except Exception as e:
        st.write("Error fetching stock price: Please enter a valid Company name")
        return None

# Other functions
def calculate_SMA(window):
    data = yf.Ticker(st.session_state.ticker).history(period = "1y").Close
    return (str(data.rolling(window = window).mean().iloc[-1]))

def calculate_EMA(window):
    data = yf.Ticker(st.session_state.ticker).history(period = "1y").Close
    return (str(data.ewm(span = window, adjust = False).mean().iloc[-1]))
 
def calculate_RSI():
    data = yf.Ticker(st.session_state.ticker).history(period = "1y").Close
    delta = data.diff()
    up = delta.clip(lower = 0)
    down = -1 * delta.clip(upper = 0)
    ema_up = up.ewm(com=14 - 1, adjust = False).mean()
    ema_down = down.ewm(com=14 - 1, adjust = False).mean()
    rs = ema_up / ema_down
    return str(100 - (100 / (1 + rs)).iloc[-1])

def calculate_MACD():
    data = yf.Ticker(st.session_state.ticker).history(period = "1y").Close
    short_EMA = data.ewm(span = 12, adjust = False).mean()
    long_EMA = data.ewm(span = 26, adjust = False).mean()
    MACD = short_EMA - long_EMA
    signal = MACD.ewm(span = 9, adjust = False).mean()
    MACD_histogram = MACD - signal
    return (f"{MACD[-1]}, {signal[-1]}, {MACD_histogram[-1]}")

def plot_stock_price():
    data = yf.Ticker(st.session_state.ticker).history(period = "1y")
    plt.figure(figsize = (10, 5))
    plt.plot(data.index, data.Close)
    plt.title(f"{st.session_state.ticker} Stock Price Over Last Year")
    plt.xlabel("Date")
    plt.ylabel("Stock Price ($)")
    plt.legend()
    plt.grid(True)
    plt.savefig("stock.png")
    plt.close()
    
functions = [
    {
        "name": "get_stock_price",
        "description": "Gets the latest stock price given the ticker symbol of a company.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The stock ticker symbol for a company (for example AAPL for Apple).",
                }
            },
            "required": ["ticker"],
        },
    },
]

available_functions = {
    "get_stock_price": get_stock_price,
}

if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "currency" not in st.session_state:
    st.session_state.currency = "USD"
    
with st.sidebar:
    user_input = st.text_input("Enter a Company Stock:", placeholder="e.g., Apple")
    currencySelected = st.selectbox("Select Currency:", options=[
        "$ USD - US Dollar", "$ CAD - Canadian Dollar", "€ EUR - Euro",
        "£ GBP - British Pound", "$ AUD - Australian Dollar", "¥ JPY - Japanese Yen",
        "₹ INR - Indian Rupee", "$ NZD - New Zealand Dollar", "₣ CHF - Swiss Franc",
        "$ SGD - Singapore Dollar", "$ HKD - Hong Kong Dollar", "₩ KRW - South Korean Won"
    ])
    show_plot = st.checkbox("Display Plot of Price 📈")
    show_EMA = st.checkbox("Display EMA (Exponential Moving Average)")
    show_SMA = st.checkbox("Display SMA (Simple Moving Average)")
    show_rsi = st.checkbox("Display RSI (Relative Strength Index)")
    show_macd = st.checkbox("Display MACD (Moving Average Convergence/Divergence)")

if user_input:
    try:
        st.session_state.messages.append({'role': 'user', 'content': user_input})
        
        response = client.chat.completions.create(
            messages = st.session_state.messages,
            model = 'llama3-8b-8192',
            functions = functions,
            function_call = 'auto'
        )

        response_message = response.choices[0].message
        
        if hasattr(response_message, 'function_call'):
            function_call = response_message.function_call
            if function_call:
                function_name = function_call.name
                function_args = json.loads(function_call.arguments)
                ticker = function_args.get('ticker')
                        
                # Call the appropriate function
                if function_name in available_functions:
                    function_to_call = available_functions[function_name]
                    st.session_state.function_response = get_stock_price(ticker)
                    
                    if st.session_state.function_response != None:
                        st.session_state.ticker = ticker
                        ticker = yf.Ticker(ticker)
                        st.session_state.companyName = ticker.info['longName']
                    
                        if "currency" in st.session_state:
                            st.session_state.stockPrice = c.convert(round(st.session_state.function_response, 2), "USD", st.session_state.currency)
                        else:
                            st.session_state.stockPrice = round(st.session_state.function_response, 2)

                else:
                    st.text("Invalid company")
         
        else:
            st.text("ERROR", response_message.content)

    except Exception as e:
        st.write("Error fetching stock price: Please enter a valid Company name")
        
if "function_response" in st.session_state and st.session_state.function_response != None:    
    currency = currencySelected.split(" ")

    st.session_state.stockPrice = round(c.convert(st.session_state.stockPrice, st.session_state.currency, currency[1]), 2)
    st.session_state.currency = currency[1]
    st.session_state.currencySymbol = currency[0]
    
    st.metric(label = "Current Stock Price of " + st.session_state.ticker + " - " + st.session_state.companyName, value=f"{st.session_state.currencySymbol} {st.session_state.stockPrice}", delta="Change Info")
    
    if show_plot:
        plot_stock_price()
        st.image('stock.png')
        
    if show_EMA:
        st.write("EMA:", calculate_EMA(30))
        
    if show_SMA:
        st.write("SMA:", calculate_SMA(30))

    if show_rsi:
        st.write("RSI:", calculate_RSI())

    if show_macd:
        st.write("MACD:", calculate_MACD())
        