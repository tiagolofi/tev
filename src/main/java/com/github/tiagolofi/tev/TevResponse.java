package com.github.tiagolofi.tev;

public record TevResponse<T>(
    String tevName,
    T tevData
) {}
