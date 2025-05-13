package org.dslul.openboard.inputmethod.latin.settings;

import android.app.Activity;
import android.os.Bundle;

import com.kakao.sdk.common.KakaoSdk;

import org.dslul.openboard.inputmethod.latin.R;
import org.dslul.openboard.inputmethod.latin.BuildConfig;
import org.dslul.openboard.inputmethod.latin.network.ApiClient;

public class SearchActivity extends Activity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        ApiClient.init(this);
        setContentView(R.layout.activity_search);

        // 프래그먼트 붙이기
        if (savedInstanceState == null) {
            getFragmentManager()
                    .beginTransaction()
                    .replace(R.id.fragment_container, new SearchPageFragment())
                    .commit();
        }

        KakaoSdk.init(getApplicationContext(), BuildConfig.KAKAO_NATIVE_APP_KEY);
    }
}
