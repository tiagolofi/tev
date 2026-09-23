package com.github.tiagolofi.tev.core;

public record TevResponse<T>(
    String tevName,
    T tevData
) {}
