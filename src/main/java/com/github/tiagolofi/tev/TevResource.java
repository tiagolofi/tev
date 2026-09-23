package com.github.tiagolofi.tev;

import org.jboss.resteasy.reactive.RestQuery;

import com.github.tiagolofi.tev.finance.TevFinance;

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
    public TevResponse<TevFinance> inference(@RestQuery String type, String texto) {
        switch (type) {
            case "finance":
                return tevFinance.get(texto);
            default:
                return null;
        }
    }

}
