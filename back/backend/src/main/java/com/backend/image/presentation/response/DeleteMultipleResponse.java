package com.backend.image.presentation.response;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.UUID;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class DeleteMultipleResponse {
    Integer successCount;
    Integer failedCount;
    List<UUID> failedImages;
}
