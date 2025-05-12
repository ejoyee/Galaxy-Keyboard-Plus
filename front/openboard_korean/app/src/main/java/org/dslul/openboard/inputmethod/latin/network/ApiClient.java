package org.dslul.openboard.inputmethod.latin.network;

import java.util.concurrent.TimeUnit;

import okhttp3.OkHttpClient;
import okhttp3.logging.HttpLoggingInterceptor;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

public class ApiClient {
    private static final String BASE_URL = "http://k12e201.p.ssafy.io:8090/"; // 슬래시 포함
    private static Retrofit retrofit;

    public static ChatApiService service() {
        if (retrofit == null) {
            // 전체 패킷을 logcat에 찍어 주는 interceptor
            HttpLoggingInterceptor log = new HttpLoggingInterceptor();
            log.setLevel(HttpLoggingInterceptor.Level.BODY);

            OkHttpClient client = new OkHttpClient.Builder()
                    .addInterceptor(log)
                    // ▼ 타임아웃 설정 -------------------------------------------------
                    .connectTimeout(120, TimeUnit.SECONDS)   // 연결
                    .readTimeout   (120, TimeUnit.SECONDS)   // 서버 응답(Body) 대기
                    .writeTimeout  (120, TimeUnit.SECONDS)   // 요청 Body 전송
                    // ---------------------------------------------------------------
                    .build();


            retrofit = new Retrofit.Builder()
                    .baseUrl(BASE_URL)
                    .client(client)
                    .addConverterFactory(GsonConverterFactory.create())
                    .build();
        }
        return retrofit.create(ChatApiService.class);
    }
}
