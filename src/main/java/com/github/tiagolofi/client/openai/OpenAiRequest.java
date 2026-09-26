package com.github.tiagolofi.client.openai;

public record OpenAiRequest(
    // OpenAiPrompt prompt,
    String model,
    String input,
    OpenAiReasoning reasoning
) {}
