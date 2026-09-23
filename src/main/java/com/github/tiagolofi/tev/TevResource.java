package com.github.tiagolofi.tev;

import org.jboss.resteasy.reactive.RestQuery;

import com.github.tiagolofi.tev.core.TevCore;
import com.github.tiagolofi.tev.core.TevMetrics;
import com.github.tiagolofi.tev.core.TevResponse;
import com.github.tiagolofi.tev.functions.finance.TevFinance;

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
    TevCore<TevFinance> tevFinance;

    @POST 
    @Path("/inference")
    @Consumes(MediaType.TEXT_PLAIN)
    @Produces(MediaType.APPLICATION_JSON)
    @TevMetrics 
    public TevResponse<TevFinance> inference(@RestQuery String type, String texto) {
        switch (type) {
            case "finance":
                return tevFinance.get(texto);
            default:
                return null;
        }
    }

}
