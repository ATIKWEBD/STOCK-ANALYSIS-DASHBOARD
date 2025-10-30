import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- Page Configuration ---
st.set_page_config(
    page_title="Stock Market Analysis Dashboard",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Helper Functions ---

@st.cache_data(ttl=3600)
def get_stock_data(ticker_symbol, start_date, end_date):
    """Fetches historical stock data from Yahoo Finance."""
    try:
        stock_data = yf.download(ticker_symbol, start=start_date, end=end_date)
        if stock_data.empty:
            st.warning(f"No data found for {ticker_symbol}. It might be delisted or an incorrect ticker.")
            return None
        return stock_data
    except Exception as e:
        st.error(f"Error fetching data for {ticker_symbol}: {e}")
        return None

@st.cache_data(ttl=3600)
def scrape_market_news(url="https://economictimes.indiatimes.com/markets/stocks/news"):
    """Scrapes top market news headlines from a financial news website."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        stories = soup.find_all('div', class_='eachStory', limit=10)

        news_list = []
        for story in stories:
            headline_tag = story.find('h3')
            link_tag = story.find('a')

            if headline_tag and link_tag and 'href' in link_tag.attrs:
                headline = headline_tag.get_text(strip=True)
                link = "https://economictimes.indiatimes.com" + link_tag['href']
                news_list.append({"headline": headline, "link": link})
        return news_list
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to retrieve news. Error: {e}")
        return []
    except Exception as e:
        st.error(f"An error occurred during news scraping: {e}")
        return []

# --- UI Layout ---
with st.sidebar:
    st.image("https://placehold.co/400x200/000000/FFFFFF?text=Stock+Dashboard", use_column_width=True)
    st.title("📊 Analysis Controls")
    st.info("Enter an NSE/BSE ticker symbol. Append '.NS' for NSE stocks or '.BO' for BSE stocks (e.g., 'RELIANCE.NS').")

    ticker_input = st.text_input("Enter Stock Ticker:", "RELIANCE.NS").upper()

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", datetime.now() - timedelta(days=365))
    with col2:
        end_date = st.date_input("End Date", datetime.now())
        
    analyze_button = st.button("Analyze Stock", use_container_width=True, type="primary")

    st.markdown("---")
    st.header("Top Market News")
    news = scrape_market_news()
    if news:
        for item in news:
            st.markdown(f"**[{item['headline']}]({item['link']})**")
            st.markdown("---")
    else:
        st.warning("Could not fetch market news at the moment.")

# --- Main Dashboard ---
st.title("📈 Interactive Financial Dashboard")
st.markdown(f"#### Analyzing: **{ticker_input}** from **{start_date}** to **{end_date}**")

if analyze_button and ticker_input:
    with st.spinner('Fetching data and generating charts...'):
        data = get_stock_data(ticker_input, start_date, end_date)

    if data is not None and not data.empty:
        # --- Data Cleaning ---
        # FIX: Handle potential MultiIndex columns from yfinance by flattening them
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # Explicitly ensure columns are numeric for robust plotting
        numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in numeric_cols:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce')
        
        # Drop rows with all NaN values in the key columns
        data.dropna(subset=['Open', 'High', 'Low', 'Close'], how='all', inplace=True)
        
        if not data.empty:
            # --- Key Metrics ---
            st.subheader("Key Performance Metrics")
            col1, col2, col3, col4 = st.columns(4)

            try:
                latest_price = data['Close'].iloc[-1]
                col1.metric("Last Price (₹)", f"{latest_price:,.2f}")

                if len(data['Close']) > 1:
                    prev_price = data['Close'].iloc[-2]
                    price_change = latest_price - prev_price
                    percent_change = (price_change / prev_price) * 100
                    col2.metric("Change (₹)", f"{price_change:,.2f}", f"{percent_change:.2f}%")
                else:
                    col2.metric("Change (₹)", "N/A", "N/A")

                col3.metric("Period High (₹)", f"{data['High'].max():,.2f}")
                col4.metric("Period Low (₹)", f"{data['Low'].min():,.2f}")
            except (IndexError, TypeError, ValueError):
                st.error("Not enough data to calculate metrics.")
            
            st.markdown("<hr>", unsafe_allow_html=True)

            # --- Interactive Candlestick Chart ---
            st.subheader("Price Action: Candlestick Chart")
            fig = go.Figure(data=[go.Candlestick(
                x=data.index,
                open=data['Open'],
                high=data['High'],
                low=data['Low'],
                close=data['Close'],
                increasing_line_color='green',
                decreasing_line_color='red'
            )])
            
            fig.update_layout(
                title=f'{ticker_input} Price Movement',
                xaxis_title='Date',
                yaxis_title='Price (₹)',
                xaxis_rangeslider_visible=False,
                template='plotly_dark'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # --- Volume Analysis Chart ---
            st.subheader("Trading Volume Analysis")
            vol_fig = go.Figure()
            vol_fig.add_trace(go.Bar(
                x=data.index, 
                y=data['Volume'],
                marker_color='royalblue',
                name='Volume'
            ))
            vol_fig.update_layout(
                title=f'{ticker_input} Trading Volume Over Time',
                xaxis_title='Date',
                yaxis_title='Volume',
                template='plotly_dark'
            )
            st.plotly_chart(vol_fig, use_container_width=True)

            # --- Data Table ---
            st.subheader("Historical Data")
            st.dataframe(data.sort_index(ascending=False).style.format({
                'Open': '₹{:,.2f}',
                'High': '₹{:,.2f}',
                'Low': '₹{:,.2f}',
                'Close': '₹{:,.2f}',
                'Adj Close': '₹{:,.2f}',
                'Volume': '{:,}'
            }))

            csv = data.to_csv().encode('utf-8')
            st.download_button(
                label="Download Data as CSV",
                data=csv,
                file_name=f'{ticker_input}_data.csv',
                mime='text/csv',
                use_container_width=True
            )
        else:
            st.error("No valid data found after cleaning. Please check the ticker or date range.")
    else:
        # This message will show if get_stock_data returned None or an empty dataframe
        st.error("Could not retrieve data. Please confirm the ticker symbol and selected date range.")
else:
    st.info("Enter a stock ticker and click 'Analyze Stock' to see the dashboard.")