package com.github.tiagolofi.tev.functions.finance;

import java.util.Map;

import org.eclipse.microprofile.rest.client.inject.RestClient;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.tiagolofi.client.openai.OpenAi;
import com.github.tiagolofi.client.openai.OpenAiConfig;
import com.github.tiagolofi.client.openai.OpenAiPrompt;
import com.github.tiagolofi.client.openai.OpenAiRequest;
import com.github.tiagolofi.tev.core.TevCore;
import com.github.tiagolofi.tev.core.TevResponse;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

@ApplicationScoped 
public class TevFinanceService implements TevCore<TevFinance> {
    
    @Inject 
    OpenAiConfig config;

    @Inject 
    @RestClient 
    OpenAi openAiClient;

    @Inject 
    ObjectMapper objectMapper;

    @Override 
    public TevResponse<TevFinance> get(String texto) {
        var prompt = new OpenAiPrompt(
            promptId(),
            promptVersion(),
            Map.of("texto", texto)
        );

        var request = new OpenAiRequest(prompt);

        TevFinance tev = openAiClient.v1Responses("Bearer " + config.apiKey(), request).output()
            .stream()
            .filter(o -> o.isMessage())
            .findFirst()
            .map(o -> {
                try {
                    return objectMapper.readValue(o.getFirstContent().text(), TevFinance.class);
                } catch (JsonProcessingException e) {
                    return null;
                }
            })
            .orElse(null);

        return new TevResponse<>("finance", tev);
    }

    @Override
    public String promptId() {
        return "pmpt_6ab33dbafdec8194b4c49b34cb564b390477239e1a95e3f7";
    }

    @Override
    public String promptVersion() {
        return "3";
    }

}

