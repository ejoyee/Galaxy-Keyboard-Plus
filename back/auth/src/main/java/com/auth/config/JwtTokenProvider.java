package com.auth.config;

import com.auth0.jwt.*;
import com.auth0.jwt.algorithms.Algorithm;
import com.auth0.jwt.exceptions.JWTVerificationException;
import com.auth0.jwt.interfaces.DecodedJWT;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.*;

@Component
public class JwtTokenProvider {

    private final Algorithm alg;
    private final long atMs;
    private final long rtMs;

    public JwtTokenProvider(@Value("${jwt.secret}") String secret,
                            @Value("${jwt.access-token-validity}") long at,
                            @Value("${jwt.refresh-token-validity}") long rt) {
        this.alg = Algorithm.HMAC256(Base64.getEncoder().encodeToString(secret.getBytes()));
        this.atMs = at;
        this.rtMs = rt;
    }

    private String create(Long uid, long ms) {
        Date now = new Date();
        return JWT.create().withSubject(uid.toString())
                  .withIssuedAt(now)
                  .withExpiresAt(new Date(now.getTime() + ms))
                  .sign(alg);
    }
    public String access(Long id)  { return create(id, atMs); }
    public String refresh(Long id) { return create(id, rtMs); }

    public Long parse(String token) {
        try {
            DecodedJWT decodedJWT = JWT.require(alg) // alg 변수는 클래스 내에 정의되어 있어야 합니다.
                    .build()
                    .verify(token);
            String subject = decodedJWT.getSubject();
            if (subject == null) {
                // Subject 클레임이 없는 경우 또는 다른 클레임에 ID를 저장한 경우에 대한 처리
                throw new JWTVerificationException("Token does not contain a subject (userId)");
            }
            return Long.parseLong(subject); // subject 문자열을 Long으로 변환
        } catch (JWTVerificationException e) {
            // 토큰 검증 실패 (예: 만료, 서명 불일치 등) 또는 subject 파싱 실패
            // 실제 운영 환경에서는 로깅을 하거나 좀 더 구체적인 예외를 던지는 것이 좋습니다.
            System.err.println("JWT parsing/verification failed: " + e.getMessage());
            throw new RuntimeException("Invalid Token or failed to parse User ID from token.", e);
        } catch (NumberFormatException e) {
            // subject 클레임이 Long으로 변환될 수 없는 형식인 경우
            System.err.println("Failed to parse subject to Long: " + e.getMessage());
            throw new RuntimeException("User ID in token is not a valid number.", e);
        }
    }
}
