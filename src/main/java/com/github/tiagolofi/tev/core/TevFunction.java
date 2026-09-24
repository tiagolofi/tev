package com.github.tiagolofi.tev.core;

public interface TevFunction<T> {
    public TevResponse<T> get(String texto);

    public String promptId();

    public String promptVersion();
}
