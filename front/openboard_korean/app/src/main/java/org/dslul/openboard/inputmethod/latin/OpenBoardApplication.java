package org.dslul.openboard.inputmethod.latin;

import android.app.Application;
import com.kakao.sdk.common.KakaoSdk;

/**
 * 애플리케이션 클래스 - 앱 초기화 담당
 */
public class OpenBoardApplication extends Application {
    @Override
    public void onCreate() {
        super.onCreate();

        // 카카오 SDK 초기화 (실제 앱 키로 교체)
        KakaoSdk.INSTANCE.init(this, "c82463a00457035bcc958acd89ea97ba");
    }
}