package org.dslul.openboard.inputmethod.latin.network;

import okhttp3.ResponseBody;
import retrofit2.Call;
import retrofit2.http.Body;
import retrofit2.http.POST;

public interface GeoAssistApi {
    @POST("mcp/api/geo-assist/")
    Call<ResponseBody> geoAssist(@Body GeoAssistReq body);
}