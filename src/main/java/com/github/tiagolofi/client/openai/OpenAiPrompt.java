package com.github.tiagolofi.client.openai;

import java.util.Map;

public record OpenAiPrompt(
    String id,
    String version,
    Map<String, String> variables
) {}
