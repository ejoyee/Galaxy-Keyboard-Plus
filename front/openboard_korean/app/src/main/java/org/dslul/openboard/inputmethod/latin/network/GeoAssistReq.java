package org.dslul.openboard.inputmethod.latin.network;

public class GeoAssistReq {
    public String query;
    public Loc location = new Loc();
    public static class Loc {
        public double latitude;
        public double longitude;
    }
}