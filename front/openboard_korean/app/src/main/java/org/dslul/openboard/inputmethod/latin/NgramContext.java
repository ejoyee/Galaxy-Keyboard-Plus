/*
 * Copyright (C) 2014 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.dslul.openboard.inputmethod.latin;

import android.text.TextUtils;

import org.dslul.openboard.inputmethod.annotations.UsedForTesting;
import org.dslul.openboard.inputmethod.latin.common.StringUtils;
import org.dslul.openboard.inputmethod.latin.define.DecoderSpecificConstants;

import java.util.ArrayList;
import java.util.Arrays;

import javax.annotation.Nonnull;

/**
 * Class to represent information of previous words. This class is used to add n-gram entries
 * into binary dictionaries, to get predictions, and to get suggestions.
 */
public class NgramContext {
    @Nonnull
    public static final NgramContext EMPTY_PREV_WORDS_INFO =
            new NgramContext(WordInfo.EMPTY_WORD_INFO);
    @Nonnull
    public static final NgramContext BEGINNING_OF_SENTENCE =
            new NgramContext(WordInfo.BEGINNING_OF_SENTENCE_WORD_INFO);

    public static final String BEGINNING_OF_SENTENCE_TAG = "<S>";

    public static final String CONTEXT_SEPARATOR = " ";

    public static NgramContext getEmptyPrevWordsContext(int maxPrevWordCount) {
        return new NgramContext(maxPrevWordCount, WordInfo.EMPTY_WORD_INFO);
    }

    /**
     * Word information used to represent previous words information.
     */
    public static class WordInfo {
        @Nonnull
        public static final WordInfo EMPTY_WORD_INFO = new WordInfo(null);
        @Nonnull
        public static final WordInfo BEGINNING_OF_SENTENCE_WORD_INFO = new WordInfo();

        // This is an empty char sequence when mIsBeginningOfSentence is true.
        public final CharSequence mWord;
        // TODO: Have sentence separator.
        // Whether the current context is beginning of sentence or not. This is true when composing
        // at the beginning of an input field or composing a word after a sentence separator.
        public final boolean mIsBeginningOfSentence;

        // Beginning of sentence.
        private WordInfo() {
            mWord = "";
            mIsBeginningOfSentence = true;
        }

        public WordInfo(final CharSequence word) {
            mWord = word;
            mIsBeginningOfSentence = false;
        }

        public boolean isValid() {
            return mWord != null;
        }

        @Override
        public int hashCode() {
            return Arrays.hashCode(new Object[] { mWord, mIsBeginningOfSentence } );
        }

        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (!(o instanceof WordInfo)) return false;
            final WordInfo wordInfo = (WordInfo)o;
            if (mWord == null || wordInfo.mWord == null) {
                return mWord == wordInfo.mWord
                        && mIsBeginningOfSentence == wordInfo.mIsBeginningOfSentence;
            }
            return TextUtils.equals(mWord, wordInfo.mWord)
                    && mIsBeginningOfSentence == wordInfo.mIsBeginningOfSentence;
        }
    }

    // The words immediately before the considered word. EMPTY_WORD_INFO element means we don't
    // have any context for that previous word including the "beginning of sentence context" - we
    // just don't know what to predict using the information. An example of that is after a comma.
    // For simplicity of implementation, elements may also be EMPTY_WORD_INFO transiently after the
    // WordComposer was reset and before starting a new composing word, but we should never be
    // calling getSuggetions* in this situation.
    private final WordInfo[] mPrevWordsInfo;
    private final int mPrevWordsCount;

    private final int mMaxPrevWordCount;

    // Construct from the previous word information.
    public NgramContext(final WordInfo... prevWordsInfo) {
        this(DecoderSpecificConstants.MAX_PREV_WORD_COUNT_FOR_N_GRAM, prevWordsInfo);
    }

    public NgramContext(final int maxPrevWordCount, final WordInfo... prevWordsInfo) {
        mPrevWordsInfo = prevWordsInfo;
        mPrevWordsCount = prevWordsInfo.length;
        mMaxPrevWordCount = maxPrevWordCount;
    }

    /**
     * Create next prevWordsInfo using current prevWordsInfo.
     */
    @Nonnull
    public NgramContext getNextNgramContext(final WordInfo wordInfo) {
        final int nextPrevWordCount = Math.min(mMaxPrevWordCount, mPrevWordsCount + 1);
        final WordInfo[] prevWordsInfo = new WordInfo[nextPrevWordCount];
        prevWordsInfo[0] = wordInfo;
        System.arraycopy(mPrevWordsInfo, 0, prevWordsInfo, 1, nextPrevWordCount - 1);
        return new NgramContext(mMaxPrevWordCount, prevWordsInfo);
    }


    /**
     * Extracts the previous words context.
     *
     * @return a String with the previous words separated by white space.
     */
    public String extractPrevWordsContext() {
        final ArrayList<String> terms = new ArrayList<>();
        for (int i = mPrevWordsInfo.length - 1; i >= 0; --i) {
            if (mPrevWordsInfo[i] != null && mPrevWordsInfo[i].isValid()) {
                final NgramContext.WordInfo wordInfo = mPrevWordsInfo[i];
                if (wordInfo.mIsBeginningOfSentence) {
                    terms.add(BEGINNING_OF_SENTENCE_TAG);
                } else {
                    final String term = wordInfo.mWord.toString();
                    if (!term.isEmpty()) {
                        terms.add(term);
                    }
                }
            }
        }
        return TextUtils.join(CONTEXT_SEPARATOR, terms);
    }

    /**
     * Extracts the previous words context.
     *
     * @return a String array with the previous words.
     */
    public String[] extractPrevWordsContextArray() {
        final ArrayList<String> prevTermList = new ArrayList<>();
        for (int i = mPrevWordsInfo.length - 1; i >= 0; --i) {
            if (mPrevWordsInfo[i] != null && mPrevWordsInfo[i].isValid()) {
                final NgramContext.WordInfo wordInfo = mPrevWordsInfo[i];
                if (wordInfo.mIsBeginningOfSentence) {
                    prevTermList.add(BEGINNING_OF_SENTENCE_TAG);
                } else {
                    final String term = wordInfo.mWord.toString();
                    if (!term.isEmpty()) {
                        prevTermList.add(term);
                    }
                }
            }
        }
        final String[] contextStringArray = prevTermList.toArray(new String[prevTermList.size()]);
        return contextStringArray;
    }

    public boolean isValid() {
        return mPrevWordsCount > 0 && mPrevWordsInfo[0].isValid();
    }

    public boolean isBeginningOfSentenceContext() {
        return mPrevWordsCount > 0 && mPrevWordsInfo[0].mIsBeginningOfSentence;
    }

    // n is 1-indexed.
    // TODO: Remove
    public CharSequence getNthPrevWord(final int n) {
        if (n <= 0 || n > mPrevWordsCount) {
            return null;
        }
        return mPrevWordsInfo[n - 1].mWord;
    }

    // n is 1-indexed.
    @UsedForTesting
    public boolean isNthPrevWordBeginningOfSentence(final int n) {
        if (n <= 0 || n > mPrevWordsCount) {
            return false;
        }
        return mPrevWordsInfo[n - 1].mIsBeginningOfSentence;
    }

    public void outputToArray(final int[][] codePointArrays,
            final boolean[] isBeginningOfSentenceArray) {
        for (int i = 0; i < mPrevWordsCount; i++) {
            final WordInfo wordInfo = mPrevWordsInfo[i];
            if (wordInfo == null || !wordInfo.isValid()) {
                codePointArrays[i] = new int[0];
                isBeginningOfSentenceArray[i] = false;
                continue;
            }
            codePointArrays[i] = StringUtils.toCodePointArray(wordInfo.mWord);
            isBeginningOfSentenceArray[i] = wordInfo.mIsBeginningOfSentence;
        }
    }

    public int getPrevWordCount() {
        return mPrevWordsCount;
    }

    @Override
    public int hashCode() {
        int hashValue = 0;
        for (final WordInfo wordInfo : mPrevWordsInfo) {
            if (wordInfo == null || !WordInfo.EMPTY_WORD_INFO.equals(wordInfo)) {
                break;
            }
            hashValue ^= wordInfo.hashCode();
        }
        return hashValue;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof NgramContext)) return false;
        final NgramContext prevWordsInfo = (NgramContext)o;

        final int minLength = Math.min(mPrevWordsCount, prevWordsInfo.mPrevWordsCount);
        for (int i = 0; i < minLength; i++) {
            if (!mPrevWordsInfo[i].equals(prevWordsInfo.mPrevWordsInfo[i])) {
                return false;
            }
        }
        final WordInfo[] longerWordsInfo;
        final int longerWordsInfoCount;
        if (mPrevWordsCount > prevWordsInfo.mPrevWordsCount) {
            longerWordsInfo = mPrevWordsInfo;
            longerWordsInfoCount = mPrevWordsCount;
        } else {
            longerWordsInfo = prevWordsInfo.mPrevWordsInfo;
            longerWordsInfoCount = prevWordsInfo.mPrevWordsCount;
        }
        for (int i = minLength; i < longerWordsInfoCount; i++) {
            if (longerWordsInfo[i] != null
                    && !WordInfo.EMPTY_WORD_INFO.equals(longerWordsInfo[i])) {
                return false;
            }
        }
        return true;
    }

    @Override
    public String toString() {
        final StringBuffer builder = new StringBuffer();
        for (int i = 0; i < mPrevWordsCount; i++) {
            final WordInfo wordInfo = mPrevWordsInfo[i];
            builder.append("PrevWord[");
            builder.append(i);
            builder.append("]: ");
            if (wordInfo == null) {
                builder.append("null. ");
                continue;
            }
            if (!wordInfo.isValid()) {
                builder.append("Empty. ");
                continue;
            }
            builder.append(wordInfo.mWord);
            builder.append(", isBeginningOfSentence: ");
            builder.append(wordInfo.mIsBeginningOfSentence);
            builder.append(". ");
        }
        return builder.toString();
    }
}
