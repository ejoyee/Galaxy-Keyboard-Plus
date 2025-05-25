package org.dslul.openboard.inputmethod.latin.inputlogic;

public final class HangulUtils {
    private HangulUtils(){}

    /** 해당 코드포인트가 유니코드 완성형 한글 음절인가? */
    public static boolean isHangulSyllable(int cp) {
        return (cp >= 0xAC00 && cp <= 0xD7A3)   // 기본
                || (cp >= 0xD7B0 && cp <= 0xD7C6)   // 확장 A
                || (cp >= 0xD7CB && cp <= 0xD7FB);  // 확장 B
    }

    /** 커서 직전에 있는 ‘하나의 음절’ 시작 인덱스(자바 char 기준)를 돌려준다. */
    public static int findSyllableStart(CharSequence text, int cursor){
        int i = Math.max(0, cursor-1);
        while(i>0 && isHangulSyllable(Character.codePointAt(text, i)))
            i--;
        // i가 음절이 아닌 곳을 가리키므로 +1
        return isHangulSyllable(Character.codePointAt(text, i)) ? i : i+1;
    }

    /** 커서 직전에 있는 음절 길이(char 단위)를 돌려준다. */
    public static int syllableLength(CharSequence text, int cursor){
        if(cursor==0) return 0;
        int start = findSyllableStart(text, cursor);
        return cursor - start;
    }
}
