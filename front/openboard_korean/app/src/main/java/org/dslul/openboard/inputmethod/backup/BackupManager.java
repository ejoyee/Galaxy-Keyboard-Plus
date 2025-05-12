package org.dslul.openboard.inputmethod.backup;

import android.Manifest;
import android.content.Context;
import android.os.Build;
import android.util.Log;

import androidx.core.content.PermissionChecker;

import org.dslul.openboard.inputmethod.backup.model.GalleryImage;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;

/**
 * 자동 백업의 전체 흐름을 관리하는 매니저 클래스
 */
public class BackupManager {
    private static final String TAG = "Backup - BackupManager";

    /**
     * 전체 백업 흐름 실행 함수
     */
    public static void startBackup(Context context) {
        // 1. 권한 확인 (API 33 이상은 READ_MEDIA_IMAGES, 그 이하는 READ_EXTERNAL_STORAGE)
        if (!hasReadPermission(context)) {
            Log.w(TAG, "⛔ 저장소 권한이 없습니다. 백업을 건너뜁니다.");
            return;
        }

        // 2. 사용자 인증 정보 가져오기
//        String userId = TokenStore.getUserId(context);
//        String accessToken = TokenStore.getAccessToken(context);
//        if (userId.isEmpty() || accessToken.isEmpty()) {
//            Log.w(TAG, "⛔ 사용자 인증 정보 없음. 백업 중단");
//            return;
//        }

        // 3. 이미지 목록 불러오기
        long lastUploadedAt = UploadStateTracker.getLastUploadedAt(context);
        Log.d(TAG, "📌 마지막 업로드된 timestamp: " + lastUploadedAt);

        List<GalleryImage> allImages = MediaStoreImageFetcher.getAllImages(context);
        Log.d(TAG, "📸 전체 불러온 이미지 수: " + allImages.size());

        // 4. 마지막 업로드 시간 이후의 이미지만 필터링
        List<GalleryImage> newImages = new ArrayList<>();
        for (GalleryImage image : allImages) {
            if (image.getTimestamp() >= lastUploadedAt) {
                newImages.add(image);
            }
        }

        // 최신순 정렬
        Collections.sort(newImages, new Comparator<GalleryImage>() {
            @Override
            public int compare(GalleryImage o1, GalleryImage o2) {
                return Long.compare(o2.getTimestamp(), o1.getTimestamp()); // 내림차순
            }
        });

        // 최대 50장 제한
        if (newImages.size() > 50) {
            newImages = newImages.subList(0, 50);
        }

        if (newImages.isEmpty()) {
            Log.i(TAG, "🟰 업로드할 새로운 이미지가 없습니다.");
            return;
        }

        Log.i(TAG, "새 이미지 " + newImages.size() + "개 업로드 시작");

        // 5. 이미지 업로드
        ImageUploader.uploadImages(
                context,
                newImages,
                "3fa85f64-5717-4562-b3fc-2c963f66afa6", // userId
                "", // accessToken
                new ImageUploader.SuccessCallback() {
                    @Override
                    public void onSuccess(String contentId) {
                        Log.d(TAG, "✅ 업로드 성공: " + contentId);
                    }
                },
                new ImageUploader.FailureCallback() {
                    @Override
                    public void onFailure(String filename, Throwable throwable) {
                        Log.e(TAG, "❌ 업로드 실패: " + filename, throwable);
                    }
                }
        );

        // 6. 가장 마지막 이미지의 timestamp 저장
        long latestTimestamp = lastUploadedAt;
        for (GalleryImage image : newImages) {
            if (image.getTimestamp() > latestTimestamp) {
                latestTimestamp = image.getTimestamp();
            }
        }

        UploadStateTracker.setLastUploadedAt(context, latestTimestamp);
    }

    private static boolean hasReadPermission(Context context) {
        String permission = Build.VERSION.SDK_INT >= 33
                ? Manifest.permission.READ_MEDIA_IMAGES // ✅ 정확한 권한 이름
                : Manifest.permission.READ_EXTERNAL_STORAGE;

        return PermissionChecker.checkSelfPermission(context, permission)
                == PermissionChecker.PERMISSION_GRANTED;
    }
}
