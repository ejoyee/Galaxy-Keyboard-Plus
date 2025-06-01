package org.dslul.openboard.inputmethod.latin.network;

import com.google.gson.annotations.SerializedName;

public class TaskMatchResponse {
    @SerializedName("matched_task")   // JSON 키
    public String matchedTask;        // Java 필드(카멜 케이스)
}