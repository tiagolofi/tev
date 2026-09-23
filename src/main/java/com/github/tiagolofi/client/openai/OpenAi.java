package com.github.tiagolofi.client.openai;

import org.eclipse.microprofile.rest.client.inject.RegisterRestClient;
import org.jboss.resteasy.reactive.RestHeader;

import com.github.tiagolofi.tev.core.TevMetrics;

import jakarta.enterprise.context.RequestScoped;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;

@RequestScoped
@RegisterRestClient(configKey = "openai")
public interface OpenAi {
    
    @POST
    @Consumes(MediaType.APPLICATION_JSON)
    @Produces(MediaType.APPLICATION_JSON)
    @Path("/v1/responses")
    @TevMetrics 
    public OpenAiResponse v1Responses(@RestHeader("Authorization") String authorization, OpenAiRequest request);
}
