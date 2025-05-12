package org.dslul.openboard.inputmethod.backup;

import android.content.Context;
import android.util.Log;

import org.dslul.openboard.inputmethod.backup.model.GalleryImage;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.List;
import java.util.Locale;

import okhttp3.MediaType;
import okhttp3.MultipartBody;
import okhttp3.RequestBody;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

/**
 * 서버로 이미지 업로드를 수행하는 유틸 클래스
 */

public class ImageUploader {
    private static final String TAG = "Backup - ImageUploader";

    /**
     * 이미지 리스트를 서버에 업로드
     * @param context Context
     * @param images 업로드할 이미지 목록
     * @param userId 사용자 ID
     * @param accessToken JWT 토큰
     * @param onSuccess 성공 시 콜백 (image.contentId 전달)
     * @param onFailure 실패 시 콜백 (filename, throwable 전달)
     */
    public static void uploadImages(
            Context context,
            List<GalleryImage> images,
            String userId,
            String accessToken,
            SuccessCallback onSuccess,
            FailureCallback onFailure,
            CompletionCallback onComplete
    ) {
        // HTTP 요청을 처리할 Retrofit 인스턴스를 생성
        ImageUploadApi api = RetrofitInstance.getApi();
        int total = images.size();
        final int[] completedCount = {0};

        // 넘겨받은 이미지 리스트를 순회하며 하나씩 업로드
        for (GalleryImage image : images) {
            try {
                // MediaStore URI로부터 InputStream 열기
                InputStream inputStream = context.getContentResolver().openInputStream(image.getUri());
                if (inputStream == null) {
                    Log.w(TAG, "InputStream is null for " + image.getUri());
                    continue;
                }

                // 이미지 바이트로 읽기 + 적절한 MIME 타입 지정
                byte[] imageBytes = readBytes(inputStream);
                MediaType mediaType = MediaType.parse(image.getMimeType());
                RequestBody imageBody = RequestBody.create(mediaType, imageBytes);

                // Retrofit용 Multipart 파트 생성 (파일 첨부용)
                MultipartBody.Part filePart = MultipartBody.Part.createFormData(
                        "file",
                        image.getFilename(),
                        imageBody
                );

                // timestamp를 yyyy:MM:dd HH:mm:ss 형식으로 변환
                String formattedTime = new SimpleDateFormat("yyyy:MM:dd HH:mm:ss", Locale.getDefault())
                        .format(new Date(image.getTimestamp()));

                // 문자열 파라미터용 RequestBody 생성
                RequestBody userIdBody = RequestBody.create(MediaType.parse("text/plain"), userId);
                RequestBody accessIdBody = RequestBody.create(MediaType.parse("text/plain"), image.getContentId());
                RequestBody imageTimeBody = RequestBody.create(MediaType.parse("text/plain"), formattedTime);

                // Retrofit 호출 객체 생성 (POST multipart 요청)
                Call<Void> call = api.uploadImage(
                        "Bearer " + accessToken,
                        userIdBody,
                        accessIdBody,
                        imageTimeBody,
                        filePart
                );

                // 비동기 요청 실행 (enqueue)
                call.enqueue(new Callback<Void>() {
                    @Override
                    public void onResponse(Call<Void> call, Response<Void> response) {
                        if (response.isSuccessful()) {
                            // 성공 시 로그 출력 및 콜백 호출
                            Log.i(TAG, "✅ Uploaded: " + image.getFilename());
                            if (onSuccess != null) {
                                onSuccess.onSuccess(image.getContentId());
                            }
                        } else {
                            // 실패 시 상태 코드 로그 출력
                            Log.w(TAG, "⚠️ Upload failed: " + response.code() + " - " + image.getFilename());
                        }
                        if (++completedCount[0] == total && onComplete != null) {
                            onComplete.onComplete();
                        }
                    }

                    @Override
                    public void onFailure(Call<Void> call, Throwable t) {
                        Log.e(TAG, "Upload failed: " + image.getFilename(), t);
                        if (onFailure != null) {
                            onFailure.onFailure(image.getFilename(), t);
                        }
                        if (++completedCount[0] == total && onComplete != null) {
                            onComplete.onComplete();
                        }
                    }
                });

            } catch (Exception e) {
                // try 블록에서 예외 발생 시 로그 및 콜백 처리
                Log.e(TAG, "Exception during upload: " + image.getFilename(), e);
                if (onFailure != null) {
                    onFailure.onFailure(image.getFilename(), e);
                }
            }
        }
    }

    private static byte[] readBytes(InputStream inputStream) throws IOException {
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        byte[] data = new byte[4096];
        int nRead;
        while ((nRead = inputStream.read(data, 0, data.length)) != -1) {
            buffer.write(data, 0, nRead);
        }
        return buffer.toByteArray();
    }

    // 성공 콜백 인터페이스
    public interface SuccessCallback {
        void onSuccess(String contentId);
    }

    // 실패 콜백 인터페이스
    public interface FailureCallback {
        void onFailure(String filename, Throwable throwable);
    }

    // Completion 콜백
    public interface CompletionCallback {
        void onComplete();
    }

}
