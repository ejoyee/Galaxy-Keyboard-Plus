package com.auth.oauth;

import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.util.Map;

@Component
@RequiredArgsConstructor
public class KakaoAuthClient {

    @Value("${spring.security.oauth2.client.registration.kakao.client-id}")
    private String id;
    //    @Value("${spring.security.oauth2.client.registration.kakao.client-secret}")private String secret;
    @Value("${spring.security.oauth2.client.registration.kakao.redirect-uri}")
    private String redirect;

    private final WebClient web = WebClient.builder().build();

    public String fetchAccessToken(String code) {
        System.out.println("카카오 인증 요청 - client_id: " + id);
        System.out.println("카카오 인증 요청 - redirect_uri: " + redirect);
        System.out.println("카카오 인증 요청 - code: " + code);

        return web.post().uri("https://kauth.kakao.com/oauth/token")
                .contentType(MediaType.APPLICATION_FORM_URLENCODED)
                .bodyValue("grant_type=authorization_code"
                        + "&client_id=" + id
                        + "&redirect_uri=" + redirect
                        + "&code=" + code)
//                     + "&client_secret=" + secret)
                .retrieve()
                .onStatus(status -> status.isError(), response -> {
                    // 오류 응답을 String 형태로 로깅하여 에러 메시지를 확인
                    return response.bodyToMono(String.class)
                            .doOnTerminate(() -> {
                                // 비동기 작업이 끝난 후 오류 메시지 출력
                                System.out.println("카카오 API 응답 오류 상태: " + response.statusCode());
                            })
                            .flatMap(errorResponse -> {
                                // `Mono.error`를 사용하여 에러를 발생시키고, 정확한 예외 메시지를 던짐
                                return Mono.error(new RuntimeException("카카오 API 요청 실패: " + errorResponse));
                            });
                })
                .bodyToMono(Map.class)
                .map(m -> (String) m.get("access_token"))
                .block();
    }

    public String fetchEmail(String at) {
        Map<?, ?> body = web.get().uri("https://kapi.kakao.com/v2/user/me")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + at)
                .retrieve()
                .bodyToMono(Map.class)
                .block();
        return (String) ((Map<?, ?>) body.get("kakao_account")).get("email");
    }
}
