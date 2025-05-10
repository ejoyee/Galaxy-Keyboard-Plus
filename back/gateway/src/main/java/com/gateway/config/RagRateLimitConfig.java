package com.gateway.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.gateway.filter.ratelimit.KeyResolver;
import org.springframework.cloud.gateway.filter.ratelimit.RedisRateLimiter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import reactor.core.publisher.Mono;

@Configuration
public class RagRateLimitConfig {

    @Bean("ragServerRateLimiter")
    public RedisRateLimiter ragServerRateLimiter(RedisConnectionFactory redisConnectionFactory) {
        // RedisConnectionFactory를 주입받아 사용
        return new RedisRateLimiter(1, 10, redisConnectionFactory);
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