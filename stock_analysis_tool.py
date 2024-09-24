import json
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
st.set_page_config(page_title = "Stock Analysis", layout = "wide")

import yfinance as yf
import os
from groq import Groq
from currency_converter import CurrencyConverter

c = CurrencyConverter()

# Define Streamlit Interface
st.markdown("<h1 style='text-align: center;'>Stock Analysis Tool</h1>", unsafe_allow_html = True)

client = Groq(
    api_key = st.secrets.api.key,
    )

def get_stock_price(ticker):
    try:
        stockData = yf.Ticker(ticker).history(period=st.session_state.plotPeriod)
        st.session_state.firstPrice = stockData.Close.iloc[0]
                
        # Check if the DataFrame is empty
        if stockData.empty:
            st.write("No data found for the given ticker. Please enter a valid company name.")
            return None
        
        todaysData = stockData.Close.iloc[-1] 
        return todaysData
    
    except Exception as e:
        st.write(f"Error fetching stock price: {e}. Please enter a valid Company name.")
        return None

# Other functions
def calculate_SMA(window):
    return (round(st.session_state.data.rolling(window = window).mean().iloc[-1], 2))

def calculate_EMA(window):
    return (round(st.session_state.data.ewm(span = window, adjust = False).mean().iloc[-1], 2))
 
def calculate_RSI():
    delta = st.session_state.data.diff()
    up = delta.clip(lower = 0)
    down = -1 * delta.clip(upper = 0)
    ema_up = up.ewm(com=14 - 1, adjust = False).mean()
    ema_down = down.ewm(com=14 - 1, adjust = False).mean()
    rs = ema_up / ema_down
    return round(100 - (100 / (1 + rs)).iloc[-1], 2)

def calculate_MACD():
    short_EMA = st.session_state.data.ewm(span = 12, adjust = False).mean()
    long_EMA = st.session_state.data.ewm(span = 26, adjust = False).mean()
    MACD = short_EMA - long_EMA
    signal = MACD.ewm(span = 9, adjust = False).mean()
    MACD_histogram = MACD - signal
    MACD[-1] = round(MACD[-1], 2)
    signal[-1] = round(signal[-1], 2)
    MACD_histogram = round(MACD_histogram, 2)
    return (f"{MACD[-1]}, {signal[-1]}, {MACD_histogram[-1]}")

def plot_stock_price():
    data = yf.Ticker(st.session_state.ticker).history(period = st.session_state.plotPeriod)
    plt.figure(figsize = (10, 5))
    plt.plot(data.index, data.Close)
    if st.session_state.plotName == "All Time":
        plt.title(f"{st.session_state.companyName} Stock Price Over {st.session_state.plotName}")
    else:
        plt.title(f"{st.session_state.companyName} Stock Price Over Last {st.session_state.plotName}")
    plt.xlabel("Date")
    plt.ylabel("Stock Price ($ USD)")
    plt.legend()
    plt.grid(True)
    plt.savefig("stock.png")
    plt.close()

def calculatePercentageChange():
    priceChange = st.session_state.stockPrice - st.session_state.firstPrice
    percentageChange = (priceChange / st.session_state.firstPrice) * 100
    
    return round(percentageChange, 2)
    
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
    st.session_state.messages = []

if "currency" not in st.session_state:
    st.session_state.currency = "USD"

if "plotPeriod" not in st.session_state:
    st.session_state.plotPeriod = "1y"

if "plotName" not in st.session_state:
    st.session_state.plotName = "Year"

if "firstPrice" not in st.session_state:
    st.session_state.firstPrice = "None"
    
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
        st.write(f"Error fetching stock price: Please enter a valid Company name {e}")
        
if "function_response" in st.session_state and st.session_state.function_response != None:    
    st.session_state.data = yf.Ticker(st.session_state.ticker).history(period = "1y").Close

    currency = currencySelected.split(" ")
    st.session_state.stockPrice = round(c.convert(st.session_state.stockPrice, st.session_state.currency, currency[1]), 2)
    st.session_state.currency = currency[1]
    st.session_state.currencySymbol = currency[0]
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        if st.button("5D", help = "Change Time Period to 5 Days"):
            st.session_state.plotName = "5 Days"
            st.session_state.plotPeriod = "5d"
    with col2:
        if st.button("1M", help = "Change Time Period to 1 Month"):
            st.session_state.plotName = "Month"
            st.session_state.plotPeriod = "1mo"
    with col3:
        if st.button("6M", help = "Change Time Period to 6 Months"):
            st.session_state.plotName = "6 Months"
            st.session_state.plotPeriod = "6mo"
    with col4:
        if st.button("1Y", help = "Change Time Period to 1 Year"):
            st.session_state.plotName = "Year"
            st.session_state.plotPeriod = "1y"
    with col5:
        if st.button("5Y", help = "Change Time Period to 5 Years"):
            st.session_state.plotName = "5 Years"
            st.session_state.plotPeriod = "5y"
    with col6:
        if st.button("Max", help = "Change Time Period to All Time"):
            st.session_state.plotPeriod = "max"
            st.session_state.plotName = "All Time"

    get_stock_price(st.session_state.ticker)
    percentChange = calculatePercentageChange()
    
    st.metric(label = "Current Stock Price of " + st.session_state.ticker + " - " + st.session_state.companyName, value=f"{st.session_state.currencySymbol} {st.session_state.stockPrice}", delta=f"{percentChange}% Past {st.session_state.plotName}")
                
    if show_plot:
        plot_stock_price()
        st.image('stock.png')
        
    if show_EMA:
        st.write("EMA:", str(calculate_EMA(30)))
        
    if show_SMA:
        st.write("SMA:", str(calculate_SMA(30)))

    if show_rsi:
        st.write("RSI:", str(calculate_RSI()))

    if show_macd:
        st.write("MACD:", calculate_MACD())
        