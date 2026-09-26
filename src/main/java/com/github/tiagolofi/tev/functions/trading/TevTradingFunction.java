package com.github.tiagolofi.tev.functions.trading;

import org.eclipse.microprofile.rest.client.inject.RestClient;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.tiagolofi.client.openai.OpenAi;
import com.github.tiagolofi.client.openai.OpenAiConfig;
import com.github.tiagolofi.client.openai.OpenAiReasoning;
import com.github.tiagolofi.client.openai.OpenAiRequest;
import com.github.tiagolofi.tev.core.TevFunction;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

@ApplicationScoped 
public class TevTradingFunction implements TevFunction<TevTrading> {
    
    @Inject 
    OpenAiConfig config;

    @Inject 
    @RestClient 
    OpenAi openAiClient;

    @Inject 
    ObjectMapper objectMapper;

    @Override 
    public TevTrading get(String input) {
        var request = new OpenAiRequest(config.model(), input, new OpenAiReasoning());

        return openAiClient.v1Responses("Bearer " + config.apiKey(), request)
            .getFirstContent(TevTrading.class);
    }
}

