package com.github.tiagolofi.tev.core;

import java.lang.reflect.Parameter;

import org.jboss.logging.Logger;

import jakarta.annotation.Priority;
import jakarta.inject.Inject;
import jakarta.interceptor.AroundInvoke;
import jakarta.interceptor.Interceptor;
import jakarta.interceptor.InvocationContext;
import jakarta.ws.rs.Path;

@Interceptor 
@TevMetrics
@Priority(Interceptor.Priority.APPLICATION)
public class TevMetricsInterceptor {
    
    private static final String NAME_METHOD_RESOUCE = "inference";

    @Inject 
    Logger log;

    @AroundInvoke 
    public Object logMetrics(InvocationContext context) throws Exception {
        long startTime = System.currentTimeMillis();
        String methodName = context.getMethod().getName();
        try {
            return context.proceed();
        } catch (Exception e) {
            throw e;
        } finally {
            long endTime = System.currentTimeMillis();
            long duration = endTime - startTime;
            if (NAME_METHOD_RESOUCE.equals(methodName)) {
                Path path = context.getMethod().getAnnotation(Path.class);
                Parameter[] parameters = context.getMethod().getParameters();
                log.infof("endpoint `%s?%s=%s` executed in %s ms", path.value(), parameters[0].getName(), context.getParameters()[0], duration);
            } else {
                log.infof("client method `%s` executed in %s ms", methodName, duration);
            }
        }
    }

}
