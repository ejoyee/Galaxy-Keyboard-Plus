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

    private String create(UUID uid, long ms) {
        Date now = new Date();
        return JWT.create().withSubject(uid.toString())
                  .withIssuedAt(now)
                  .withExpiresAt(new Date(now.getTime() + ms))
                  .sign(alg);
    }
    public String access(UUID id)  { return create(id, atMs); }
    public String refresh(UUID id) { return create(id, rtMs); }

    public UUID parse(String token) {
        try {
            DecodedJWT decoded = JWT.require(alg).build().verify(token);
            String subject = decoded.getSubject();
            if (subject == null) {
                throw new JWTVerificationException("Token does not contain a subject (userId)");
            }
            return UUID.fromString(subject);
        } catch (JWTVerificationException | IllegalArgumentException e) {
            // IllegalArgumentException은 UUID.fromString 실패 시 던져집니다.
            System.err.println("JWT parsing/verification failed: " + e.getMessage());
            throw new RuntimeException("Invalid Token or failed to parse User ID from token.", e);
        }
    }
}
