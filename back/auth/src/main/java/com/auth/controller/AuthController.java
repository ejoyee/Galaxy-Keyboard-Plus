package com.auth.controller;

import com.auth.service.AuthService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.view.RedirectView;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Map;

@RestController
@RequestMapping("/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService auth;

    // 카카오 리다이렉트 URI 설정 (카카오에서 인증 후 리다이렉트할 URI)
    private final String redirectUri = "http://localhost:8082/login/oauth2/code/kakao"; // 카카오 개발자 콘솔에 등록된 리다이렉트 URI와 동일해야 함.


    /** 카카오 리다이렉트 URI */
    @GetMapping("/kakao/callback")
    public RedirectView kakaoCallback(@RequestParam String code) {
        System.out.println("카카오 인증 코드: " + code);
        try {
            System.out.println("카카오 로그인 요청에 사용된 리다이렉트 URI: " + redirectUri);
            Map<String, String> tokens = auth.login(code, redirectUri);
            String at = tokens.get("accessToken");
            String rt = tokens.get("refreshTok`en");

            System.out.println("발급된 액세스 토큰: " + at);


            String target = "http://localhost:5173/login/success?at=" +
                    at +
                    "&rt=" + rt;
            return new RedirectView(target);
        } catch (Exception e) {
            // 예외가 뭔지 redirect URI에 실어서 프론트로 보내 보기
            String err = URLEncoder.encode(e.getMessage(), StandardCharsets.UTF_8);
            return new RedirectView("http://localhost:5173/login/fail?error=" + err);
        }
    }

    /** AT 재발급 */
    @PostMapping("/reissue")
    public Map<String,String> reissue(@RequestBody Map<String,String> body) {
        return auth.reissue(body.get("refreshToken"));
    }

}
