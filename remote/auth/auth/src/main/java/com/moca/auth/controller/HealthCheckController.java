package com.moca.auth.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

/**
 * 서비스 상태 확인을 위한 헬스 체크 컨트롤러
 */
@RestController
@RequestMapping("/auth/health")
public class HealthCheckController {

    /**
     * 서비스 상태 확인 엔드포인트
     * 
     * @return 서비스 상태 정보
     */
    @GetMapping
    public ResponseEntity<Map<String, Object>> checkHealth() {
        Map<String, Object> healthInfo = new HashMap<>();
        healthInfo.put("service", "auth");
        healthInfo.put("status", "UP");
        healthInfo.put("timestamp", LocalDateTime.now().toString());
        
        return ResponseEntity.ok(healthInfo);
    }
}
