package com.gateway.config;

import com.gateway.filter.RagRateLimitExceptionHandler;
import org.springframework.boot.autoconfigure.AutoConfigureBefore;
import org.springframework.boot.autoconfigure.web.reactive.error.ErrorWebFluxAutoConfiguration;
import org.springframework.boot.web.reactive.error.ErrorWebExceptionHandler;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.annotation.Order;

/**
 * Exception Handler 설정
 * Rate Limit 예외를 커스텀 핸들러로 처리
 */
@Configuration
@AutoConfigureBefore(ErrorWebFluxAutoConfiguration.class)
public class WebExceptionHandlerConfig {

    private final RagRateLimitExceptionHandler ragRateLimitExceptionHandler;

    public WebExceptionHandlerConfig(RagRateLimitExceptionHandler ragRateLimitExceptionHandler) {
        this.ragRateLimitExceptionHandler = ragRateLimitExceptionHandler;
    }

    @Bean
    @Order(-1)
    public ErrorWebExceptionHandler errorWebExceptionHandler() {
        return ragRateLimitExceptionHandler;
    }
}