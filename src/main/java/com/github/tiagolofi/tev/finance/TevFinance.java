package com.github.tiagolofi.tev.finance;

import java.util.List;
import java.util.Map;

public record TevFinance(
    String ticker,
    String decisao,
    List<String> fatores,
    Map<String, Double> indicadores
) {}
