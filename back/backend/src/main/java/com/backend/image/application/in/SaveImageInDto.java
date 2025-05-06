package com.backend.image.application.in;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.UUID;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class SaveImageInDto {
    private UUID userId;
    private String accessId;
    private String imageTime;
    private Float type;
    private String content;
}
