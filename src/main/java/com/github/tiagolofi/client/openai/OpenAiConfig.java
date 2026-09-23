package com.github.tiagolofi.client.openai;

import io.smallrye.config.ConfigMapping;

@ConfigMapping(prefix = "openai")
public interface OpenAiConfig {
    String apiKey();
}
