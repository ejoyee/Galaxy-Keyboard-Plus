package com.auth.domain;

import jakarta.persistence.*;
import lombok.*;

@Entity @Table(name = "auth_token")
@Getter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class AuthTokenEntity {

    @Id @Column(name = "user_id")
    private Long userId;

    @MapsId @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id")
    private UserInfo user;

    @Column(name="refresh_token", columnDefinition = "TEXT", nullable = false)
    private String refreshToken;

    @Builder
    private AuthTokenEntity(UserInfo user, String refreshToken) {
        this.user = user;
        this.userId = user.getId();
        this.refreshToken = refreshToken;
    }

    public void updateRefreshToken(String token) { this.refreshToken = token; }
}
