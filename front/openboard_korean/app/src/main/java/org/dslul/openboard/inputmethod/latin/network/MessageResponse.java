package org.dslul.openboard.inputmethod.latin.network;

import java.util.ArrayList;
import java.util.List;

public class MessageResponse {
    private String queryType;

    private String answer;

    private List<PhotoResult> photoResults = new ArrayList<>();

    private List<InfoResult> infoResults = new ArrayList<>();

    public String getQueryType() {
        return queryType;
    }

    public String getAnswer() {
        return answer;
    }

    public List<PhotoResult> getPhotoResults() {
        return photoResults;
    }

    public List<InfoResult> getInfoResults() {
        return infoResults;
    }

    public MessageResponse setAnswer(String answer) {
        this.answer = answer;
        return this;
    }
}
