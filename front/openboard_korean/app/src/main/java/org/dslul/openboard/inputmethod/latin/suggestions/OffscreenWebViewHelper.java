package org.dslul.openboard.inputmethod.latin.suggestions;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.net.Uri;
import android.os.Handler;
import android.os.Looper;
import android.util.DisplayMetrics;
import android.view.View;
import android.webkit.WebChromeClient;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.core.content.FileProvider;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
public class OffscreenWebViewHelper {
    public interface OnCaptureListener {
        void onCaptured(@NonNull Uri contentUri);
        void onError(@NonNull Exception e);
    }

    private final Context mContext;
    private final String mFileProviderAuthority;

    public OffscreenWebViewHelper(@NonNull Context context, @NonNull String fileProviderAuthority) {
        mContext = context.getApplicationContext();
        mFileProviderAuthority = fileProviderAuthority;
    }

    /**
     * HTML 문자열을 로드하여 전체 콘텐츠를 캡처합니다.
     * @param htmlContent 캡처할 HTML (loadDataWithBaseURL 호출용)
     * @param listener 완료 콜백
     */
    public void captureHtml(@NonNull final String htmlContent, @NonNull final OnCaptureListener listener) {
        new Handler(Looper.getMainLooper()).post(() -> {
            // 1) Offscreen WebView 생성
            final WebView offscreenWebView = new WebView(mContext);
            offscreenWebView.getSettings().setJavaScriptEnabled(true);
            offscreenWebView.setVisibility(View.GONE);          // 화면에 보이지 않도록
            offscreenWebView.setWebViewClient(new WebViewClient() {
                @Override
                public void onPageFinished(WebView view, String url) {
                    captureBitmap(offscreenWebView, htmlContent, listener);
                }
            });
            // 반드시 내부적으로도 ChromeClient를 설정하여 일부 레이아웃 이슈 예방
            offscreenWebView.setWebChromeClient(new WebChromeClient());

            // 2) loadDataWithBaseURL 호출 (baseURL을 null로 두면 상대경로가 없을 때도 상관없음)
            offscreenWebView.loadDataWithBaseURL(null, htmlContent, "text/html", "UTF-8", null);
        });
    }

    private void captureBitmap(@NonNull WebView webView,
                               @NonNull String htmlContent,
                               @NonNull OnCaptureListener listener) {
        try {
            // (A) 전체 콘텐츠 높이 계산
            DisplayMetrics metrics = mContext.getResources().getDisplayMetrics();
            float density = metrics.density;
            int contentHeightCssPx = webView.getContentHeight(); // CSS 픽셀 단위
            final int fullHeightPx = (int) (contentHeightCssPx * density);

            Toast.makeText(mContext, "contentHeightCssPx=" + contentHeightCssPx + ", fullHeightPx=" + fullHeightPx, Toast.LENGTH_SHORT).show();

            if (fullHeightPx <= 0) {
                throw new IllegalStateException("WebView 콘텐츠 높이를 가져올 수 없습니다.");
            }

            // (B) Measure & Layout (off-screen 상태)
            int viewWidth = webView.getWidth();
            if (viewWidth == 0) {
                // 아직 크기가 측정되지 않았다면, 전체 화면 너비를 기준으로 설정하거나 임의 픽셀 값을 지정
                // 여기서는 디스플레이 너비를 기준으로 삼습니다.
                viewWidth = metrics.widthPixels;
            }

            Toast.makeText(mContext, "viewWidth=" + viewWidth, Toast.LENGTH_SHORT).show();

            // 정확하게 fullWidth x fullHeight 크기로 measure + layout
            int widthSpec = View.MeasureSpec.makeMeasureSpec(viewWidth, View.MeasureSpec.EXACTLY);
            int heightSpec = View.MeasureSpec.makeMeasureSpec(fullHeightPx, View.MeasureSpec.EXACTLY);
            webView.measure(widthSpec, heightSpec);
            webView.layout(0, 0, viewWidth, fullHeightPx);

            Toast.makeText(mContext, "레이아웃 완료: " + viewWidth + "x" + fullHeightPx, Toast.LENGTH_SHORT).show();

            // (C) 비트맵 생성 및 WebView 전체 내용 그리기
            Bitmap bitmap = Bitmap.createBitmap(viewWidth, fullHeightPx, Bitmap.Config.ARGB_8888);
            Canvas canvas = new Canvas(bitmap);
            webView.draw(canvas);

            Toast.makeText(mContext, "비트맵 생성 완료", Toast.LENGTH_SHORT).show();

            // (D) 캐시/images 폴더 준비
            File cacheDir = mContext.getCacheDir();
            File imagesDir = new File(cacheDir, "offscreen_images");
            if (!imagesDir.exists() && !imagesDir.mkdirs()) {
                throw new IOException("임시 폴더(offscreen_images/) 생성 실패");
            }

            Toast.makeText(mContext, "디렉토리 준비 완료: " + imagesDir.getAbsolutePath(), Toast.LENGTH_SHORT).show();

            // (E) 파일 이름 생성 후 저장
            String fileName = "offscreen_capture_" + System.currentTimeMillis() + ".png";
            File imageFile = new File(imagesDir, fileName);
            try (FileOutputStream fos = new FileOutputStream(imageFile)) {
                bitmap.compress(Bitmap.CompressFormat.PNG, 100, fos);
                fos.flush();
            }

            Toast.makeText(mContext, "파일 저장 완료: " + imageFile.getName(), Toast.LENGTH_SHORT).show();

            // (F) FileProvider를 통해 content:// URI 생성
            Uri resultUri = FileProvider.getUriForFile(mContext, mFileProviderAuthority, imageFile);

            Toast.makeText(mContext, "URI 발급 완료: " + resultUri.toString(), Toast.LENGTH_SHORT).show();

            // (G) offscreenWebView 정리
            webView.stopLoading();
            webView.clearHistory();
            webView.removeAllViews();
            webView.destroy();

            Toast.makeText(mContext, "WebView 정리 완료", Toast.LENGTH_SHORT).show();

            // (H) 콜백
            listener.onCaptured(resultUri);

        } catch (Exception e) {
            Toast.makeText(mContext, "캡처 중 예외: " + e.getMessage(), Toast.LENGTH_LONG).show();

            // 캡처나 파일 저장 중 예외 발생 시 onError 호출
            listener.onError(e);
        }
    }
}