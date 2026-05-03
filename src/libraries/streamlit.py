import streamlit as st
from snowflake.snowpark.context import get_active_session
import snowflake.permissions as permission
from sys import exit
from udf import calculate_rsi, calculate_ma
import datetime
import pandas as pd

st.set_page_config(layout="wide")
session = get_active_session()

# Reference 연결 확인 및 정보 가져오기
stock_price_reference_associations = permission.get_reference_associations("stock_price")
if len(stock_price_reference_associations) == 0:
    permission.request_reference("stock_price")
    exit(0)
stock_price = "reference('stock_price')"

st.title(f"Stock Price Visualization")

# 날짜 세팅
latest_date_query = f"""
    SELECT MAX(DATE) FROM {stock_price}
"""
lodest_date_query = f"""
    SELECT MIN(DATE) FROM {stock_price}
"""
latest_date_row = session.sql(latest_date_query).collect()
oldest_date_row = session.sql(lodest_date_query).collect()


end_date = latest_date_row[0][0]
time_options = {
    "1 week": 7,
    "1 month": 30,
    "3 month": 90,
    "1 year": 365,
    "3 year": 365*3,
    "5 year": 365*5,
    "all": None
}

selected_label = st.sidebar.radio(
    "Select duration",
    options = list(time_options.keys()),
    horizontal = True,
    index = 2 # 기본 3month
)

if selected_label == "all":
    start_date = oldest_date_row[0][0] # 아주 오래전 날짜로 설정
else:
    days_to_subtract = time_options[selected_label]
    start_date = end_date - datetime.timedelta(days=days_to_subtract)
st.write(f"Start date: {start_date} ~ End date: {end_date}")

with st.spinner("Please wait..."):
    query = f"""
    SELECT
        s1.date as "DATE",
        s1.close as "CLOSE",
        s1.high as "HIGH",
        s1.low as "LOW",
        s1.open as "OPEN",
        s1.volume as "VOLUME"
    FROM {stock_price} as s1
    ORDER BY "DATE" ASC
    """
    stock_df = session.sql(query).to_pandas()
    stock_df['RSI'] = calculate_rsi(stock_df['CLOSE'], window=14)
    stock_df['MA'] = calculate_ma(stock_df['CLOSE'], window=20)

    # 상단 알림 표시 (RSI Metric)
    current_rsi = stock_df['RSI'].iloc[-1]

    if current_rsi >= 70:
        status = "과매수 (Overhought)"
        data_color = "inverse" # 빨간색 계열
    elif current_rsi <= 30:
        status = "과매도 (Oversold)"
        dalta_color = "normal" # 초록색 계열
    else:
        status = "중립 (Neutral)"
        delta_color = "off"
    
    st.columns(3)[0].metric(
        label = "Current RSI",
        value = f"{current_rsi:.2f}",
        delta = status,
        delta_color = delta_color
    )


    stock_df['DATE'] = pd.to_datetime(stock_df['DATE'])    
    mask = (stock_df['DATE'].dt.date >= start_date) & (stock_df['DATE'].dt.date <= end_date)
    filtered_df = stock_df.loc[mask].copy()
    st.dataframe(filtered_df)

    # close & ma
    st.write(f"### Close Price & MA:blue[20]")
    st.line_chart(filtered_df.set_index("DATE")[["CLOSE", "MA"]])

    # rsi
    rsi_df = filtered_df.set_index("DATE")[["RSI"]].copy()
    rsi_df['Overbought(70)'] = 70
    rsi_df['Oversold(30)'] = 30
    st.write("### RSI:blue[14] (Relative Strength Index)")
    st.line_chart(rsi_df, color=["#0072f0", "#ff4b4b", "#8884d8"])

