package com.github.tiagolofi.client.openai;

import java.util.List;

public record OpenAiInput(
    String role,
    List<OpenAiContent> content
) {}
