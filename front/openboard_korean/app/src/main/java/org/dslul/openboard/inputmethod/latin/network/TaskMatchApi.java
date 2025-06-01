package org.dslul.openboard.inputmethod.latin.network;

import retrofit2.Call;
import retrofit2.http.GET;
import retrofit2.http.Query;

public interface TaskMatchApi {
    @GET("/search/mcp/match/")
    Call<TaskMatchResponse> match(@Query("word") String word);
}