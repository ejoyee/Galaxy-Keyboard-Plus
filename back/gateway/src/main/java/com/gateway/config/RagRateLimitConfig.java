package com.gateway.config;

import org.springframework.cloud.gateway.filter.ratelimit.KeyResolver;
import org.springframework.cloud.gateway.filter.ratelimit.RedisRateLimiter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import reactor.core.publisher.Mono;

/**
 * RAG 서비스 전용 Rate Limiter 설정
 * - 분당 40개 요청
 * - 버스트 10개
 */
@Configuration
public class RagRateLimitConfig {

    @Bean("ragServerRateLimiter")
    public RedisRateLimiter ragServerRateLimiter() {
        return new RedisRateLimiter(
            40.0/60,  // replenishRate: 분당 40개 = 초당 0.67개
            10,       // burstCapacity: 최대 10개의 연속 요청
            1         // requestedTokens: 요청당 1개 토큰
        );
    }

    @Bean("userKeyResolver")
    public KeyResolver userKeyResolver() {
        // 사용자별 rate limiting (JWT token 또는 IP 기반)
        return exchange -> {
            String authHeader = exchange.getRequest().getHeaders().getFirst("Authorization");
            
            if (authHeader != null && authHeader.startsWith("Bearer ")) {
                // JWT 토큰에서 사용자 식별자 추출
                // 실제 사용자별은아님 해시충돌가능성 존재
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