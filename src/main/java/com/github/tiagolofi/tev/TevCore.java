package com.github.tiagolofi.tev;

public interface TevCore<T> {
    public TevResponse<T> get(String texto);

    public String promptId();

    public String promptVersion();
}
