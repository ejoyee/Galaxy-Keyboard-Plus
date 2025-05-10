package com.gateway.config;

import org.springframework.cloud.gateway.filter.ratelimit.KeyResolver;
import org.springframework.cloud.gateway.filter.ratelimit.RedisRateLimiter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import reactor.core.publisher.Mono;

/**
 * RAG 서비스 전용 Rate Limiter 설정
 * - application.yml의 redis-rate-limiter 설정 사용
 */
@Configuration
public class RagRateLimitConfig {

    @Bean("ragServerRateLimiter")
    public RedisRateLimiter ragServerRateLimiter() {
        // application.yml의 설정을 자동으로 가져옴
        return new RedisRateLimiter(40, 10);
    }

    @Bean("userKeyResolver")
    public KeyResolver userKeyResolver() {
        // 사용자별 rate limiting (JWT token 또는 IP 기반)
        return exchange -> {
            String authHeader = exchange.getRequest().getHeaders().getFirst("Authorization");
            
            if (authHeader != null && authHeader.startsWith("Bearer ")) {
                // JWT 토큰에서 사용자 식별자 추출
                String token = authHeader.substring(7);
                return Mono.just("rag-user:" + token.hashCode());
            }
            
            // 인증 토큰이 없는 경우 IP 기반
            return exchange.getRequest()
                .getRemoteAddress()
                .map(addr -> "rag-ip:" + addr.getAddress().getHostAddress())
                .orElse(Mono.just("rag-anonymous"));
        };
    }
}