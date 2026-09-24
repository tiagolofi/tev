package com.github.tiagolofi.tev.functions.trading;

import java.util.List;
import java.util.Map;

public record TevTrading(
    String ticker,
    String decisao,
    Double confianca,
    List<String> fatores,
    Map<String, Double> operacao
) {}
