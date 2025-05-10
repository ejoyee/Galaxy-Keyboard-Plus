package com.gateway.config;

import org.springframework.cloud.gateway.filter.ratelimit.KeyResolver;
import org.springframework.cloud.gateway.filter.ratelimit.RedisRateLimiter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import reactor.core.publisher.Mono;

@Configuration
public class RagRateLimitConfig {

    @Bean("ragServerRateLimiter")
    public RedisRateLimiter ragServerRateLimiter() {
        // 첫번째: 분당 토큰 1개, 두번째: 버스트 최대 10개, 세번째: 요청당 소모 토큰 수 1
        return new RedisRateLimiter(1, 10, 1);
    }

    @Bean("userKeyResolver")
    public KeyResolver userKeyResolver() {
        return exchange -> {
            String authHeader = exchange.getRequest().getHeaders().getFirst("Authorization");
            if (authHeader != null && authHeader.startsWith("Bearer ")) {
                String token = authHeader.substring(7);
                return Mono.just("rag-user:" + token.hashCode());
            }
            var remote = exchange.getRequest().getRemoteAddress();
            String key = (remote != null)
                ? "rag-ip:" + remote.getAddress().getHostAddress()
                : "rag-anonymous";
            return Mono.just(key);
        };
    }
}
