package com.backend.image.presentation.request;

import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.UUID;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class SaveImageRequest {
    @NotNull
    private UUID userId;
    @NotNull
    private String accessId;

    private String imageTime;
    private Float type;
    private String content;
}
