package org.dslul.openboard.inputmethod.latin.login;

import android.app.Activity;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.Signature;
import android.os.Bundle;
import android.util.Base64;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.ProgressBar;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import org.dslul.openboard.inputmethod.latin.R;
import org.dslul.openboard.inputmethod.latin.auth.AuthCallback;
import org.dslul.openboard.inputmethod.latin.auth.AuthManager;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/**
 * 카카오 로그인 화면
 */
public class KakaoLoginActivity extends Activity {

    private AuthManager authManager;
    private Button btnKakaoLogin;
    private ProgressBar progressBar;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_kakao_login);

        // 매니저 인스턴스 초기화
        authManager = AuthManager.getInstance(this);
        authManager.setCurrentActivity(this); // 현재 액티비티 설정

        // 뷰 초기화
        btnKakaoLogin = findViewById(R.id.btn_kakao_login);
        progressBar = findViewById(R.id.progress_bar);

        // 이미 로그인되어 있는 경우 처리
        if (authManager.isLoggedIn()) {
            Toast.makeText(this, "이미 로그인되어 있습니다: " + authManager.getUserId(), Toast.LENGTH_SHORT).show();
            finish();
            return;
        }

        // 로그인 버튼 이벤트 설정
        btnKakaoLogin.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                performKakaoLogin();
            }
        });


        try {
            PackageInfo info = getPackageManager().getPackageInfo(getPackageName(), PackageManager.GET_SIGNATURES);
            for (Signature signature : info.signatures) {
                MessageDigest md = MessageDigest.getInstance("SHA");
                md.update(signature.toByteArray());
                String hash = Base64.encodeToString(md.digest(), Base64.DEFAULT);
                Log.d("KeyHash", "키해시: " + hash);
            }
        } catch (PackageManager.NameNotFoundException | NoSuchAlgorithmException e) {
            e.printStackTrace();
        }


    }

    @Override
    protected void onResume() {
        super.onResume();
        // 화면이 다시 보일 때마다 현재 액티비티 업데이트
        if (authManager != null) {
            authManager.setCurrentActivity(this);
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        // 화면이 사라질 때 현재 액티비티 참조 제거 (메모리 누수 방지)
        if (authManager != null) {
            authManager.setCurrentActivity(null);
        }
    }

    /**
     * 카카오 로그인 수행
     */
    private void performKakaoLogin() {
        // 로딩 표시
        setLoading(true);

        // 로그인 요청
        authManager.loginWithKakao(new AuthCallback() {
            @Override
            public void onLoginSuccess(final String userId) {
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        setLoading(false);
                        Toast.makeText(KakaoLoginActivity.this,
                                "로그인 성공: " + userId, Toast.LENGTH_SHORT).show();

                        // 로그인 성공 후 액티비티 종료
                        setResult(RESULT_OK);
                        finish();
                    }
                });
            }

            @Override
            public void onLoginFailure(final String errorMessage) {
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        setLoading(false);
                        Toast.makeText(KakaoLoginActivity.this,
                                "로그인 실패: " + errorMessage, Toast.LENGTH_LONG).show();
                    }
                });
            }

            @Override
            public void onLogoutSuccess() {
                // 로그인 화면에서는 사용되지 않음
            }
        });
    }

    /**
     * 로딩 상태 표시
     */
    private void setLoading(boolean isLoading) {
        btnKakaoLogin.setEnabled(!isLoading);
        progressBar.setVisibility(isLoading ? View.VISIBLE : View.GONE);
    }
}