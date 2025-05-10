package com.gateway.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.gateway.filter.ratelimit.KeyResolver;
import org.springframework.cloud.gateway.filter.ratelimit.RedisRateLimiter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.ReactiveRedisConnectionFactory;
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;
import reactor.core.publisher.Mono;

@Configuration
public class RagRateLimitConfig {

    // application.yml 의 spring.redis.host
    @Value("${spring.redis.host}")
    private String redisHost;

    // application.yml 의 spring.redis.port
    @Value("${spring.redis.port}")
    private int redisPort;

    /**
     * 1) Reactive API용 LettuceConnectionFactory 빈 등록
     */
    @Bean
    public ReactiveRedisConnectionFactory reactiveRedisConnectionFactory() {
        LettuceConnectionFactory factory = new LettuceConnectionFactory(redisHost, redisPort);
        factory.afterPropertiesSet();  // 설정 적용
        return factory;
    }

    /**
     * 2) Gateway RequestRateLimiter 빈
     *    — ReactiveRedisConnectionFactory를 주입받도록 변경
     */
    @Bean("ragServerRateLimiter")
    public RedisRateLimiter ragServerRateLimiter(ReactiveRedisConnectionFactory factory) {
        // 분당 1 토큰, 버스트 10 토큰
        return new RedisRateLimiter(1, 10, factory);
    }

    /**
     * 3) 사용자별 KeyResolver (JWT or IP)
     */
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
