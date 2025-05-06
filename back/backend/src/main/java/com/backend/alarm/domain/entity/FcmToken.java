package com.backend.alarm.domain.entity;

import com.backend.user.domain.entity.User;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.util.UUID;

@Entity
@Table(name = "fcm_token")
@Getter
@NoArgsConstructor
@AllArgsConstructor
public class FcmToken {
    @Id
    @Column(name = "user_id", nullable = false)
    private UUID userId;

    @OneToOne
    @MapsId
    @JoinColumn(name = "user_id")
    private User user;

    @Column(name = "token", nullable = false, unique = true, length = 255)
    private String token;
}
