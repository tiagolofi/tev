package com.github.tiagolofi.client.openai;

public record OpenAiReasoning(
    String mode,
    String effort
) {
    public OpenAiReasoning() {
        this("standard", "low");
    }
}
