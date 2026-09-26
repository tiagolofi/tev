import yfinance as yf
import pandas as pd
import requests
import time


# ============================================================
# CONFIGURAÇÃO
# ============================================================

TICKER = "VALE3.SA"
INTERVAL = "5m"
WINDOW = 30

JEV_URL = "http://localhost:8080/tev/inference?type=trading"

BUY_RANGE = 0.20
SELL_RANGE = 0.80

Z_BUY = -2.0
Z_SELL = 2.0

BUY_SCORE = 0.03
SELL_RETURN = 0.03


# ============================================================
# PROMPTS
# ============================================================

PROMPT_2 = """
Você recebe o preço atual e o menor preço observado na janela recente.

Calcule:

distancia = (preco - minimo) / minimo

Sem posição:
se a distância estiver suficientemente próxima do mínimo, considere COMPRA.

Com posição:
se o preço estiver suficientemente acima do preço de compra, considere VENDA.

Caso contrário, MANTER.

Não use indicadores técnicos, notícias ou previsão.
Analise exclusivamente a relação entre preço atual, mínimo recente e preço de compra.

Retorne exclusivamente um JSON válido no formato:

{
  "decision": "COMPRA|VENDA|MANTER",
  "confidence": 0.0
}

confidence deve representar a confiança da decisão em percentual, entre 0 e 100.
Não escreva explicações, markdown ou qualquer outro texto.
""".strip()


PROMPT_3 = """
Você recebe:

preço atual
mínimo da janela
máximo da janela
preço de compra, se existir

Calcule:

posicao = (preco - minimo) / (maximo - minimo)

Interprete:
posicao próxima de 0 = região inferior da faixa
posicao próxima de 1 = região superior da faixa

Sem posição:
se estiver na região inferior, considere COMPRA.

Com posição:
se estiver na região superior, considere VENDA.

Caso contrário:
MANTER.

Não use indicadores, notícias ou previsão.
Use somente os preços fornecidos.

Retorne exclusivamente um JSON válido no formato:

{
  "decision": "COMPRA|VENDA|MANTER",
  "confidence": 0.0
}

confidence deve representar a confiança da decisão em percentual, entre 0 e 100.
Não escreva explicações, markdown ou qualquer outro texto.
""".strip()


PROMPT_6 = """
Você recebe:

preço atual
média dos preços da janela
desvio-padrão dos preços
preço de compra, se existir

Calcule:

z = (preço atual - média) / desvio-padrão

Um z muito negativo significa que o preço está muito abaixo
do comportamento recente.

Um z muito positivo significa que está muito acima.

Sem posição:
se z <= -2, considere COMPRA.

Com posição:
se z >= 2, considere VENDA.

Caso contrário:
MANTER.

Não use outros indicadores, notícias ou previsão.
Use exclusivamente os valores fornecidos.

Retorne exclusivamente um JSON válido no formato:

{
  "decision": "COMPRA|VENDA|MANTER",
  "confidence": 0.0
}

confidence deve representar a confiança da decisão em percentual, entre 0 e 100.
Não escreva explicações, markdown ou qualquer outro texto.
""".strip()


PROMPT_8 = """
Você recebe:

preço atual
máximo recente
variação percentual do último candle
preço de compra, se existir

Calcule:

queda = preço atual / máximo recente - 1

score = -queda * (1 - variação)

Quanto maior o score, maior a combinação de:
queda acumulada + velocidade da queda.

Sem posição:
se o score superar o limite de compra, considere COMPRA.

Com posição:
se o preço atingir o retorno-alvo sobre o preço de compra,
considere VENDA.

Caso contrário:
MANTER.

Não use indicadores técnicos, notícias ou previsão.
Use exclusivamente o comportamento do preço.

Retorne exclusivamente um JSON válido no formato:

{
  "decision": "COMPRA|VENDA|MANTER",
  "confidence": 0.0
}

confidence deve representar a confiança da decisão em percentual, entre 0 e 100.
Não escreva explicações, markdown ou qualquer outro texto.
""".strip()


# ============================================================
# YFINANCE
# ============================================================

def load_data():

    df = yf.download(
        TICKER,
        period="1d",
        interval=INTERVAL,
        auto_adjust=True,
        progress=False
    )

    if df.empty:
        raise RuntimeError("Nenhum dado retornado pelo Yahoo Finance.")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    return df[
        ["Open", "High", "Low", "Close", "Volume"]
    ].dropna()


# ============================================================
# JEV
# ============================================================

def jev_inference(prompt: str, data: dict) -> dict:

    data_text = "\n".join(
        f"- {key}: {value}"
        for key, value in data.items()
    )

    body = (
        f"{prompt}\n\n"
        f"--- DADOS DA OPERAÇÃO ---\n"
        f"{data_text}\n"
        f"--- FIM DOS DADOS ---"
    )

    response = requests.post(
        JEV_URL,
        data=body,
        headers={
            "Content-Type": "text/plain; charset=utf-8"
        },
        timeout=30
    )

    response.raise_for_status()

    return response.json()

# ============================================================
# NORMALIZA RESPOSTA DO JEV
# ============================================================

def extract_decision(response):

    # Caso o JEV retorne:
    #
    # {"decision": "COMPRA"}
    #
    if isinstance(response, dict):

        if "decision" in response:
            return str(response["decision"]).upper()

        if "response" in response:
            return str(response["response"]).upper()

        if "result" in response:
            return str(response["result"]).upper()

    return str(response).upper()


# ============================================================
# ESTRATÉGIA 2
# ============================================================

def build_case_2(df):

    data = df.copy()

    data["min"] = data["Close"].rolling(WINDOW).min()

    data["distance"] = (
        (data["Close"] - data["min"]) /
        data["min"]
    )

    return data


# ============================================================
# ESTRATÉGIA 3
# ============================================================

def build_case_3(df):

    data = df.copy()

    data["min"] = data["Close"].rolling(WINDOW).min()
    data["max"] = data["Close"].rolling(WINDOW).max()

    data["range_position"] = (
        (data["Close"] - data["min"]) /
        (data["max"] - data["min"])
    )

    return data


# ============================================================
# ESTRATÉGIA 6
# ============================================================

def build_case_6(df):

    data = df.copy()

    data["mean"] = data["Close"].rolling(WINDOW).mean()
    data["std"] = data["Close"].rolling(WINDOW).std()

    data["zscore"] = (
        (data["Close"] - data["mean"]) /
        data["std"]
    )

    return data


# ============================================================
# ESTRATÉGIA 8
# ============================================================

def build_case_8(df):

    data = df.copy()

    data["max"] = data["Close"].rolling(WINDOW).max()

    data["drawdown"] = (
        data["Close"] / data["max"] - 1
    )

    data["velocity"] = data["Close"].pct_change()

    data["cheap_score"] = (
        -data["drawdown"] *
        (1 - data["velocity"])
    )

    return data


# ============================================================
# PAYLOADS
# ============================================================

def payload_case_2(row, buy_price):

    return {
        "price": float(row["Close"]),
        "minimum": float(row["min"]),
        "distance": float(row["distance"]),
        "buy_price": buy_price
    }


def payload_case_3(row, buy_price):

    return {
        "price": float(row["Close"]),
        "minimum": float(row["min"]),
        "maximum": float(row["max"]),
        "range_position": float(row["range_position"]),
        "buy_price": buy_price
    }


def payload_case_6(row, buy_price):

    return {
        "price": float(row["Close"]),
        "mean": float(row["mean"]),
        "std": float(row["std"]),
        "zscore": float(row["zscore"]),
        "buy_price": buy_price
    }


def payload_case_8(row, buy_price):

    return {
        "price": float(row["Close"]),
        "maximum": float(row["max"]),
        "drawdown": float(row["drawdown"]),
        "velocity": float(row["velocity"]),
        "cheap_score": float(row["cheap_score"]),
        "buy_price": buy_price,
        "sell_return": SELL_RETURN
    }


# ============================================================
# SIMULADOR
# ============================================================

def simulate(name, df, prompt, payload_builder):

    print()
    print("=" * 70)
    print(name)
    print("=" * 70)

    position = False
    buy_price = None

    trades = []

    for timestamp, row in df.iterrows():

        # Ainda não existe janela suficiente
        if pd.isna(row.get("min", None)) and \
           pd.isna(row.get("mean", None)) and \
           pd.isna(row.get("cheap_score", None)):

            continue

        try:

            payload = payload_builder(
                row,
                buy_price
            )

            response = jev_inference(
                prompt,
                payload
            )

            decision = response.get("decision", "ERRO").upper()
            confidence = float(response.get("confidence", 0))

            print(
                f"Decisão: {decision} | "
                f"Confiança: {confidence:.2f}%"
            )

        except Exception as e:

            print(
                f"[{timestamp}] "
                f"ERRO JEV: {e}"
            )

            continue

        price = float(row["Close"])

        print(
            f"{timestamp} | "
            f"R$ {price:.2f} | "
            f"{decision}"
        )

        # ----------------------------------------------------
        # COMPRA
        # ----------------------------------------------------

        if decision == "COMPRA" and not position:

            position = True
            buy_price = price

            trades.append({
                "time": timestamp,
                "action": "BUY",
                "price": price
            })

        # ----------------------------------------------------
        # VENDA
        # ----------------------------------------------------

        elif decision == "VENDA" and position:

            profit = (
                price / buy_price
            ) - 1

            trades.append({
                "time": timestamp,
                "action": "SELL",
                "price": price,
                "return": profit,
                "confidence": confidence
            })

            position = False
            buy_price = None

        # Evita sobrecarregar o servidor
        time.sleep(0.05)

    return pd.DataFrame(trades)


# ============================================================
# RESULTADO
# ============================================================

def summarize(name, trades):

    print()
    print("=" * 70)
    print(f"RESULTADO — {name}")
    print("=" * 70)

    if trades.empty:

        print("Nenhuma operação.")
        return

    sells = trades[
        trades["action"] == "SELL"
    ]

    if sells.empty:

        print("Nenhuma operação encerrada.")
        return

    returns = sells["return"]

    accumulated = (
        (1 + returns).prod()
    ) - 1

    wins = (
        returns > 0
    ).sum()

    print(
        f"Operações: {len(sells)}"
    )

    print(
        f"Acertos: {wins}"
    )

    print(
        f"Taxa de acerto: "
        f"{wins / len(sells):.2%}"
    )

    print(
        f"Retorno acumulado: "
        f"{accumulated:.2%}"
    )

    print()

    print(
        sells.to_string(index=False)
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("Carregando dados...")

    df = load_data()

    print(
        f"{TICKER} | "
        f"{len(df)} candles | "
        f"{INTERVAL}"
    )

    # --------------------------------------------------------
    # CONSTRÓI FEATURES
    # --------------------------------------------------------

    case_2 = build_case_2(df)
    case_3 = build_case_3(df)
    case_6 = build_case_6(df)
    case_8 = build_case_8(df)

    # --------------------------------------------------------
    # EXECUTA JEV
    # --------------------------------------------------------

    trades_2 = simulate(
        "CASO 2 — DISTÂNCIA DO MÍNIMO",
        case_2,
        PROMPT_2,
        payload_case_2
    )

    trades_3 = simulate(
        "CASO 3 — POSIÇÃO NA FAIXA",
        case_3,
        PROMPT_3,
        payload_case_3
    )

    trades_6 = simulate(
        "CASO 6 — Z-SCORE",
        case_6,
        PROMPT_6,
        payload_case_6
    )

    trades_8 = simulate(
        "CASO 8 — MAGNITUDE + VELOCIDADE",
        case_8,
        PROMPT_8,
        payload_case_8
    )

    # --------------------------------------------------------
    # RESULTADOS
    # --------------------------------------------------------

    summarize(
        "CASO 2",
        trades_2
    )

    summarize(
        "CASO 3",
        trades_3
    )

    summarize(
        "CASO 6",
        trades_6
    )

    summarize(
        "CASO 8",
        trades_8
    )


if __name__ == "__main__":
    main()