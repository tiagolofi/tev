package com.github.tiagolofi.tev;

import org.jboss.resteasy.reactive.RestQuery;

import com.github.tiagolofi.tev.core.TevFunction;
import com.github.tiagolofi.tev.core.TevMetrics;
import com.github.tiagolofi.tev.core.TevResponse;
import com.github.tiagolofi.tev.functions.trading.TevTrading;

import jakarta.enterprise.context.RequestScoped;
import jakarta.inject.Inject;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;

@RequestScoped 
@Path("/tev")
public class TevResource {
    
    @Inject 
    TevFunction<TevTrading> trading;

    @POST 
    @Path("/inference")
    @Consumes(MediaType.TEXT_PLAIN)
    @Produces(MediaType.APPLICATION_JSON)
    @TevMetrics 
    public TevResponse<TevTrading> inference(@RestQuery String type, String json) {
        switch (type) {
            case "trading":
                return trading.get(json);
            default:
                return null;
        }
    }

}
