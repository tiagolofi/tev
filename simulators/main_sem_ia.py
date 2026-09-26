import yfinance as yf
import pandas as pd
import numpy as np


TICKER = "BBAS3.SA"
INTERVAL = "5m"

# Parâmetros
N = 30

# Caso 2
BUY_RANGE = 0.20
SELL_RANGE = 0.80

# Caso 3
BUY_RETURN = -0.03
SELL_RETURN = 0.03

# Caso 6
Z_BUY = -2.0
Z_SELL = 2.0


def load_data():
    df = yf.download(
        TICKER,
        period="5d",
        interval=INTERVAL,
        auto_adjust=True,
        progress=False
    )

    if df.empty:
        raise RuntimeError("Nenhum dado retornado pelo Yahoo Finance.")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()

    return df


# ============================================================
# 2. DISTÂNCIA DO MÍNIMO RECENTE
# ============================================================

def strategy_2(df):
    data = df.copy()

    data["min"] = data["Close"].rolling(N).min()
    data["range_from_min"] = (
        (data["Close"] - data["min"]) /
        data["min"]
    )

    position = False
    buy_price = None
    trades = []

    for index, row in data.iterrows():

        if pd.isna(row["range_from_min"]):
            continue

        # Compra próxima ao mínimo da janela
        if not position and row["range_from_min"] <= BUY_RANGE:

            position = True
            buy_price = row["Close"]

            trades.append({
                "time": index,
                "action": "BUY",
                "price": buy_price
            })

        # Venda após recuperação
        elif position:

            gain = row["Close"] / buy_price - 1

            if gain >= SELL_RETURN:

                position = False

                trades.append({
                    "time": index,
                    "action": "SELL",
                    "price": row["Close"],
                    "return": gain
                })

    return pd.DataFrame(trades)


# ============================================================
# 3. POSIÇÃO DENTRO DA FAIXA
# ============================================================

def strategy_3(df):
    data = df.copy()

    data["min"] = data["Close"].rolling(N).min()
    data["max"] = data["Close"].rolling(N).max()

    data["range_position"] = (
        (data["Close"] - data["min"]) /
        (data["max"] - data["min"])
    )

    position = False
    buy_price = None
    trades = []

    for index, row in data.iterrows():

        if pd.isna(row["range_position"]):
            continue

        if not position and row["range_position"] <= BUY_RANGE:

            position = True
            buy_price = row["Close"]

            trades.append({
                "time": index,
                "action": "BUY",
                "price": buy_price
            })

        elif position and row["range_position"] >= SELL_RANGE:

            position = False

            gain = row["Close"] / buy_price - 1

            trades.append({
                "time": index,
                "action": "SELL",
                "price": row["Close"],
                "return": gain
            })

    return pd.DataFrame(trades)


# ============================================================
# 6. Z-SCORE DO PREÇO
# ============================================================

def strategy_6(df):
    data = df.copy()

    data["mean"] = data["Close"].rolling(N).mean()
    data["std"] = data["Close"].rolling(N).std()

    data["zscore"] = (
        (data["Close"] - data["mean"]) /
        data["std"]
    )

    position = False
    buy_price = None
    trades = []

    for index, row in data.iterrows():

        if pd.isna(row["zscore"]):
            continue

        # Preço muito abaixo do comportamento recente
        if not position and row["zscore"] <= Z_BUY:

            position = True
            buy_price = row["Close"]

            trades.append({
                "time": index,
                "action": "BUY",
                "price": buy_price,
                "zscore": row["zscore"]
            })

        # Preço muito acima do comportamento recente
        elif position and row["zscore"] >= Z_SELL:

            position = False

            gain = row["Close"] / buy_price - 1

            trades.append({
                "time": index,
                "action": "SELL",
                "price": row["Close"],
                "return": gain,
                "zscore": row["zscore"]
            })

    return pd.DataFrame(trades)


# ============================================================
# 8. BARATO DEPENDENTE DA MAGNITUDE E VELOCIDADE DA QUEDA
# ============================================================

def strategy_8(df):
    data = df.copy()

    data["max"] = data["Close"].rolling(N).max()

    # Queda percentual desde o máximo recente
    data["drawdown"] = (
        data["Close"] / data["max"] - 1
    )

    # Retorno do último candle
    data["velocity"] = (
        data["Close"].pct_change()
    )

    # Quanto maior a queda e maior a velocidade,
    # maior o valor de "barato"
    data["cheap_score"] = (
        -data["drawdown"] *
        (1 + -data["velocity"])
    )

    position = False
    buy_price = None
    trades = []

    BUY_SCORE = 0.03
    SELL_RETURN = 0.03

    for index, row in data.iterrows():

        if pd.isna(row["cheap_score"]):
            continue

        if not position and row["cheap_score"] >= BUY_SCORE:

            position = True
            buy_price = row["Close"]

            trades.append({
                "time": index,
                "action": "BUY",
                "price": buy_price,
                "cheap_score": row["cheap_score"]
            })

        elif position:

            gain = row["Close"] / buy_price - 1

            if gain >= SELL_RETURN:

                position = False

                trades.append({
                    "time": index,
                    "action": "SELL",
                    "price": row["Close"],
                    "return": gain
                })

    return pd.DataFrame(trades)


# ============================================================
# RESULTADOS
# ============================================================

def summarize(name, trades):

    print("\n" + "=" * 60)
    print(name)
    print("=" * 60)

    if trades.empty:
        print("Nenhuma operação.")
        return

    sells = trades[trades["action"] == "SELL"]

    if sells.empty:
        print("Nenhuma operação encerrada.")
        return

    total_return = (1 + sells["return"]).prod() - 1
    wins = (sells["return"] > 0).sum()

    print(f"Operações encerradas : {len(sells)}")
    print(f"Operações positivas  : {wins}")
    print(f"Taxa de acerto       : {wins / len(sells):.2%}")
    print(f"Retorno acumulado    : {total_return:.2%}")
    print()
    print(sells.to_string(index=False))


def main():

    df = load_data()

    print(f"Ativo: {TICKER}")
    print(f"Período: últimos 5 dias")
    print(f"Intervalo: {INTERVAL}")
    print(f"Candles: {len(df)}")

    summarize(
        "ESTRATÉGIA 2 - DISTÂNCIA DO MÍNIMO",
        strategy_2(df)
    )

    summarize(
        "ESTRATÉGIA 3 - POSIÇÃO NA FAIXA",
        strategy_3(df)
    )

    summarize(
        "ESTRATÉGIA 6 - Z-SCORE",
        strategy_6(df)
    )

    summarize(
        "ESTRATÉGIA 8 - MAGNITUDE + VELOCIDADE",
        strategy_8(df)
    )


if __name__ == "__main__":
    main()