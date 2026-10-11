import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(
    page_title="Aktie-dashboard",
    page_icon="📈",
    layout="wide",
)

WATCHLIST = {
    "Volvo B": "VOLV-B.ST",
    "Investor B": "INVE-B.ST",
    "Atlas Copco A": "ATCO-A.ST",
    "Apple": "AAPL",
    "Microsoft": "MSFT",
}


def format_number(value, decimals=2):
    if value is None or pd.isna(value):
        return "Saknas"
    return f"{value:.{decimals}f}"


def format_percent(value):
    if value is None or pd.isna(value):
        return "Saknas"
    if value > 1:
        return f"{value:.1f}%"
    return f"{value * 100:.1f}%"


def format_market_cap(value):
    if value is None or pd.isna(value):
        return "Saknas"
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f} md"
    return f"{value / 1_000_000:.1f} mn"


def get_trend_status(price, sma_50, sma_200):
    if pd.isna(sma_50) or pd.isna(sma_200):
        return "För lite data"
    if price > sma_50 and sma_50 > sma_200:
        return "Positiv"
    if price < sma_50 and sma_50 < sma_200:
        return "Negativ"
    return "Blandad"


def make_insight(stock_data):
    ticker = stock_data["ticker"]
    price = stock_data["price"]
    monthly_change = stock_data["monthly_change"]
    sma_50 = stock_data["sma_50"]
    sma_200 = stock_data["sma_200"]
    pe = stock_data["pe"]
    forward_pe = stock_data["forward_pe"]
    profit_margin = stock_data["profit_margin"]
    dividend_yield = stock_data["dividend_yield"]

    trend = get_trend_status(price, sma_50, sma_200)

    if trend == "Positiv":
        trend_text = (
            "Den tekniska bilden är positiv: kursen ligger över SMA 50 "
            "och SMA 50 ligger över SMA 200."
        )
    elif trend == "Negativ":
        trend_text = (
            "Den tekniska bilden är negativ: kursen ligger under SMA 50 "
            "och SMA 50 ligger under SMA 200."
        )
    else:
        trend_text = (
            "Den tekniska bilden är blandad: kurs och glidande medelvärden "
            "ger inte en tydlig gemensam riktning."
        )

    if monthly_change > 0:
        momentum_text = (
            f"Momentum är positivt: aktien har stigit "
            f"{monthly_change * 100:.1f}% den senaste månaden."
        )
    elif monthly_change < 0:
        momentum_text = (
            f"Momentum är negativt: aktien har fallit "
            f"{abs(monthly_change) * 100:.1f}% den senaste månaden."
        )
    else:
        momentum_text = "Momentum är neutralt den senaste månaden."

    if pe is None or pd.isna(pe):
        valuation_text = "P/E-tal saknas i datakällan."
    elif forward_pe is None or pd.isna(forward_pe):
        valuation_text = (
            f"Nuvarande P/E är {pe:.1f}, men forward P/E saknas."
        )
    elif forward_pe < pe:
        valuation_text = (
            f"Forward P/E ({forward_pe:.1f}) är lägre än nuvarande P/E "
            f"({pe:.1f}), vilket kan vara förenligt med förväntad "
            "vinsttillväxt."
        )
    else:
        valuation_text = (
            f"Forward P/E ({forward_pe:.1f}) är högre än nuvarande P/E "
            f"({pe:.1f}), vilket kan signalera lägre vinstförväntningar "
            "eller högre förväntad värdering."
        )

    if profit_margin is None or pd.isna(profit_margin):
        profitability_text = "Vinstmarginal saknas i datakällan."
    else:
        profitability_text = (
            f"Vinstmarginalen är {profit_margin * 100:.1f}%."
        )

    if dividend_yield is None or pd.isna(dividend_yield):
        dividend_text = "Direktavkastning saknas i datakällan."
    elif dividend_yield > 1:
        dividend_text = f"Direktavkastningen är {dividend_yield:.1f}%."
    else:
        dividend_text = (
            f"Direktavkastningen är {dividend_yield * 100:.1f}%."
        )

    return {
        "trend": trend_text,
        "momentum": momentum_text,
        "vardering": valuation_text,
        "lonsamhet": profitability_text,
        "utdelning": dividend_text,
    }


@st.cache_data(ttl=3600)
def load_watchlist(watchlist):
    rows = []

    for company, ticker in watchlist.items():
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period="1y")
            info = stock.info

            if data.empty or len(data) < 200:
                rows.append(
                    {
                        "Bolag": company,
                        "Ticker": ticker,
                        "Status": "För lite data",
                    }
                )
                continue

            data["SMA 50"] = data["Close"].rolling(50).mean()
            data["SMA 200"] = data["Close"].rolling(200).mean()

            price = data["Close"].iloc[-1]
            one_month_ago = data["Close"].iloc[-22]
            monthly_change = price / one_month_ago - 1
            sma_50 = data["SMA 50"].iloc[-1]
            sma_200 = data["SMA 200"].iloc[-1]

            rows.append(
                {
                    "Bolag": company,
                    "Ticker": ticker,
                    "Kurs": price,
                    "1M": monthly_change,
                    "Trend": get_trend_status(price, sma_50, sma_200),
                    "P/E": info.get("trailingPE"),
                    "Forward P/E": info.get("forwardPE"),
                    "Direktavkastning": info.get("dividendYield"),
                    "Status": "OK",
                }
            )

        except Exception:
            rows.append(
                {
                    "Bolag": company,
                    "Ticker": ticker,
                    "Status": "Kunde inte hämta data",
                }
            )

    return pd.DataFrame(rows)


st.title("📈 Aktie-dashboard")
st.write("Sök aktier, analysera trend och jämför en egen watchlist.")

tab_overview, tab_watchlist, tab_insights = st.tabs(
    ["Aktieöversikt", "Watchlist", "AI-insikter"]
)

with tab_overview:
    ticker = st.text_input("Skriv en aktieticker", "VOLV-B.ST")

    if st.button("Hämta kurs"):
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period="1y")
            info = stock.info

            if data.empty or len(data) < 200:
                st.error(
                    "Hittade inte tillräckligt med data. "
                    "Testa exempelvis AAPL eller VOLV-B.ST."
                )
            else:
                data["SMA 50"] = data["Close"].rolling(50).mean()
                data["SMA 200"] = data["Close"].rolling(200).mean()

                price = data["Close"].iloc[-1]
                one_month_ago = data["Close"].iloc[-22]
                monthly_change = price / one_month_ago - 1
                sma_50 = data["SMA 50"].iloc[-1]
                sma_200 = data["SMA 200"].iloc[-1]

                pe = info.get("trailingPE")
                forward_pe = info.get("forwardPE")
                peg = info.get("trailingPegRatio")
                profit_margin = info.get("profitMargins")
                dividend_yield = info.get("dividendYield")
                market_cap = info.get("marketCap")

                st.session_state["selected_stock"] = {
                    "ticker": ticker,
                    "price": price,
                    "monthly_change": monthly_change,
                    "sma_50": sma_50,
                    "sma_200": sma_200,
                    "pe": pe,
                    "forward_pe": forward_pe,
                    "profit_margin": profit_margin,
                    "dividend_yield": dividend_yield,
                }

                col1, col2, col3 = st.columns(3)

                col1.metric(
                    f"Senaste kurs för {ticker}",
                    f"{price:.2f}",
                    f"{monthly_change * 100:.1f}% senaste månaden",
                )
                col2.metric("SMA 50", f"{sma_50:.2f}")
                col3.metric("SMA 200", f"{sma_200:.2f}")

                st.subheader("Kursutveckling och trend")
                st.line_chart(data[["Close", "SMA 50", "SMA 200"]])

                trend = get_trend_status(price, sma_50, sma_200)

                if trend == "Positiv":
                    st.success(
                        "Positiv trend: kursen ligger över SMA 50 och "
                        "SMA 50 ligger över SMA 200."
                    )
                elif trend == "Negativ":
                    st.warning(
                        "Negativ trend: kursen ligger under SMA 50 och "
                        "SMA 50 ligger under SMA 200."
                    )
                else:
                    st.info(
                        "Blandad trend: kurs och glidande medelvärden "
                        "ger ingen helt tydlig signal."
                    )

                st.caption(
                    "SMA = Simple Moving Average. Indikatorerna beskriver "
                    "historisk prisutveckling och är inte investeringsråd."
                )

                st.divider()
                st.subheader("Fundamentala nyckeltal")

                col1, col2, col3 = st.columns(3)
                col1.metric("P/E", format_number(pe))
                col2.metric("Forward P/E", format_number(forward_pe))
                col3.metric("PEG", format_number(peg))

                col4, col5, col6 = st.columns(3)
                col4.metric("Vinstmarginal", format_percent(profit_margin))
                col5.metric(
                    "Direktavkastning",
                    format_percent(dividend_yield),
                )
                col6.metric("Börsvärde", format_market_cap(market_cap))

                st.caption(
                    "Fundamentala data kommer från Yahoo Finance via "
                    "yfinance. Data kan saknas eller vara fördröjda."
                )

        except Exception as error:
            st.error(f"Något gick fel: {error}")

with tab_watchlist:
    st.subheader("Min watchlist")
    st.write(
        "Jämför kursutveckling, trend och grundläggande "
        "värderingsmått för utvalda bolag."
    )

    if st.button("Uppdatera watchlist"):
        st.cache_data.clear()

    with st.spinner("Hämtar data för watchlist..."):
        watchlist_data = load_watchlist(WATCHLIST)

    if watchlist_data.empty:
        st.error("Kunde inte hämta data till watchlisten.")
    else:
        if "Kurs" in watchlist_data.columns:
            watchlist_data["Kurs"] = watchlist_data["Kurs"].apply(
                format_number
            )
            watchlist_data["1M"] = watchlist_data["1M"].apply(
                lambda value: (
                    f"{value * 100:.1f}%"
                    if pd.notna(value)
                    else "Saknas"
                )
            )
            watchlist_data["P/E"] = watchlist_data["P/E"].apply(
                format_number
            )
            watchlist_data["Forward P/E"] = watchlist_data[
                "Forward P/E"
            ].apply(format_number)
            watchlist_data["Direktavkastning"] = watchlist_data[
                "Direktavkastning"
            ].apply(format_percent)

        columns = [
            "Bolag",
            "Ticker",
            "Kurs",
            "1M",
            "Trend",
            "P/E",
            "Forward P/E",
            "Direktavkastning",
            "Status",
        ]

        visible_columns = [
            column for column in columns
            if column in watchlist_data.columns
        ]

        st.dataframe(
            watchlist_data[visible_columns],
            use_container_width=True,
            hide_index=True,
        )

    st.caption(
        "Watchlisten cache:as i upp till en timme. Klicka på "
        "“Uppdatera watchlist” för att hämta data på nytt."
    )

with tab_insights:
    st.subheader("AI-insikter")
    st.write(
        "En regelbaserad och datadriven sammanfattning av trend, momentum, "
        "värdering, lönsamhet och utdelning."
    )

    if "selected_stock" not in st.session_state:
        st.info(
            "Gå först till Aktieöversikt, välj en aktie och klicka "
            "på “Hämta kurs”."
        )
    else:
        stock_data = st.session_state["selected_stock"]
        insight = make_insight(stock_data)

        st.subheader(
            f"Automatisk analys för {stock_data['ticker']}"
        )

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Teknisk bild")
            st.write(insight["trend"])

            st.markdown("### Momentum")
            st.write(insight["momentum"])

            st.markdown("### Värdering")
            st.write(insight["vardering"])

        with col2:
            st.markdown("### Lönsamhet")
            st.write(insight["lonsamhet"])

            st.markdown("### Utdelning")
            st.write(insight["utdelning"])

        st.warning(
            "Begränsning: Analysen bygger på historisk kursdata och "
            "nyckeltal från Yahoo Finance. Den omfattar inte nyheter, "
            "rapporter, räntor, estimatrevideringar eller din egen "
            "risksituation. Detta är inte investeringsråd."
        )