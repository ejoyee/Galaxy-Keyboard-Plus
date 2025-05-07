package com.auth.controller;

import com.auth.service.AuthService;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.view.RedirectView;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Map;

@RestController
@RequestMapping("/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    // 카카오 리다이렉트 URI 설정 (카카오에서 인증 후 리다이렉트할 URI)
//    private final String redirectUri = "http://localhost:8082/login/oauth2/code/kakao"; // 카카오 개발자 콘솔에 등록된 리다이렉트 URI와 동일해야 함.

    // KakaoAuthClient가 토큰 교환 시 사용할 redirect_uri (application.yml에서 로드)
    // 이 URI는 카카오 개발자 콘솔에 백엔드 서버용으로 등록된 것이어야 합니다.
    // KakaoAuthClient 내부에서 직접 @Value로 주입받아 사용하므로, 컨트롤러에서 명시적으로 알 필요는 없을 수 있습니다.
    // 다만, AuthService.login()의 두 번째 파라미터로 무엇을 넘길지 명확히 하기 위함입니다.
//    @Value("${spring.security.oauth2.client.registration.kakao.redirect-uri}")
//    private String kakaoTokenExchangeRedirectUri;


//    /** 카카오 리다이렉트 URI */
//    @GetMapping("/kakao/callback")
//    public RedirectView kakaoCallback(@RequestParam String code) {
//        System.out.println("카카오 인증 코드: " + code);
//        try {
////            System.out.println("카카오 로그인 요청에 사용된 리다이렉트 URI: " + kakaoTokenExchangeRedirectUri);
//            Map<String, String> tokens = authService.login(code);
//            String at = tokens.get("accessToken");
//            String rt = tokens.get("refreshTok`en");
//
//            System.out.println("발급된 액세스 토큰: " + at);
//
//
//            String target = "http://localhost:5173/login/success?at=" +
//                    at +
//                    "&rt=" + rt;
//            return new RedirectView(target);
//        } catch (Exception e) {
//            // 예외가 뭔지 redirect URI에 실어서 프론트로 보내 보기
//            String err = URLEncoder.encode(e.getMessage(), StandardCharsets.UTF_8);
//            return new RedirectView("http://localhost:5173/login/fail?error=" + err);
//        }
//    }
//
//    /**
//     * React Native 앱과 같은 모바일 클라이언트용 카카오 로그인 처리 엔드포인트
//     * 앱에서 받은 authorization_code를 사용해 로그인 처리 후 JWT 토큰 반환
//     * @param payload 요청 본문, {"code": "카카오 인가 코드"} 형태
//     * @return JWT (accessToken, refreshToken) 포함 응답 또는 에러 메시지
//     */
//    @PostMapping("/kakao/mobile-login")
//    public ResponseEntity<Map<String, String>> kakaoMobileLogin(@RequestBody Map<String, String> payload) {
//        String code = payload.get("code");
//        System.out.println("카카오 인증 코드 (모바일): " + code);
//
//        if (code == null || code.trim().isEmpty()) {
//            return ResponseEntity.badRequest().body(Map.of("error", "Authorization code is missing or empty."));
//        }
//
//        try {
//            // KakaoAuthClient는 토큰 교환 시 application.yml에 설정된 redirect_uri를 사용합니다.
//            // 이 redirect_uri는 카카오 개발자 콘솔에 백엔드 서버용으로 등록된 URI여야 합니다.
//            // (예: https://your-backend.com/login/oauth2/code/kakao)
//            // 모바일 앱의 커스텀 스킴(kakao{APP_KEY}://oauth)과는 다릅니다.
//            // AuthService.login의 두번째 redirectUri 파라미터는 KakaoAuthClient가 실제로 사용하는
//            // 서버측 redirect_uri 값을 전달하거나, KakaoAuthClient가 이를 직접 참조하도록 합니다.
//            // 현재 KakaoAuthClient는 @Value 주입으로 스스로 해결하므로, AuthService.login의 두번째 파라미터는
//            // KakaoAuthClient 내부 로직에 영향을 주지 않습니다. 명확성을 위해 해당 값을 전달합니다.
//            Map<String, String> tokens = authService.login(code);
//            System.out.println("발급된 액세스 토큰 (모바일): " + tokens.get("accessToken"));
//            return ResponseEntity.ok(tokens);
//        } catch (Exception e) {
//            e.printStackTrace(); // 서버 로그에 상세 오류 출력
//            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
//                    .body(Map.of("error", "Login failed: " + e.getMessage()));
//        }
//    }

    // AuthController.java 에 추가
    @PostMapping("/kakao/login-sdk") // 또는 "/kakao/token-login" 등
    public ResponseEntity<Map<String, String>> kakaoLoginWithSdkToken(@RequestBody Map<String, String> payload) {
        String kakaoAccessToken = payload.get("kakaoAccessToken");
        System.out.println("카카오 SDK Access Token (모바일): " + kakaoAccessToken);

        if (kakaoAccessToken == null || kakaoAccessToken.trim().isEmpty()) {
            return ResponseEntity.badRequest().body(Map.of("error", "Kakao Access Token is missing or empty."));
        }

        try {
            Map<String, String> appTokens = authService.loginWithKakaoAccessToken(kakaoAccessToken); // AuthService의 새 메소드 호출
            return ResponseEntity.ok(appTokens);
        } catch (Exception e) {
            e.printStackTrace(); // 서버 로그
            // 실제로는 예외 유형에 따라 다른 메시지나 상태 코드 반환
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED) // 예: 토큰이 유효하지 않거나 사용자 정보 조회 실패 시
                    .body(Map.of("error", "Login failed with Kakao Access Token: " + e.getMessage()));
        }
    }

    /**
     * AT 재발급
     */
    @PostMapping("/reissue")
    public ResponseEntity<Map<String, String>> reissue(@RequestBody Map<String, String> body) {
        String refreshToken = body.get("refreshToken");
        if (refreshToken == null || refreshToken.trim().isEmpty()) {
            return ResponseEntity.badRequest().body(Map.of("error", "Refresh token is missing or empty."));
        }
        try {
            return ResponseEntity.ok(authService.reissue(refreshToken));
        } catch (Exception e) {
            e.printStackTrace(); // 서버 로그
            // 실제로는 예외 유형에 따라 다른 상태 코드(예: 401 Unauthorized) 반환 고려
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                    .body(Map.of("error", "Token reissue failed: " + e.getMessage()));
        }
    }

}
