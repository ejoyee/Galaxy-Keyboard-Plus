package com.auth.domain;

import jakarta.persistence.*;
import lombok.*;

@Entity @Table(name = "user_info")
@Getter @NoArgsConstructor(access = AccessLevel.PROTECTED)
public class UserInfo {

    @Id
    @GeneratedValue(generator = "UUID")
    @Column(name = "user_id")
    private java.util.UUID id;

    @Column(name = "kakao_email", nullable = false, unique = true)
    private String kakaoEmail;

    @Builder
    private UserInfo(java.util.UUID id, String kakaoEmail) {
        this.id = id;
        this.kakaoEmail = kakaoEmail;
    }
}
