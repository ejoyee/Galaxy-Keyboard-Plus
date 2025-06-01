package org.dslul.openboard.inputmethod.latin.network;

import okhttp3.ResponseBody;
import retrofit2.Call;
import retrofit2.http.Body;
import retrofit2.http.POST;

public interface AirbnbApi {
    @POST("mcp/api/search/airbnb-search-html")
    Call<ResponseBody> searchHtml(@Body AirbnbSearchReq body);
}