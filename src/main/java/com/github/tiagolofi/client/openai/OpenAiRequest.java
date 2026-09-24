package com.github.tiagolofi.client.openai;

import java.util.List;

public record OpenAiRequest(
    OpenAiPrompt prompt,
    List<OpenAiInput> input
) {}
