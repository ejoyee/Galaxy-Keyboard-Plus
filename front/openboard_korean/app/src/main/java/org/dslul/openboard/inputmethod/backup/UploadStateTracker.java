package org.dslul.openboard.inputmethod.backup;


import android.content.Context;
import android.content.SharedPreferences;

import java.util.concurrent.TimeUnit;

/**
 * 마지막 업로드된 이미지의 timestamp를 저장/조회하는 클래스
 */
public class UploadStateTracker {
    private static final String PREF_NAME = "upload_state";
    private static final String KEY_LAST_UPLOADED_AT = "last_uploaded_at";

    private static SharedPreferences getPrefs(Context context) {
        return context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE);
    }

    /**
     * 마지막 업로드된 timestamp를 저장 (밀리초)
     */
    public static void setLastUploadedAt(Context context, long timestamp) {
        getPrefs(context).edit().putLong(KEY_LAST_UPLOADED_AT, timestamp).apply();
    }

    /**
     * 마지막 업로드된 timestamp를 반환 (기본값: 0)
     */
    public static long getLastUploadedAt(Context context) {
        return getPrefs(context).getLong(KEY_LAST_UPLOADED_AT, 0L);
    }

    /**
     * 마지막 업로드 시간이 24시간 이상 지났는지 여부 확인
     */
    public static boolean isExpired(Context context) {
        return isExpired(context, TimeUnit.HOURS.toMillis(24));
    }

    public static boolean isExpired(Context context, long thresholdMillis) {
        long last = getLastUploadedAt(context);
        long now = System.currentTimeMillis();
        return (now - last) > thresholdMillis;
    }

    /**
     * 초기화 (테스트용 또는 리셋용)
     */
    public static void clear(Context context) {
        getPrefs(context).edit().remove(KEY_LAST_UPLOADED_AT).apply();
    }
}
