package com.auth.repository;

import com.auth.domain.UserInfo;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.*;

public interface UserInfoRepository extends JpaRepository<UserInfo, java.util.UUID> {
    Optional<UserInfo> findByKakaoEmail(String kakaoEmail);
}


