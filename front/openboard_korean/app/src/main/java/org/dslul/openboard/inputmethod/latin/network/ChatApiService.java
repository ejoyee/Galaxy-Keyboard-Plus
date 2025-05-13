package org.dslul.openboard.inputmethod.latin.network;

import retrofit2.Call;
import retrofit2.http.Field;
import retrofit2.http.FormUrlEncoded;
import retrofit2.http.POST;

public interface ChatApiService {
    @FormUrlEncoded
    @POST("rag/search/")
    Call<MessageResponse> search(
            @Field("user_id") String userId,
            @Field("query") String query
    );
}
