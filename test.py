import gradio as gr
import yfinance as yf
import matplotlib.pyplot as plt

def get_combined_market_data(period):
    # Using VNM (VanEck Vietnam ETF) as a proxy since ^VNINDEX is sometimes unreliable in yfinance
    tickers = {
        "BTC": "BTC-USD", 
        "Gold": "GC=F", 
        "Oil": "CL=F",
        "S&P 500": "SPY",
        "10Y Treasury": "^TNX",
        "USD Index": "DX-Y.NYB",
        "Vietnam ETF (VNM)": "VNM",
        "USD/VND": "VND=X"
    }
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    for name, ticker in tickers.items():
        data = yf.download(ticker, period=period)
        if not data.empty:
            close_data = data["Close"]
            if len(close_data.shape) > 1:
                close_data = close_data.iloc[:, 0]
            
            # Normalize data: (Price / Initial_Price) * 100
            start_price = close_data.iloc[0]
            if start_price != 0:
                normalized_data = (close_data / start_price) * 100
                ax.plot(normalized_data, label=f"{name}")
        
    ax.set_title(f"Market Trend Comparison (Normalized, Period: {period})")
    ax.set_xlabel("Time")
    ax.set_ylabel("Price Index (Start = 100)")
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.grid(True)
    plt.tight_layout()
    
    return fig

with gr.Blocks() as demo:
    gr.Markdown("# Comprehensive Market Trend Comparison (Vietnam Context)")
    gr.Markdown("Comparing global assets with Vietnam ETF (VNM), normalized to Base=100.")
    
    period_dropdown = gr.Dropdown(
        choices=["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"],
        value="1mo",
        label="Select Time Period"
    )
    combined_plot = gr.Plot(label="Market Indicators")
    
    period_dropdown.change(get_combined_market_data, inputs=period_dropdown, outputs=combined_plot)
    demo.load(get_combined_market_data, inputs=period_dropdown, outputs=combined_plot)

if __name__ == "__main__":
    demo.launch()
