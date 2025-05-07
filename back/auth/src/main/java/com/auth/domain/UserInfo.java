package com.auth.domain;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "user_info")
@Getter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class UserInfo {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "user_id", updatable = false, nullable = false) // id는 DB에서 생성되므로 앱에서 업데이트하지 않음
    private Long id;

    @Column(name = "kakao_email", nullable = false, unique = true)
    private String kakaoEmail;

}
