package com.backend.plan.domain.entity;

import com.backend.image.domain.entity.Image;
import com.backend.user.domain.entity.User;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "plan")
@Getter
@NoArgsConstructor
@AllArgsConstructor
public class Plan {
    @Id
    @Column(name = "plan_id", nullable = false)
    private UUID planId;

    @ManyToOne
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(name = "plan_time", nullable = false)
    private LocalDateTime planTime;

    @Column(name = "plan_content")
    private String planContent;

    @ManyToOne
    @JoinColumn(name = "image_id")
    private Image image;

    @Column(name = "alarm_tf")
    private Boolean alarmTf = true;
}
