package com.github.tiagolofi.client.openai;

import java.util.List;

public record OpenAiResponse(
    List<OpenAiOutput> output
) {}
