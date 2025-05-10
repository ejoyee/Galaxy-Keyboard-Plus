package com.gateway.filter;

import org.springframework.boot.autoconfigure.web.ErrorProperties;
import org.springframework.boot.autoconfigure.web.WebProperties;
import org.springframework.boot.autoconfigure.web.reactive.error.DefaultErrorWebExceptionHandler;
import org.springframework.boot.web.reactive.error.ErrorAttributes;
import org.springframework.context.ApplicationContext;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerCodecConfigurer;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.server.*;
import reactor.core.publisher.Mono;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Map;

@Component
public class RagRateLimitExceptionHandler extends DefaultErrorWebExceptionHandler {

    public RagRateLimitExceptionHandler(
            ErrorAttributes errorAttributes,
            WebProperties.Resources resources,
            ErrorProperties errorProperties,
            ApplicationContext applicationContext,
            ServerCodecConfigurer serverCodecConfigurer) {
        super(errorAttributes, resources, errorProperties, applicationContext);
        this.setMessageWriters(serverCodecConfigurer.getWriters());
    }

    @Override
    protected RouterFunction<ServerResponse> getRoutingFunction(ErrorAttributes errorAttributes) {
        return RouterFunctions.route(RequestPredicates.all(), this::renderErrorResponse);
    }

    @Override  // protected로 변경
    protected Mono<ServerResponse> renderErrorResponse(ServerRequest request) {
        Map<String, Object> error = getErrorAttributes(request, org.springframework.boot.web.error.ErrorAttributeOptions.defaults());
        
        // Rate Limit 초과 에러 처리
        if (error.get("error") != null && error.get("error").equals("Too Many Requests")) {
            String timestamp = LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME);
            
            return ServerResponse.status(HttpStatus.TOO_MANY_REQUESTS)
                .contentType(MediaType.APPLICATION_JSON)
                .body(BodyInserters.fromValue(Map.of(
                    "error", "RAG_RATE_LIMIT_EXCEEDED",
                    "message", "RAG 서비스 요청 횟수가 제한을 초과했습니다.",
                    "detail", "분당 40개 요청, 연속 10개까지 가능합니다. 잠시 후 다시 시도해주세요.",
                    "limit", "40/minute, burst: 10",
                    "status", 429,
                    "timestamp", timestamp,
                    "path", request.path()
                )));
        }
        
        // 기타 에러 처리
        int status = (Integer) error.getOrDefault("status", 500);
        return ServerResponse.status(status)
            .contentType(MediaType.APPLICATION_JSON)
            .body(BodyInserters.fromValue(error));
    }
}