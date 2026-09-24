import json
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
import yfinance as yf


# ============================================================
# CONFIGURAÇÃO
# ============================================================

TEV_URL = "http://localhost:8080/tev/inference?type=trading"

TICKER = "PETR4"

INITIAL_CASH = 1000

# Confiança mínima para executar uma operação
MIN_CONFIDENCE = 0.70

# Quantidade de dinheiro utilizada em cada compra.
# None = utiliza todo o cash disponível.
TRADE_VALUE = None

# Custo aproximado da operação.
# Exemplo: 0.0005 = 0,05%
TRANSACTION_COST = 0.0005

BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")


# ============================================================
# INDICADORES
# ============================================================

def calculate_rsi(close, period=14):
    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    return float(rsi.iloc[-1])


def calculate_atr(df, period=14):
    previous_close = df["Close"].shift(1)

    tr = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - previous_close).abs(),
            (df["Low"] - previous_close).abs()
        ],
        axis=1
    ).max(axis=1)

    atr = tr.rolling(period).mean()

    return float(atr.iloc[-1])


def calculate_vwap(df):
    typical_price = (
        df["High"] +
        df["Low"] +
        df["Close"]
    ) / 3

    return (
        (typical_price * df["Volume"]).cumsum()
        / df["Volume"].cumsum()
    )


def percentage_change(df, candles):
    if len(df) <= candles:
        return 0.0

    current = df["Close"].iloc[-1]
    previous = df["Close"].iloc[-candles - 1]

    return float((current / previous - 1) * 100)

def calculate_scores(market):
    direction = 0
    entry = 0
    risk = 0

    direction_factors = []
    entry_factors = []
    risk_factors = []

    price = market["preco"]
    vwap = market["vwap"]

    ema9 = market["ema9"]
    ema21 = market["ema21"]
    ema50 = market["ema50"]

    var5m = market["var5m%"]
    var15m = market["var15m%"]
    var1h = market["var1h%"]

    volume_relative = market["volume_relativo"]

    support = market["suporte"]
    resistance = market["resistencia"]

    atr = market["atr"]

    # ============================================================
    # SCORE DE DIREÇÃO
    # ============================================================

    # Tendência
    if ema9 > ema21 > ema50:
        direction += 2
        direction_factors.append("tendencia_alta")

    elif ema9 < ema21 < ema50:
        direction -= 2
        direction_factors.append("tendencia_baixa")

    # Momentum
    if var5m > 0 and var15m > 0 and var1h > 0:
        direction += 2
        direction_factors.append("momentum_positivo")

    elif var5m < 0 and var15m < 0 and var1h < 0:
        direction -= 2
        direction_factors.append("momentum_negativo")

    # VWAP
    if price > vwap:
        direction += 1
        direction_factors.append("preco_acima_vwap")

    elif price < vwap:
        direction -= 1
        direction_factors.append("preco_abaixo_vwap")

    # Volume
    if volume_relative >= 1.20:

        if price > vwap:
            direction += 1
            direction_factors.append("volume_confirmando_alta")

        elif price < vwap:
            direction -= 1
            direction_factors.append("volume_confirmando_baixa")


    # ============================================================
    # SCORE DE ENTRADA
    #
    # Positivo = entrada favorável para compra
    # Negativo = entrada favorável para venda
    # Próximo de zero = entrada ruim/indefinida
    # ============================================================

    # Distância da VWAP
    vwap_distance = (price - vwap) / vwap

    # Preço muito acima da VWAP
    if vwap_distance > 0.02:
        entry -= 2
        entry_factors.append("preco_estendido_acima_vwap")

    elif vwap_distance > 0.01:
        entry -= 1
        entry_factors.append("preco_distante_vwap")

    # Preço muito abaixo da VWAP
    elif vwap_distance < -0.02:
        entry += 2
        entry_factors.append("preco_estendido_abaixo_vwap")

    elif vwap_distance < -0.01:
        entry += 1
        entry_factors.append("preco_distante_vwap")


    # ============================================================
    # PROXIMIDADE DA RESISTÊNCIA
    # ============================================================

    resistance_distance = (resistance - price) / price

    if resistance_distance <= 0.005:
        # Muito próximo da resistência.
        entry -= 2
        entry_factors.append("resistencia_muito_proxima")

    elif resistance_distance <= 0.01:
        entry -= 1
        entry_factors.append("resistencia_proxima")

    else:
        # Existe espaço razoável até a resistência.
        entry += 1
        entry_factors.append("espaco_ate_resistencia")


    # ============================================================
    # PROXIMIDADE DO SUPORTE
    # ============================================================

    support_distance = (price - support) / price

    if support_distance <= 0.005:
        # Para uma compra, estar próximo do suporte
        # pode melhorar a relação risco/retorno.
        entry += 2
        entry_factors.append("suporte_proximo")

    elif support_distance <= 0.01:
        entry += 1
        entry_factors.append("suporte_proximo")

    else:
        entry_factors.append("espaco_ate_suporte")


    # ============================================================
    # SCORE DE RISCO
    #
    # Positivo = risco favorável
    # Negativo = risco desfavorável
    # ============================================================

    # Distância entre suporte e resistência
    range_distance = (resistance - support) / price

    if range_distance >= 0.03:
        risk += 2
        risk_factors.append("range_amplo")

    elif range_distance >= 0.015:
        risk += 1
        risk_factors.append("range_adequado")

    else:
        risk -= 1
        risk_factors.append("range_curto")


    # ATR em relação ao preço
    atr_percent = atr / price

    if atr_percent < 0.005:
        risk += 1
        risk_factors.append("volatilidade_controlada")

    elif atr_percent > 0.02:
        risk -= 1
        risk_factors.append("volatilidade_alta")


    # ============================================================
    # RISCO/RETORNO TEÓRICO
    # ============================================================

    # Compra:
    # risco = preço - suporte
    # retorno = resistência - preço

    risk_buy = price - support
    reward_buy = resistance - price

    if risk_buy > 0 and reward_buy > 0:

        rr_buy = reward_buy / risk_buy

        if rr_buy >= 2.0:
            risk += 2
            risk_factors.append("risco_retorno_compra_favoravel")

        elif rr_buy >= 1.5:
            risk += 1
            risk_factors.append("risco_retorno_compra_aceitavel")

        else:
            risk -= 2
            risk_factors.append("risco_retorno_compra_desfavoravel")

    else:
        rr_buy = None


    # Venda:
    # risco = resistência - preço
    # retorno = preço - suporte

    risk_sell = resistance - price
    reward_sell = price - support

    if risk_sell > 0 and reward_sell > 0:

        rr_sell = reward_sell / risk_sell

        if rr_sell >= 2.0:
            risk += 2
            risk_factors.append("risco_retorno_venda_favoravel")

        elif rr_sell >= 1.5:
            risk += 1
            risk_factors.append("risco_retorno_venda_aceitavel")

        else:
            risk -= 2
            risk_factors.append("risco_retorno_venda_desfavoravel")

    else:
        rr_sell = None


    return {
        "direcao": {
            "valor": direction,
            "fatores": direction_factors
        },

        "entrada": {
            "valor": entry,
            "fatores": entry_factors
        },

        "risco": {
            "valor": risk,
            "fatores": risk_factors
        },

        "distancias": {
            "vwap_percent": vwap_distance,
            "suporte_percent": support_distance,
            "resistencia_percent": resistance_distance,
            "atr_percent": atr_percent
        },

        "risco_retorno": {
            "compra": rr_buy,
            "venda": rr_sell
        }
    }

def calculate_exit_score(market, position):
    score = 0
    factors = []

    quantity = position["quantity"]
    average_price = position["average_price"]

    # Sem posição aberta
    if quantity <= 0:
        return {
            "valor": 0,
            "fatores": []
        }

    price = market["preco"]
    resistance = market["resistencia"]

    # ============================================================
    # LUCRO ATUAL
    # ============================================================

    pnl = (price - average_price) * quantity
    pnl_percent = (price - average_price) / average_price

    if pnl_percent >= 0.02:
        score += 2
        factors.append("lucro_significativo")

    elif pnl_percent >= 0.01:
        score += 1
        factors.append("lucro_moderado")

    # ============================================================
    # RESISTÊNCIA
    # ============================================================

    resistance_distance = (
        resistance - price
    ) / price

    if resistance_distance <= 0.005:
        score += 2
        factors.append("resistencia_muito_proxima")

    elif resistance_distance <= 0.01:
        score += 1
        factors.append("resistencia_proxima")

    # ============================================================
    # PERDA DE MOMENTUM
    # ============================================================

    if (
        market["var5m%"] < 0
        and market["var15m%"] < 0
    ):
        score += 1
        factors.append("momentum_perdendo_forca")

    # ============================================================
    # RESULTADO
    # ============================================================

    return {
        "valor": score,
        "fatores": factors,
        "pnl": round(pnl, 2),
        "pnl_percent": round(pnl_percent * 100, 4),
        "resistencia_distance_percent": round(
            resistance_distance * 100,
            4
        )
    }

# ============================================================
# PAYLOAD
# ============================================================

def build_payload(
    ticker,
    df,
    cash,
    quantity,
    average_price,
    realized_pnl,
    initial_cash
):

    price = float(df["Close"].iloc[-1])

    # --------------------------------------------------------
    # Indicadores
    # --------------------------------------------------------

    vwap = calculate_vwap(df)

    vwap_current = float(vwap.iloc[-1])

    rsi = calculate_rsi(df["Close"])

    atr = calculate_atr(df)

    ema9 = (
        df["Close"]
        .ewm(span=9, adjust=False)
        .mean()
        .iloc[-1]
    )

    ema21 = (
        df["Close"]
        .ewm(span=21, adjust=False)
        .mean()
        .iloc[-1]
    )

    ema50 = (
        df["Close"]
        .ewm(span=50, adjust=False)
        .mean()
        .iloc[-1]
    )

    volume = float(df["Volume"].iloc[-1])

    volume_average = (
        df["Volume"]
        .rolling(20)
        .mean()
        .iloc[-1]
    )

    volume_relative = (
        volume / volume_average
        if volume_average > 0
        else 0
    )

    # --------------------------------------------------------
    # Dados do pregão
    # --------------------------------------------------------

    opening = float(df["Open"].iloc[0])
    high = float(df["High"].max())
    low = float(df["Low"].min())

    var5m = percentage_change(df, 1)
    var15m = percentage_change(df, 3)
    var1h = percentage_change(df, 12)

    var_day = (price / opening - 1) * 100

    # --------------------------------------------------------
    # Portfolio
    # --------------------------------------------------------

    market_value = quantity * price

    unrealized_pnl = (
        (price - average_price) * quantity
        if quantity > 0
        else 0.0
    )

    equity = cash + market_value

    total_pnl = realized_pnl + unrealized_pnl

    daily_pnl_percent = (
        total_pnl / initial_cash * 100
        if initial_cash > 0
        else 0
    )

    timestamp = df.index[-1]

    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize(BRAZIL_TZ)
    else:
        timestamp = timestamp.tz_convert(BRAZIL_TZ)

    # --------------------------------------------------------
    # Payload
    # --------------------------------------------------------

    market = {
            "preco": round(price, 4),
            "abertura": round(opening, 4),
            "maxima_dia": round(high, 4),
            "minima_dia": round(low, 4),

            "vwap": round(vwap_current, 4),

            "var5m%": round(var5m, 4),
            "var15m%": round(var15m, 4),
            "var1h%": round(var1h, 4),
            "var_dia%": round(var_day, 4),

            "rsi": round(rsi, 2),

            "volume": int(volume),
            "volume_medio": int(volume_average),
            "volume_relativo": round(volume_relative, 2),

            "ema9": round(float(ema9), 4),
            "ema21": round(float(ema21), 4),
            "ema50": round(float(ema50), 4),

            "atr": round(atr, 4),

            "suporte": round(vwap_current, 4),
            "resistencia": round(high, 4)
        }   
    
    scores = calculate_scores(market)

    position = {
                "quantity": quantity,
                "average_price": round(average_price, 4),
                "market_value": round(market_value, 2)
            }

    scores["saida"] = calculate_exit_score(market, position)

    portfolio = {
            "initial_cash": round(initial_cash, 2),
            "cash": round(cash, 2),
            "equity": round(equity, 2),

            "realized_pnl": round(realized_pnl, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "total_pnl": round(total_pnl, 2),

            "daily_pnl": round(total_pnl, 2),
            "daily_pnl_percent": round(daily_pnl_percent, 2),

            "position": position
        }

    payload = {
        "ticker": ticker,
        "timestamp": timestamp.isoformat(),

        "market": market,

        "portfolio": portfolio,
        "scores": scores
    }

    return payload


# ============================================================
# CONSULTA AO TEV
# ============================================================

def ask_tev(payload):

    # IMPORTANTE:
    # O JSON é enviado como texto plano no body.
    body = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":")
    )

    response = requests.post(
        TEV_URL,
        data=body,
        headers={
            "Content-Type": "text/plain; charset=utf-8"
        },
        timeout=30
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# EXECUÇÃO SIMULADA
# ============================================================

def execute_buy(
    price,
    cash,
    quantity,
    average_price
):

    if cash <= 0:
        return cash, quantity, average_price, 0

    value = (
        cash
        if TRADE_VALUE is None
        else min(TRADE_VALUE, cash)
    )

    # Considera custo da compra
    effective_value = value * (1 - TRANSACTION_COST)

    bought_quantity = int(effective_value // price)

    if bought_quantity <= 0:
        return cash, quantity, average_price, 0

    cost = bought_quantity * price

    fee = cost * TRANSACTION_COST

    total_cost = cost + fee

    if total_cost > cash:
        return cash, quantity, average_price, 0

    new_quantity = quantity + bought_quantity

    if new_quantity > 0:
        new_average = (
            quantity * average_price
            + bought_quantity * price
        ) / new_quantity
    else:
        new_average = 0

    new_cash = cash - total_cost

    return (
        new_cash,
        new_quantity,
        new_average,
        bought_quantity
    )


def execute_sell(
    price,
    cash,
    quantity,
    average_price
):

    if quantity <= 0:
        return cash, quantity, average_price, 0, 0

    revenue = quantity * price

    fee = revenue * TRANSACTION_COST

    net_revenue = revenue - fee

    pnl = (
        (price - average_price) * quantity
        - fee
    )

    new_cash = cash + net_revenue

    return (
        new_cash,
        0,
        0,
        quantity,
        pnl
    )

def should_trade(scores, decision, position):
    direction = scores["direcao"]["valor"]
    entry = scores["entrada"]["valor"]
    risk = scores["risco"]["valor"]
    exit_score = scores["saida"]["valor"]

    decision = decision.upper()

    # Sem posição: procurar entrada
    if position["quantity"] == 0:

        if decision == "COMPRAR":
            if direction >= 3 and entry >= 0 and risk >= 0:
                return True, "entrada_compradora_aprovada"

        return False, "sem_entrada"

    # Com posição: procurar saída
    if position["quantity"] > 0:

        if decision == "VENDER":

            if exit_score >= 2:
                return True, "realizacao_ou_saida_aprovada"

            if direction <= -3:
                return True, "reversao_aprovada"

        return False, "manter_posicao"

    return False, "estado_invalido"

# ============================================================
# SIMULAÇÃO
# ============================================================

def simulate():

    print(f"Baixando dados de {TICKER}...")

    yahoo_ticker = (
        TICKER
        if TICKER.endswith(".SA")
        else f"{TICKER}.SA"
    )

    # Precisamos de alguns dias anteriores para calcular
    # corretamente EMA50, RSI etc.
    data = yf.download(
        yahoo_ticker,
        period="5d",
        interval="5m",
        auto_adjust=False,
        progress=False
    )

    if data.empty:
        raise RuntimeError("Nenhum dado encontrado.")

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = data.dropna(
        subset=[
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]
    )

    # --------------------------------------------------------
    # Seleciona somente o pregão de hoje
    # --------------------------------------------------------

    now = datetime.now(BRAZIL_TZ)

    if data.index.tz is None:
        data.index = data.index.tz_localize(BRAZIL_TZ)
    else:
        data.index = data.index.tz_convert(BRAZIL_TZ)

    today = data[
        data.index.date == now.date()
    ]

    if today.empty:
        raise RuntimeError(
            "Não existem candles para o pregão de hoje."
        )

    # --------------------------------------------------------
    # Estado inicial
    # --------------------------------------------------------

    cash = INITIAL_CASH

    quantity = 0

    average_price = 0.0

    realized_pnl = 0.0

    operations = []

    print()
    print("=" * 70)
    print(f"SIMULAÇÃO {TICKER}")
    print("=" * 70)

    # --------------------------------------------------------
    # Cada candle = uma nova decisão
    # --------------------------------------------------------

    for i in range(len(today)):

        current_timestamp = today.index[i]

        # Dados disponíveis até este candle.
        # IMPORTANTE:
        # o modelo não recebe candles futuros.
        historical = data[
            data.index <= current_timestamp
        ]

        # Precisamos de dados suficientes para os indicadores.
        if len(historical) < 50:
            continue

        payload = build_payload(
            ticker=TICKER,
            df=historical,
            cash=cash,
            quantity=quantity,
            average_price=average_price,
            realized_pnl=realized_pnl,
            initial_cash=INITIAL_CASH
        )

        # ----------------------------------------------------
        # Consulta ao TEV
        # ----------------------------------------------------

        try:

            result = ask_tev(payload)

        except Exception as e:

            print(
                f"[ERRO] "
                f"{current_timestamp} -> {e}"
            )

            continue

        # ----------------------------------------------------
        # Resposta do TEV
        #
        # Aceita tanto:
        # "decisao"
        # quanto:
        # "decisão"
        # ----------------------------------------------------

        decision = (
            result.get("tevData", {}).get("decisao", "SEGURAR")
        ).upper()

        confidence = float(
            result.get("tevData", {}).get("confianca", 0)
        )

        price = float(
            historical["Close"].iloc[-1]
        )

        scores = payload.get("scores", {})

        position = payload.get("portfolio", {}).get("position", {})

        approved, reason = should_trade(
            scores,
            decision,
            position
        )

        # ----------------------------------------------------
        # Somente executa se confiança > 0.80
        # ----------------------------------------------------

        executed = False

        if confidence >= MIN_CONFIDENCE and approved:

            # =================================================
            # COMPRA
            # =================================================

            if decision == "COMPRAR":

                old_quantity = quantity

                (
                    cash,
                    quantity,
                    average_price,
                    bought
                ) = execute_buy(
                    price,
                    cash,
                    quantity,
                    average_price
                )

                if bought > 0:

                    executed = True

                    operations.append({
                        "timestamp": current_timestamp.isoformat(),
                        "operation": "COMPRA",
                        "price": price,
                        "quantity": bought,
                        "confidence": confidence,
                        "cash": cash
                    })

            # =================================================
            # VENDA
            # =================================================

            elif decision == "VENDER":

                (
                    cash,
                    quantity,
                    average_price,
                    sold,
                    pnl
                ) = execute_sell(
                    price,
                    cash,
                    quantity,
                    average_price
                )

                if sold > 0:

                    realized_pnl += pnl

                    executed = True

                    operations.append({
                        "timestamp": current_timestamp.isoformat(),
                        "operation": "VENDA",
                        "price": price,
                        "quantity": sold,
                        "pnl": pnl,
                        "confidence": confidence,
                        "cash": cash
                    })

            # SEGURAR = nenhuma operação

        # ----------------------------------------------------
        # Log da iteração
        # ----------------------------------------------------

        print(
            f"{current_timestamp.strftime('%H:%M')} | "
            f"{decision:8s} | "
            f"{price:>8.2f} | "
            f"conf={confidence:.2f} | "
            f"direcao={scores['direcao']['valor']:+d} | "
            f"entrada={scores['entrada']['valor']:+d} | "
            f"risco={scores['risco']['valor']:+d} | "
            f"{reason}"
        )

    # ========================================================
    # FECHAMENTO DA SIMULAÇÃO
    # ========================================================

    final_price = float(
        today["Close"].iloc[-1]
    )

    # Se ainda existir posição, fazemos mark-to-market.
    unrealized_pnl = (
        (final_price - average_price) * quantity
        if quantity > 0
        else 0
    )

    final_equity = (
        cash +
        quantity * final_price
    )

    total_pnl = (
        final_equity -
        INITIAL_CASH
    )

    return_percent = (
        total_pnl /
        INITIAL_CASH *
        100
    )

    # ========================================================
    # RESULTADO
    # ========================================================

    print()
    print("=" * 70)
    print("RESULTADO")
    print("=" * 70)

    print(f"Capital inicial : R$ {INITIAL_CASH:,.2f}")
    print(f"Capital final   : R$ {final_equity:,.2f}")
    print(f"Lucro/prejuízo  : R$ {total_pnl:,.2f}")
    print(f"Retorno         : {return_percent:.2f}%")
    print(f"Realizado       : R$ {realized_pnl:,.2f}")
    print(f"Não realizado   : R$ {unrealized_pnl:,.2f}")
    print(f"Operações       : {len(operations)}")

    if quantity > 0:
        print()
        print(
            f"Posição aberta  : {quantity} ações"
        )
        print(
            f"Preço médio     : R$ {average_price:.2f}"
        )
        print(
            f"Preço final     : R$ {final_price:.2f}"
        )

    print()
    print("=" * 70)

    # --------------------------------------------------------
    # Salva histórico
    # --------------------------------------------------------

    result = {
        "ticker": TICKER,
        "initial_cash": INITIAL_CASH,
        "final_equity": round(final_equity, 2),
        "total_pnl": round(total_pnl, 2),
        "return_percent": round(return_percent, 2),
        "realized_pnl": round(realized_pnl, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "operations": operations
    }

    with open(
        "simulation_result.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        "\nResultado salvo em simulation_result.json"
    )


if __name__ == "__main__":
    simulate()