package com.auth.service;

import com.auth.config.JwtTokenProvider;
import com.auth.domain.*;
import com.auth.oauth.KakaoAuthClient;
import com.auth.repository.*;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.Map;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final KakaoAuthClient kakao;
    private final UserInfoRepository userRepo;
    private final AuthTokenRepository tokenRepo;
    private final JwtTokenProvider jwt;

    public Map<String,String> login(String code, String redirectUri) {

        String kakaoAT = kakao.fetchAccessToken(code);
        String email   = kakao.fetchEmail(kakaoAT);

        UserInfo user = userRepo.findByKakaoEmail(email)
                .orElseGet(() -> userRepo.save(
                        UserInfo.builder()
                                .id(UUID.randomUUID())
                                .kakaoEmail(email)
                                .build()));

        String at = jwt.access(user.getId());
        String rt = jwt.refresh(user.getId());

        tokenRepo.findById(user.getId())
                 .ifPresentOrElse(
                     t -> t.updateRefreshToken(rt),
                     () -> tokenRepo.save(
                             AuthTokenEntity.builder()
                                            .user(user)
                                            .refreshToken(rt)
                                            .build()));

        return Map.of("accessToken", at, "refreshToken", rt);
    }

    public Map<String,String> reissue(String oldRt) {
        var uid = jwt.parse(oldRt);
        AuthTokenEntity token = tokenRepo.findById(uid)
                .orElseThrow(() -> new RuntimeException("Invalid RT"));
        if (!token.getRefreshToken().equals(oldRt))
            throw new RuntimeException("RT mismatch");

        String newAt = jwt.access(uid);
        String newRt = jwt.refresh(uid);
        token.updateRefreshToken(newRt);
        return Map.of("accessToken", newAt, "refreshToken", newRt);
    }

    public void logout(String rt) { tokenRepo.deleteById(jwt.parse(rt)); }
}
