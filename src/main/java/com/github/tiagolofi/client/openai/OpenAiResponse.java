package com.github.tiagolofi.client.openai;

import java.util.List;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

public record OpenAiResponse(
    List<OpenAiOutput> output
) {
    public <T> T getFirstContent(Class<T> clazz) {
        return output()
            .stream()
            .filter(OpenAiOutput::isMessage)
            .findFirst()
            .map(o -> {
                try {
                    return new ObjectMapper().readValue(o.getFirstContent().text(), clazz);
                } catch (JsonProcessingException e) {
                    return null;
                }
            })
            .orElse(null);
    }
}
