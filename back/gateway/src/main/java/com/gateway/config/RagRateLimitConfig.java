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
        // burstCapacity가 replenishRate보다 크거나 같아야 함
        // 초당 단위로 계산: 분당 40개 = 초당 0.67개
        return new RedisRateLimiter(1, 10);  // 초당 1개, 버스트 10개
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
            var remoteAddress = exchange.getRequest().getRemoteAddress();
            if (remoteAddress != null) {
                String ip = remoteAddress.getAddress().getHostAddress();
                return Mono.just("rag-ip:" + ip);
            }
            
            return Mono.just("rag-anonymous");
        };
    }
}