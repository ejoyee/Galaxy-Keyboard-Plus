package org.dslul.openboard.inputmethod.backup;

import okhttp3.OkHttpClient;
import okhttp3.logging.HttpLoggingInterceptor;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

public class RetrofitInstance {
    private static final String BASE_URL = "http://k12e201.p.ssafy.io:8090/";

    private static ImageUploadApi api;

    public static ImageUploadApi getApi() {
        if (api == null) {
            synchronized (RetrofitInstance.class) {
                if (api == null) {
                    HttpLoggingInterceptor logging = new HttpLoggingInterceptor();
                    logging.setLevel(HttpLoggingInterceptor.Level.BODY);

                    OkHttpClient client = new OkHttpClient.Builder()
                            .addInterceptor(logging)
                            .build();

                    Retrofit retrofit = new Retrofit.Builder()
                            .baseUrl(BASE_URL)
                            .client(client)
                            .addConverterFactory(GsonConverterFactory.create())
                            .build();

                    api = retrofit.create(ImageUploadApi.class);
                }
            }
        }
        return api;
    }
}
