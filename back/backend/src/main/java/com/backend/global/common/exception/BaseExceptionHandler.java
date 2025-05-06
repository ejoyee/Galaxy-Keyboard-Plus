package com.backend.global.common.exception;

import com.backend.global.common.response.BaseResponse;
import com.backend.global.common.response.BaseResponseStatus;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.http.ResponseEntity;
import jakarta.validation.ConstraintViolationException;
import org.springframework.web.bind.MethodArgumentNotValidException;

@Slf4j
@RestControllerAdvice
public class BaseExceptionHandler {
    /**
     * 등록된 에러 처리
     */
    @ExceptionHandler(BaseException.class)
    protected ResponseEntity<BaseResponse<Void>> BaseError(BaseException e) {

        log.info("BaseException -> {}({})", e.getStatus(), e.getStatus().getMessage(), e);

        BaseResponse<Void> response = new BaseResponse<>(e.getStatus());
        return new ResponseEntity<>(response, response.httpStatus());
    }

    /**
     * 런타임 에러 처리
     * 비즈니스 로직 상 잘 못 값이 입력되는 경우 등
     */
    @ExceptionHandler(RuntimeException.class)
    protected ResponseEntity<BaseResponse<Void>> RuntimeError(RuntimeException e) {

        StackTraceElement[] stackTrace = e.getStackTrace();
        log.error("RuntimeException -> {}", stackTrace[0]);

        BaseResponse<Void> response = new BaseResponse<>(BaseResponseStatus.INTERNAL_SERVER_ERROR);
        return new ResponseEntity<>(response, response.httpStatus());
    }

    /**
     * 검증 실패 에러 처리
     * MethodArgumentNotValidException @Valid 유효성 검사 실패
     * ConstraintViolationException @Validated 유효성 검사 실패
     */
    @ExceptionHandler({ConstraintViolationException.class, MethodArgumentNotValidException.class})
    protected ResponseEntity<BaseResponse<Void>> ConstraintViolationException(Exception e) {

        // 검증 실패한 필드와 메시지를 추출
        log.info("검증 실패 Exception -> {}", e.getMessage(), e);

        BaseResponse<Void> response = new BaseResponse<>(BaseResponseStatus.INVALID_INPUT_VALUE);
        return new ResponseEntity<>(response, response.httpStatus());
    }
}
