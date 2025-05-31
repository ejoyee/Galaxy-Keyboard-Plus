/*
 * Copyright (C) 2011 The Android Open Source Project
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

package org.dslul.openboard.inputmethod.latin.suggestions;

import android.Manifest;
import android.animation.Animator;
import android.animation.AnimatorListenerAdapter;
import android.animation.AnimatorSet;
import android.animation.Keyframe;
import android.animation.ObjectAnimator;
import android.animation.PropertyValuesHolder;
import android.animation.ValueAnimator;
import android.app.Dialog;
import android.content.ClipData;
import android.content.ClipDescription;
import android.content.ClipboardManager;
import android.content.ContentUris;
import android.content.Context;
import android.content.ContextWrapper;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.res.Resources;
import android.content.res.TypedArray;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.ColorFilter;
import android.graphics.Paint;
import android.graphics.PixelFormat;
import android.graphics.Point;
import android.graphics.PorterDuff;
import android.graphics.RadialGradient;
import android.graphics.Shader;
import android.graphics.Typeface;
import android.graphics.drawable.ColorDrawable;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.LayerDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.provider.MediaStore;
import android.util.AttributeSet;
import android.util.Log;
import android.util.TypedValue;
import android.view.DragEvent;
import android.view.GestureDetector;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.LayoutInflater;
import android.view.MotionEvent;
import android.view.View;
import android.view.View.OnClickListener;
import android.view.View.OnLongClickListener;
import android.view.ViewGroup;
import android.view.ViewParent;
import android.view.Window;
import android.view.WindowManager;
import android.view.accessibility.AccessibilityEvent;
import android.view.animation.AccelerateInterpolator;
import android.view.animation.DecelerateInterpolator;
import android.view.animation.Interpolator;
import android.view.animation.LinearInterpolator;
import android.view.animation.OvershootInterpolator;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.ExtractedText;
import android.view.inputmethod.ExtractedTextRequest;
import android.view.inputmethod.InputConnection;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.HorizontalScrollView;
import android.widget.ImageButton;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.RelativeLayout;
import android.widget.TextView;
import android.widget.Toast;

import org.dslul.openboard.inputmethod.accessibility.AccessibilityUtils;
import org.dslul.openboard.inputmethod.keyboard.Keyboard;
import org.dslul.openboard.inputmethod.keyboard.KeyboardActionListener;
import org.dslul.openboard.inputmethod.keyboard.MainKeyboardView;
import org.dslul.openboard.inputmethod.keyboard.MoreKeysPanel;
import org.dslul.openboard.inputmethod.latin.AudioAndHapticFeedbackManager;
import org.dslul.openboard.inputmethod.latin.LatinIME;
import org.dslul.openboard.inputmethod.latin.R;
import org.dslul.openboard.inputmethod.latin.SuggestedWords;
import org.dslul.openboard.inputmethod.latin.SuggestedWords.SuggestedWordInfo;
import org.dslul.openboard.inputmethod.latin.auth.AuthManager;
import org.dslul.openboard.inputmethod.latin.common.Constants;
import org.dslul.openboard.inputmethod.latin.define.DebugFlags;
import org.dslul.openboard.inputmethod.latin.network.ApiClient;
import org.dslul.openboard.inputmethod.latin.network.ChatSaveService;
import org.dslul.openboard.inputmethod.latin.network.ClipBoardResponse;
import org.dslul.openboard.inputmethod.latin.network.ClipboardService;
import org.dslul.openboard.inputmethod.latin.network.GeoAssistReq;
import org.dslul.openboard.inputmethod.latin.network.KeywordApi;
import org.dslul.openboard.inputmethod.latin.network.KeywordExistsResponse;
import org.dslul.openboard.inputmethod.latin.network.MessageResponse;
import org.dslul.openboard.inputmethod.latin.network.TaskMatchResponse;
import org.dslul.openboard.inputmethod.latin.search.SearchResultView;
import org.dslul.openboard.inputmethod.latin.settings.Settings;
import org.dslul.openboard.inputmethod.latin.settings.SettingsValues;
import org.dslul.openboard.inputmethod.latin.suggestions.MoreSuggestionsView.MoreSuggestionsListener;

import java.io.IOException;
import java.net.URISyntaxException;
import java.util.ArrayList;
import java.util.List;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.cardview.widget.CardView;
import androidx.core.content.ContextCompat;
import androidx.core.view.ViewCompat;
import androidx.core.view.inputmethod.EditorInfoCompat;
import androidx.core.view.inputmethod.InputConnectionCompat;
import androidx.core.view.inputmethod.InputContentInfoCompat;
import androidx.interpolator.view.animation.FastOutSlowInInterpolator;

import com.airbnb.lottie.LottieAnimationView;
import com.airbnb.lottie.LottieDrawable;
import com.bumptech.glide.Glide;
import com.bumptech.glide.load.engine.DiskCacheStrategy;
import com.bumptech.glide.load.resource.drawable.DrawableTransitionOptions;
import com.google.android.gms.location.FusedLocationProviderClient;
import com.google.android.gms.location.LocationServices;
import com.google.android.gms.location.Priority;
import com.google.gson.Gson;

import okhttp3.ResponseBody;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

import org.greenrobot.eventbus.EventBus;
import org.greenrobot.eventbus.Subscribe;
import org.greenrobot.eventbus.ThreadMode;
import org.dslul.openboard.inputmethod.event.HangulCommitEvent;

public final class SuggestionStripView extends RelativeLayout implements OnClickListener, OnLongClickListener {
    public interface Listener {
        void pickSuggestionManually(SuggestedWordInfo word);

        void onCodeInput(int primaryCode, int x, int y, boolean isKeyRepeat);

        void onTextInput(final String rawText);

        CharSequence getSelection();
    }

    /* ▼ 새로 추가할 필드들 --------------------------------------------------- */
    private static final int DEFAULT_TASK_ICON = R.drawable.ic_plus;
    private static final Typeface STRIP_TYPEFACE = Typeface.create("samsung_one", Typeface.NORMAL); // 시스템 폰트명
    private static final float STRIP_TEXT_SCALE = 0.9f;     // 10% 확대
    private final ImageButton mFetchClipboardKey;
    private int mDefaultHeight = 0;
    private final HorizontalScrollView mPhotoBar;
    private final LinearLayout mPhotoBarContainer;
    private final TextView mSearchAnswer;
    private final LottieAnimationView mSearchKey;
    private final ImageView mLoadingSpinner;
    private String mLastKeywordWithImages = null;
    private final ImageButton mVoiceKey;       // 마이크
    private boolean mInSearchMode = false;
    private boolean mIsPausedBlue = false;

    /**
     * 파랑 JSON(pause된) 상태인지 알려주는 메서드
     */
    public boolean isPausedBlue() {
        return mIsPausedBlue;
    }

    private String mLastQuery;
    private LatinIME mImeService = null;

    private boolean mIsDragging = false;
    private int mDragExtra = 0;
    private boolean mDragHover = false;
    private final Paint mOverlayPaint;
    private final Paint mOverlayPaintHover;

    // 기존 필드 바로 아래
    private final Drawable mIconClose;    // X 아이콘

    private static final String TAG_NET = "SearchAPI";
    private static String DEFAULT_USER_ID;
    private SearchResultView mSearchPanel;

    static final boolean DBG = DebugFlags.DEBUG_ENABLED;
    private static final float DEBUG_INFO_TEXT_SIZE_IN_DIP = 6.0f;

    private final ViewGroup mSuggestionsStrip;
    private final ImageButton mClipboardKey;
    MainKeyboardView mMainKeyboardView;

    // 상황 구분용
    private enum ResponseType {LONG_TEXT, PHOTO_ONLY, SHORT_TEXT}

    private ResponseType mResponseType;
    private MessageResponse mLastResponse;
    private boolean mKeyHighlighted = false; // 깜빡임→강조 상태 구분
    private boolean mAnswerShown = false;    // 답변(말풍선) 이미 그렸는지

    private final View mMoreSuggestionsContainer;
    private final MoreSuggestionsView mMoreSuggestionsView;
    private final MoreSuggestions.Builder mMoreSuggestionsBuilder;

    private final ArrayList<TextView> mWordViews = new ArrayList<>();
    private final ArrayList<TextView> mDebugInfoViews = new ArrayList<>();
    private final ArrayList<View> mDividerViews = new ArrayList<>();

    Listener mListener;
    private SuggestedWords mSuggestedWords = SuggestedWords.getEmptyInstance();
    private int mStartIndexOfMoreSuggestions;

    private final SuggestionStripLayoutHelper mLayoutHelper;
    private final StripVisibilityGroup mStripVisibilityGroup;

    private ValueAnimator mBorderPulseAnimator;
    private final Drawable mOriginalSearchKeyBg;

    private EditorInfo mEditorInfo;
    private final Drawable mDropIcon;
    private final int mDropIconSize;
    private final int mPhotoBarSizePx;
    private final LinearLayout.LayoutParams mPhotoItemLp;
    private final ImageButton mTaskKey;
    private boolean mTaskMatched = false;   // 이미 매칭돼 있으면 true
    private String mMatchedTask = null;
    private String mMatchedWord = null;
    private final TextView mTaskLabel;               // 등장할 문구
    private static final long TASK_ANIM_DURATION = 400; // ms

    private boolean mPhotoOnlyLocked = false;
    private boolean mScrollTipShown = false;   // 스크롤 툴팁 이미 보여줬는지
    private boolean mDragTipShown = false;      // 드래그 툴팁 이미 보여줬는지
    private FrameLayout mDragTipView;
    private final Handler mTipHandler = new Handler(Looper.getMainLooper());
    private Runnable mDragTipRunnable;

    // 키보드 웨이브 관련
    private ValueAnimator mScanAnimator;
    private ScanWaveDrawable mScanWaveDrawable;

    private String mGeoAssistHtml;   // 응답 HTML 저장
    private boolean mGeoAssistReady = false;

    private final FusedLocationProviderClient mFusedLocationClient;

    // 한 곳에서 쓰기 편하도록
    private boolean isPhotoOnlyLocked() {
        return mPhotoOnlyLocked && mResponseType == ResponseType.PHOTO_ONLY;
    }

    /**
     * IME 서비스로부터 EditorInfo 를 전달받습니다
     */
    public void setEditorInfo(EditorInfo info) {
        mEditorInfo = info;
        // 지원할 MIME 타입을 에디터에 등록
        // AndroidX EditorInfoCompat 사용
        String[] mimeTypes = new String[]{"image/*"};
        EditorInfoCompat.setContentMimeTypes(info, mimeTypes);
    }

    private static class StripVisibilityGroup {
        private final View mSuggestionStripView;
        private final View mSuggestionsStrip;

        public StripVisibilityGroup(final View suggestionStripView, final ViewGroup suggestionsStrip) {
            mSuggestionStripView = suggestionStripView;
            mSuggestionsStrip = suggestionsStrip;
            showSuggestionsStrip();
        }

        public void setLayoutDirection(final boolean isRtlLanguage) {
            final int layoutDirection = isRtlLanguage ? ViewCompat.LAYOUT_DIRECTION_RTL : ViewCompat.LAYOUT_DIRECTION_LTR;
            ViewCompat.setLayoutDirection(mSuggestionStripView, layoutDirection);
            ViewCompat.setLayoutDirection(mSuggestionsStrip, layoutDirection);
        }

        public void showSuggestionsStrip() {
            mSuggestionsStrip.setVisibility(GONE);
        }
    }

    /**
     * Construct a {@link SuggestionStripView} for showing suggestions to be picked by the user.
     *
     * @param context
     * @param attrs
     */
    public SuggestionStripView(final Context context, final AttributeSet attrs) {
        this(context, attrs, R.attr.suggestionStripViewStyle);
    }

    public SuggestionStripView(final Context context, final AttributeSet attrs, final int defStyle) {
        super(context, attrs, defStyle);

        // 1) dp → px 변환을 미리 해두기
        mPhotoBarSizePx = dpToPx(88);
        int photoItemMargin = dpToPx(4);

        // 2) LayoutParams도 한 번만 생성
        mPhotoItemLp = new LinearLayout.LayoutParams(mPhotoBarSizePx, mPhotoBarSizePx);
        mPhotoItemLp.setMargins(photoItemMargin, 0, photoItemMargin, 0);

        // ─── ContextThemeWrapper 언래핑 ───
        Context base = context;
        while (base instanceof ContextWrapper && !(base instanceof LatinIME)) {
            base = ((ContextWrapper) base).getBaseContext();
        }
        if (base instanceof LatinIME) {
            mImeService = (LatinIME) base;
        } else {
            Log.w(TAG_NET, "SuggestionStripView: LatinIME 인스턴스 찾기 실패");
        }
        // ─────────────────────────────────────

        // AuthManager에 들어있는 userId를 사용.
        DEFAULT_USER_ID = AuthManager.getInstance(context).getUserId();

        final LayoutInflater inflater = LayoutInflater.from(context);
        inflater.inflate(R.layout.suggestions_strip, this);
        setBackgroundColor(ContextCompat.getColor(context, R.color.phokey_strip_bg));

        /* ▼ 여기쯤에 추가 --------------------------------------- */
        setClipChildren(false);     // 자식이 View 바깥으로 나가도 잘라내지 않음
        setClipToPadding(false);    // padding 범위까지 허용
        /* ------------------------------------------------------ */

        mSuggestionsStrip = findViewById(R.id.suggestions_strip);
        mSuggestionsStrip.setVisibility(View.GONE);
        mVoiceKey = findViewById(R.id.suggestions_strip_voice_key);
        mClipboardKey = findViewById(R.id.suggestions_strip_clipboard_key);
        mStripVisibilityGroup = new StripVisibilityGroup(this, mSuggestionsStrip);

        mTaskKey = findViewById(R.id.suggestions_strip_task_key);
        mTaskKey.setImageResource(DEFAULT_TASK_ICON);
        mTaskKey.setOnClickListener(this);
        mTaskKey.setVisibility(VISIBLE);

        LinearLayout wrapper = findViewById(R.id.suggestions_strip_wrapper);
        wrapper.setGravity(Gravity.CENTER_VERTICAL); // 자식들을 세로 중앙정렬

        LinearLayout.LayoutParams lpLabel =
                new LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT,
                        LinearLayout.LayoutParams.WRAP_CONTENT);
        lpLabel.gravity = Gravity.CENTER_VERTICAL;
        lpLabel.setMarginStart(0);   // 실제 레이아웃 간격

        mTaskLabel = new TextView(context);
        mTaskLabel.setVisibility(GONE);

        mTaskLabel.setLayoutParams(lpLabel);

        mTaskLabel.setTypeface(STRIP_TYPEFACE, Typeface.BOLD);
        mTaskLabel.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16);   // 글씨 조금 키움
        wrapper.addView(mTaskLabel);

        // blink 애니메이션 리소스 로드  ◀ 수정
        mKeyHighlighted = false;
        mAnswerShown = false;

        mDropIcon = ContextCompat.getDrawable(context, R.drawable.ic_paste_here);
        mDropIconSize = dpToPx(200); // 원하는 픽셀 크기

        for (int pos = 0; pos < SuggestedWords.MAX_SUGGESTIONS; pos++) {
            final TextView word = new TextView(context, null, R.attr.suggestionWordStyle);
            // ① 글꼴 적용
            word.setTypeface(STRIP_TYPEFACE);
            // ② 글꼴 크기 일괄 스케일
            word.setTextSize(TypedValue.COMPLEX_UNIT_PX, word.getTextSize() * STRIP_TEXT_SCALE);

            word.setContentDescription(getResources().getString(R.string.spoken_empty_suggestion));
            word.setOnClickListener(this);
            word.setOnLongClickListener(this);
            mWordViews.add(word);
            final View divider = inflater.inflate(R.layout.suggestion_divider, null);
            mDividerViews.add(divider);
            final TextView info = new TextView(context, null, R.attr.suggestionWordStyle);
            info.setTextColor(Color.WHITE);
            info.setTextSize(TypedValue.COMPLEX_UNIT_DIP, DEBUG_INFO_TEXT_SIZE_IN_DIP);
            mDebugInfoViews.add(info);
        }

        mLayoutHelper = new SuggestionStripLayoutHelper(context, attrs, defStyle, mWordViews, mDividerViews, mDebugInfoViews);

        mMoreSuggestionsContainer = inflater.inflate(R.layout.more_suggestions, null);
        mMoreSuggestionsView = mMoreSuggestionsContainer.findViewById(R.id.more_suggestions_view);
        mMoreSuggestionsBuilder = new MoreSuggestions.Builder(context, mMoreSuggestionsView);
        applyStripTypefaceRecursively(mMoreSuggestionsContainer);

        final Resources res = context.getResources();
        mMoreSuggestionsModalTolerance = res.getDimensionPixelOffset(R.dimen.config_more_suggestions_modal_tolerance);
        mMoreSuggestionsSlidingDetector = new GestureDetector(context, mMoreSuggestionsSlidingListener);

        final TypedArray keyboardAttr = context.obtainStyledAttributes(attrs, R.styleable.Keyboard, defStyle, R.style.SuggestionStripView);
        final Drawable iconVoice = keyboardAttr.getDrawable(R.styleable.Keyboard_iconShortcutKey);
        final Drawable iconIncognito = keyboardAttr.getDrawable(R.styleable.Keyboard_iconIncognitoKey);
        final Drawable iconClipboard = keyboardAttr.getDrawable(R.styleable.Keyboard_iconClipboardNormalKey);
        keyboardAttr.recycle();

        mVoiceKey.setImageDrawable(iconVoice);

        // 🔍, ❌ 아이콘 준비
        mIconClose = getResources().getDrawable(R.drawable.ic_close, null);

        mSearchKey = findViewById(R.id.suggestions_strip_search_key);
        if (mSearchKey == null) {
            throw new IllegalStateException("suggestions_strip_search_key not found in current layout variant");
        }
        mOriginalSearchKeyBg = mSearchKey.getBackground();

        mSearchKey.setOnClickListener(this);

        mVoiceKey.setOnClickListener(this);
        mClipboardKey.setImageDrawable(iconClipboard);
        mClipboardKey.setOnClickListener(this);
        mClipboardKey.setOnLongClickListener(this);

        ContextCompat.getColor(context, R.color.phokey_icon_tint);
        int tint = ContextCompat.getColor(context, R.color.phokey_icon_tint);
        mVoiceKey.setColorFilter(tint, PorterDuff.Mode.SRC_IN);
        mClipboardKey.setColorFilter(tint, PorterDuff.Mode.SRC_IN);

        mFetchClipboardKey = findViewById(R.id.suggestions_strip_fetch_clipboard);
        mFetchClipboardKey.setOnClickListener(this);

        mPhotoBar = findViewById(R.id.suggestions_strip_photo_bar);
        mPhotoBarContainer = findViewById(R.id.photo_bar_container);
        mSearchAnswer = findViewById(R.id.search_answer);

        mPhotoBar.setClipToPadding(false);
        mPhotoBar.setClipChildren(false);
        mPhotoBarContainer.setClipToPadding(false);
        mPhotoBarContainer.setClipChildren(false);

        post(() -> {
            if (mDefaultHeight == 0) {
                mDefaultHeight = getHeight();
            }
        });

        // 로딩 스피너 준비
        mLoadingSpinner = new ImageView(context);
        mLoadingSpinner.setVisibility(GONE);
        mLoadingSpinner.setScaleType(ImageView.ScaleType.CENTER_INSIDE);

        // 2) Glide로 GIF 로드
        Glide.with(context)
                .asGif()
                .load(R.drawable.galaxyai_loading_spinner)
                .diskCacheStrategy(DiskCacheStrategy.ALL)          // 메모리+디스크 캐시
                .transition(DrawableTransitionOptions.withCrossFade())
                .into(mLoadingSpinner);

        // 3) 레이아웃 파라미터 (CENTER_IN_PARENT)
        LayoutParams lpSpinner =
                new LayoutParams(
                        LayoutParams.WRAP_CONTENT,
                        LayoutParams.WRAP_CONTENT);
        lpSpinner.addRule(RelativeLayout.CENTER_IN_PARENT);

        // 4) 뷰 계층에 추가 (`this`는 RelativeLayout)
        this.addView(mLoadingSpinner, lpSpinner);

        // SuggestionStripView 생성자나 init() 내부
        this.setOnDragListener((v, event) -> {
            switch (event.getAction()) {
                case DragEvent.ACTION_DRAG_STARTED:
                    // 드래그 가능한 데이터인지 검사
                    if (event.getClipDescription().hasMimeType(ClipDescription.MIMETYPE_TEXT_URILIST)) {
                        // 1) IME Insets Freeze ON
                        if (mImeService != null) mImeService.setDragging(true);

                        hideDragTipLoop();

                        expandDragArea();

                        // 드래그 툴팁
//                        showDragTip();

                        return true;
                    }
                    return false;

                case DragEvent.ACTION_DRAG_LOCATION:
                    // y 좌표가 strip 최상단(=0)에서 mDragExtra 안쪽이면 hover 로 간주
                    float y = event.getY();
                    boolean nowHover = (y < mDragExtra);
                    if (nowHover != mDragHover) {
                        mDragHover = nowHover;   // 상태 갱신
                        invalidate();            // 색 다시 칠하게 draw() 호출
                    }
                    return true;

                case DragEvent.ACTION_DROP:
                    // 드롭 위치가 추가된 빈 공간 안인지 체크
                    float area = event.getY();
                    if (area < mDragExtra) {
                        // “추가된 빈 공간”으로 드롭
                        Uri uri = Uri.parse(event.getClipData().getItemAt(0).getText().toString());
                        InputConnection ic = mMainKeyboardView.getInputConnection();
                        boolean handled = false;
                        if (ic != null && mEditorInfo != null) {
                            ClipDescription desc = new ClipDescription("pasted image", new String[]{"image/*"});
                            InputContentInfoCompat content =
                                    new InputContentInfoCompat(uri, desc, null);
                            handled = InputConnectionCompat.commitContent(
                                    ic, mEditorInfo, content,
                                    InputConnectionCompat.INPUT_CONTENT_GRANT_READ_URI_PERMISSION,
                                    null);
                        }
                        if (!handled && ic != null) {
                            // fallback: clipboard → paste
                            ClipboardManager cm =
                                    (ClipboardManager) getContext().getSystemService(Context.CLIPBOARD_SERVICE);
                            cm.setPrimaryClip(ClipData.newUri(
                                    getContext().getContentResolver(), "Image", uri));
                            ic.performContextMenuAction(android.R.id.paste);
                        }

                        if (ic != null) {
                            // 컴포지션 확정
                            ic.finishComposingText();
                            // 최대한 많은 텍스트 요청
                            ExtractedTextRequest req = new ExtractedTextRequest();
                            req.hintMaxChars = Integer.MAX_VALUE;
                            req.hintMaxLines = Integer.MAX_VALUE;
                            ExtractedText et = ic.getExtractedText(req, 0);
                            if (et != null && et.text != null) {
                                int len = et.text.length();
                                ic.beginBatchEdit();
                                ic.setSelection(0, len);
                                ic.commitText("", 1);
                                ic.endBatchEdit();
                            }
                        }
                    } else {
                        // ── 기존 썸네일 영역: 아무 작업 없이 드래그만 정리
                    }
                    // 공통으로 드래그 모드 해제 & 원복
                    mDragHover = false;
                    if (mImeService != null) mImeService.setDragging(false);
                    collapseDragArea();
                    return true;

                case DragEvent.ACTION_DRAG_ENDED:
                    mDragHover = false;
                    // 1) IME Insets Freeze OFF
                    if (mImeService != null) mImeService.setDragging(false);

                    // 혹시 DROP 이외에 취소된 경우에도 알파 복원
                    View original = (View) event.getLocalState();
                    if (original != null) original.setAlpha(1f);

                    // 크기 원복
                    collapseDragArea();

                    hideDragTipLoop();
                    return true;

                default:
                    return true;
            }
        });

        // 반투명 오버레이용 Paint
        mOverlayPaint = new Paint();
        mOverlayPaintHover = new Paint();
        mOverlayPaint.setColor(Color.parseColor("#15000000"));
        mOverlayPaintHover.setColor(Color.parseColor("#40000000"));

        mFusedLocationClient = LocationServices.getFusedLocationProviderClient(context);
    }

    /* ▼ EventBus로 HangulCommitEvent 이벤트 구독 --------------------------------------------------- */
    @Subscribe(threadMode = ThreadMode.MAIN)
    public void onHangulCommitEvent(HangulCommitEvent event) {
        // 검색키가 X 상태라면 무시
        if (mSearchKey != null) {
            // 1) ❌ 아이콘 상태
            boolean isClose = isCloseIconVisible();
            // 2) 파랑 JSON(pause된 상태) — 애니메이션이 멈춰있고, 로드된 애니메이션 이름이 "ic_search_blue.json" 일 때
            boolean isPaused = mIsPausedBlue;
            if (isClose || isPaused) {
                return;
            }
        }
        Log.d("KeywordSearch", "받은 HangulCommitEvent: type=" + event.type + ", text=" + event.text);

        // 실제 동작 예시
        if (event.type == HangulCommitEvent.TYPE_SYLLABLE) {
            // 1. 입력창에서 최근 100자 이내 텍스트 가져오기
            // String input = getSearchInput().getText().toString();
            String input = event.text != null ? event.text : "";

            if (input.length() > 100) {
                input = input.substring(input.length() - 100);
            }

            // 2. 띄어쓰기(split)해서 마지막 단어 추출
            String[] tokens = input.split("\\s+"); // 여러 공백도 대응
            if (tokens.length == 0) return;        // 아무 단어도 없으면 중단

            String lastWord = tokens[tokens.length - 1];
            if (lastWord.isEmpty()) return;        // 마지막이 공백일 경우도 방지

            // 3. user_id를 준비 (실제 값에 맞게)
            String userId = DEFAULT_USER_ID; // AuthManager에서 받아오기

            // 4. exists API 호출 (Retrofit2 사용)
            KeywordApi api = ApiClient.getKeywordApi();
            Call<KeywordExistsResponse> call = api.exists(userId, lastWord);

            // 5. 비동기 호출 및 결과 처리
            call.enqueue(new Callback<KeywordExistsResponse>() {
                @Override
                public void onResponse(Call<KeywordExistsResponse> call, Response<KeywordExistsResponse> response) {
                    if (response.isSuccessful() && response.body() != null) {
                        boolean exists = response.body().exists;
                        Log.d("KeywordSearch", "[API] 단어 \"" + lastWord + "\" 존재여부: " + exists);

                        if (exists && mSearchKey != null) {
                            if (!mSearchKey.isAnimating() && !mKeyHighlighted) {
                                int[] gradientColors = new int[]{
                                        Color.parseColor("#DDA0FF"), // 연한 네온 바이올렛
                                        Color.parseColor("#A0DFFF"), // 연한 네온 스카이블루
                                        Color.parseColor("#A0FFD6")  // 연한 네온 민트
                                };

                                GradientDrawable glowBg = new GradientDrawable();
                                glowBg.setShape(GradientDrawable.OVAL);
                                // 그라데이션 타입을 RADIAL 로
                                glowBg.setGradientType(GradientDrawable.LINEAR_GRADIENT);
                                glowBg.setOrientation(GradientDrawable.Orientation.TL_BR);
                                glowBg.setColors(gradientColors);
                                // 부드러운 흐림 효과를 위해 외곽 스트로크를 반투명으로
                                glowBg.setStroke(dpToPx(2), Color.argb(0x40, 255, 255, 255));

                                // 2) 뷰 배경에 바로 적용
                                mSearchKey.setBackground(glowBg);

                                mSearchKey.setRepeatCount(LottieDrawable.INFINITE);
                                mSearchKey.setAnimation("ic_search.json");
                                mSearchKey.playAnimation();

                                mBorderPulseAnimator = ValueAnimator.ofInt(1, 200);
                                mBorderPulseAnimator.setDuration(500);
                                mBorderPulseAnimator.setRepeatMode(ValueAnimator.REVERSE);
                                mBorderPulseAnimator.setRepeatCount(ValueAnimator.INFINITE);
                                mBorderPulseAnimator.addUpdateListener(anim -> {
                                    int alpha = (int) anim.getAnimatedValue();
                                    // 전체 글로우 배경의 투명도 조절
                                    glowBg.setAlpha(alpha);
                                });
                                mBorderPulseAnimator.start();

                                mLastKeywordWithImages = lastWord;
                            }
                        }
                    } else {
                        Log.e("KeywordSearch", "API 응답 실패: " + response.code());
                    }
                }

                @Override
                public void onFailure(Call<KeywordExistsResponse> call, Throwable t) {
                    Log.e("KeywordSearch", "API 호출 에러: ", t);
                }
            });
            updateTaskButtonState();   // ← 항상 먼저 현재 상태 정리
            sendTaskMatch(lastWord);   // ← 아직 매칭 안 돼 있으면 활성화 시도
        } else if (event.type == HangulCommitEvent.TYPE_END) {
            // ① 키워드가 사라졌는지 먼저 확인
            updateTaskButtonState();

            if (mSearchKey != null && mSearchKey.isAnimating()) {
                mSearchKey.pauseAnimation();
                mSearchKey.setProgress(0f);

                if (mBorderPulseAnimator != null) {
                    mBorderPulseAnimator.cancel();
                    mBorderPulseAnimator = null;
                }

                mSearchKey.setBackground(mOriginalSearchKeyBg);
                mSearchKey.setLayerType(View.LAYER_TYPE_NONE, null);
            }

            if (isSearchInputEmpty()) resetTaskButton();

            mKeyHighlighted = false;
            mLastKeywordWithImages = null;
            mIsPausedBlue = false;
        }
    }

    private void sendTaskMatch(String word) {
        // 이미 매칭돼 있으면 더 이상 호출 X
        if (mTaskMatched || word.isEmpty()) return;

        ApiClient.getTaskMatchApi().match(word).enqueue(
                new Callback<TaskMatchResponse>() {
                    @Override
                    public void onResponse(Call<TaskMatchResponse> c,
                                           Response<TaskMatchResponse> r) {
                        if (!r.isSuccessful() || r.body() == null) {
                            return;
                        }
                        String task = r.body().matchedTask;
                        if (task == null || task.isEmpty()) {
                            return;
                        }
                        activateTaskButton(task, word);
                    }

                    @Override
                    public void onFailure(Call<TaskMatchResponse> c, Throwable t) {
                    }
                });
    }

    private void activateTaskButton(String task, String triggerWord) {
        int resId;
        switch (task) {
            case "maps":
                resId = R.drawable.ic_search;   // 임시
                showTaskActivatedMessage("maps 버튼 활성화(test)");
                break;
            case "opencv":
                resId = R.drawable.ic_send;     // 임시
                showTaskActivatedMessage("opencv 버튼 활성화(test)");
                break;
            case "airbnb":
                resId = R.drawable.ic_send;     // 임시
                showTaskActivatedMessage("airbnb 버튼 활성화(test)");
                break;
            case "web":
                resId = R.drawable.ic_send;     // 임시
                showTaskActivatedMessage("web 버튼 활성화(test)");
                break;
            case "gmail":
                resId = R.drawable.ic_send;     // 임시
                showTaskActivatedMessage("gmail 버튼 활성화(test)");
                break;
            case "calendar":
                resId = R.drawable.ic_send;     // 임시
                showTaskActivatedMessage("calendar 버튼 활성화(test)");
                break;
            default:
                return;           // 매칭 안 됨
        }
        mTaskKey.setImageResource(resId);
        mTaskMatched = true;
        mMatchedTask = task;
        mMatchedWord = triggerWord;

    }

    public void resetTaskButton() {
        hideTaskActivatedMessage(() -> {
            mTaskKey.setImageResource(DEFAULT_TASK_ICON);
            mTaskMatched = false;
            mMatchedTask = null;
        });
    }

    /**
     * 현재 활성 입력창의 전체 문자열(빈 문자열 가능)
     */
    private String getCurrentInputText() {
        if (mMainKeyboardView == null) return "";
        InputConnection ic = mMainKeyboardView.getInputConnection();
        if (ic == null) return "";
        ExtractedText et = ic.getExtractedText(new ExtractedTextRequest(), 0);
        return (et != null && et.text != null) ? et.text.toString() : "";
    }

    /**
     * 입력창에 활성 키워드가 ‘단어 경계’로 남아 있으면 true
     */
    private boolean isKeywordAlive(String text) {
        if (!mTaskMatched || mMatchedWord == null || mMatchedWord.isEmpty()) return false;

        int idx = text.lastIndexOf(mMatchedWord);
        if (idx == -1) return false;                       // 아예 사라짐

        int end = idx + mMatchedWord.length();
        // 키워드 앞·뒤가 공백·줄바꿈·문자열 끝이면 ‘단어 경계’라고 간주
        boolean beforeOK = idx == 0 || Character.isWhitespace(text.charAt(idx - 1));
        boolean afterOK = end == text.length() || Character.isWhitespace(text.charAt(end));

        return beforeOK && afterOK;
    }

    /**
     * 호출될 때마다 “키워드가 사라졌는지” 확인하고 필요하면 리셋
     */
    private void updateTaskButtonState() {
        if (mTaskMatched && !isKeywordAlive(getCurrentInputText())) {
            resetTaskButton();            // 아이콘·플래그 전부 원상복구
        }
    }

    // 등장 애니메이션
    private void showTaskActivatedMessage(String text) {
        if (mTaskLabel == null) return;

        mTaskLabel.setText(text);
        mTaskLabel.setAlpha(0f);
        mTaskLabel.setVisibility(VISIBLE);

        // ① 폭 측정
        mTaskLabel.measure(MeasureSpec.UNSPECIFIED, MeasureSpec.UNSPECIFIED);
        int labelW = mTaskLabel.getMeasuredWidth();

        // ② 시작 위치 : 라벨은 오른쪽 밖, 버튼은 제자리
        mTaskLabel.setTranslationX(labelW);
        mTaskKey.setTranslationX(labelW);

        // ③ 동시 애니메이션
        mTaskKey.animate()
                .translationX(0f)               // 왼쪽으로 밀림
                .setDuration(TASK_ANIM_DURATION)
                .setInterpolator(new FastOutSlowInInterpolator())
                .start();

        mTaskLabel.animate()
                .translationX(0f)                   // 제자리 도착
                .alpha(1f)
                .setDuration(TASK_ANIM_DURATION)
                .setInterpolator(new FastOutSlowInInterpolator())
                .start();
    }

    // 리셋 애니메이션
    private void hideTaskActivatedMessage(@Nullable Runnable endAction) {
        if (mTaskLabel == null || mTaskLabel.getVisibility() != VISIBLE) return;

        int labelW = mTaskLabel.getWidth();

        // 버튼도 함께 원위치
        mTaskKey.animate()
                .translationX(labelW)                 // ➜ 오른쪽으로
                .setDuration(TASK_ANIM_DURATION)
                .setInterpolator(new FastOutSlowInInterpolator())
                .start();

        mTaskLabel.animate()
                .translationX(labelW)
                .alpha(0f)
                .setDuration(TASK_ANIM_DURATION)
                .withEndAction(() -> {
                    mTaskLabel.setVisibility(GONE);
                    mTaskKey.setTranslationX(0f);     // 애니 완료 후 원복
                    if (endAction != null) endAction.run();
                })
                .setInterpolator(new FastOutSlowInInterpolator())
                .start();
    }


    // ========== Search Mode helpers ======================================
    private void enterSearchMode() {
        if (mInSearchMode) return;
        mInSearchMode = true;

        stopBreathing(mSearchKey);
        stopBreathing(mVoiceKey);
        stopBreathing(mClipboardKey);
        stopBreathing(mFetchClipboardKey);
        stopBreathing(mTaskKey);

        hideTaskActivatedMessage(() -> {
            mTaskKey.setImageResource(DEFAULT_TASK_ICON);
            mTaskMatched = false;
            mMatchedTask = null;
        });   // 라벨 & 버튼 애니메이션 원위치
        mTaskLabel.setVisibility(GONE);   // 안전망
        mTaskKey.setTranslationX(0f);

        // 1) 모든 키/버튼 숨기기
        mSearchKey.setVisibility(GONE);
        mVoiceKey.setVisibility(GONE);
        mClipboardKey.setVisibility(GONE);
        mFetchClipboardKey.setVisibility(GONE);
        mSuggestionsStrip.setVisibility(GONE);
        mTaskKey.setVisibility(GONE);

        // 3) 로딩 스피너 보이기
        mLoadingSpinner.setScaleX(0.8f);
        mLoadingSpinner.setScaleY(0.8f);
        mLoadingSpinner.setVisibility(VISIBLE);
        mLoadingSpinner.bringToFront();

        // 3) 실제 API 호출
        dispatchSearchQuery();
    }

    private void dispatchSearchQuery() {
        // 0) panel이 없으면 새로 만들고 리스너 바인드`
        if (mSearchPanel == null) {
            mSearchPanel = new SearchResultView(getContext());
            // SuggestionStripView의 mListener와 키보드 뷰를 넘겨 줍니다
            setListener(mListener, getRootView());
        }

        String query;
        // 내부 입력창이 아니라 외부 입력창에서 텍스트 가져오기
        InputConnection ic = mMainKeyboardView.getInputConnection();
        if (ic != null) {
            ExtractedText et = ic.getExtractedText(new ExtractedTextRequest(), 0);
            query = et != null && et.text != null ? et.text.toString().trim() : "";
        } else {
            query = "";
        }

        mLastQuery = query;  // ◀ 사용자가 입력한 원본 질문 보관
        Log.d("SugStrip", "dispatchSearchQuery: mLastQuery = \"" + mLastQuery + "\"");
        // ✅ 로그 출력 추가
        Log.d(TAG_NET, "🔍 전송된 query: " + query);

        // ─── 사용자 질문 저장 ───
        ChatSaveService.enqueue(
                getContext(),
                DEFAULT_USER_ID,
                "user",
                query,
                null
        );

        // 3) 로딩 스피너만 붙이기
        mSearchPanel.clearLoadingBubble();  // 혹시 이전 로딩이 남아 있으면 지우고
        mSearchPanel.bindLoading();

        Log.d(TAG_NET, "▶ REQUEST\n" + "user_id = " + DEFAULT_USER_ID + "\n" + "query   = " + query);

        // ① Retrofit 호출
        ApiClient.getChatApiService().search(DEFAULT_USER_ID, query).enqueue(new Callback<MessageResponse>() {
            @Override
            public void onResponse(Call<MessageResponse> call, Response<MessageResponse> res) {
                if (!res.isSuccessful()) {
                    Log.e(TAG_NET, "❌ " + res.code() + " " + res.message());
                    return;
                }
                MessageResponse body = res.body();
                if (body == null) return;

                // ─── 봇 응답 저장 ───
                List<String> photos = body.getPhotoIds();
                String itemsJson = null;
                if (photos != null) {
                    itemsJson = new Gson().toJson(photos);
                }
                ChatSaveService.enqueue(
                        getContext(),
                        DEFAULT_USER_ID,
                        "bot",
                        body.getAnswer(),
                        itemsJson
                );

                post(() -> {
                    // ① **스피너 숨기기**
                    mLoadingSpinner.setVisibility(View.GONE);
                    mSearchKey.setVisibility(VISIBLE);

                    if (body.getType().equals("info_search") || body.getType().equals("conversation"))
                        mResponseType = ResponseType.LONG_TEXT;
                    else mResponseType = ResponseType.PHOTO_ONLY;

                    mLastResponse = body;

                    View strip;
                    int startH;
                    int endH;

                    // 2) 분기별 행동
                    switch (mResponseType) {
                        case LONG_TEXT:
                            // ── 50자 이상: 버튼 강조 후 대기 ──
                            Log.d("행동", "LONG_TEXT = \"" + body.getAnswer() + "\"");
                            mSearchPanel.clearLoadingBubble();
                            mSearchKey.pauseAnimation();
                            mSearchKey.setRepeatCount(0);
                            mSearchKey.setAnimation("ic_search_blue.json"); // 파랑 정지된 JSON
                            mSearchKey.setProgress(0f);
                            mKeyHighlighted = true;
                            mIsPausedBlue = true;

                            if (mBorderPulseAnimator != null) {
                                mBorderPulseAnimator.cancel();
                                mBorderPulseAnimator = null;
                            }
                            // ② 원래 배경으로 복원
                            mSearchKey.setBackground(mOriginalSearchKeyBg);
                            // ③ (선택) 레이어 타입도 원래대로 돌려놓기
                            mSearchKey.setLayerType(View.LAYER_TYPE_NONE, null);

                            mVoiceKey.setVisibility(VISIBLE);
                            mFetchClipboardKey.setVisibility(VISIBLE);
                            mTaskKey.setVisibility(VISIBLE);

                            // ★ 키보드 웨이브 애니메이션 중지
                            stopKeyboardAnimation();
                            break;

                        case PHOTO_ONLY:
                            SuggestionStripView.this.setLayerType(View.LAYER_TYPE_HARDWARE, null);

                            Log.d("행동", "PHOTO_ONLY = \"" + body.getAnswer() + "\"");
                            Log.d(TAG_NET, "[PHOTO_ONLY] before dismiss: panelShowing=" + isShowingMoreSuggestionPanel() + ", stripVis=" + mSuggestionsStrip.getVisibility());

                            // 1) 남아 있는 추천 단어 팝업이 떠 있으면 닫기
                            if (isShowingMoreSuggestionPanel()) {
                                dismissMoreSuggestionsPanel();
                                Log.d(TAG_NET, "[PHOTO_ONLY] after dismiss: panelShowing=" + isShowingMoreSuggestionPanel());
                            }
                            // 기존 텍스트·제안 줄 숨기기
                            mSuggestionsStrip.setVisibility(GONE);
                            mSuggestionsStrip.setClickable(false);
                            mSuggestionsStrip.setEnabled(false);

                            mVoiceKey.setVisibility(GONE);
                            mClipboardKey.setVisibility(GONE);
                            mFetchClipboardKey.setVisibility(GONE);   // ← 사진 모드일 땐 숨김

                            mSearchAnswer.setVisibility(GONE);

                            mTaskKey.setVisibility(GONE);

                            // photo bar 초기화 및 채우기
                            mPhotoBarContainer.removeAllViews();
                            int barSize = dpToPx(96);
                            List<String> photoIds = body.getPhotoIds();
                            for (int i = 0; i < photoIds.size(); i++) {
                                String idStr = photoIds.get(i);
                                try {
                                    long id = Long.parseLong(idStr);
                                    Bitmap thumb = MediaStore.Images.Thumbnails.getThumbnail(getContext().getContentResolver(), id, MediaStore.Images.Thumbnails.MINI_KIND, null);
                                    // ① CardView 준비
                                    CardView card = new CardView(getContext());
                                    card.setLayoutParams(mPhotoItemLp);
                                    card.setRadius(dpToPx(8));            // 둥근 모서리
                                    card.setOutlineSpotShadowColor(Color.BLUE);
                                    card.setOutlineAmbientShadowColor(Color.BLUE);
                                    card.setCardElevation(dpToPx(6));     // 그림자 깊이
                                    card.setUseCompatPadding(true);       // Pre-Lollipop 보정
                                    card.setPreventCornerOverlap(false);  // 내부 이미지를 완전히 클립하지 않음

                                    // ② 실제 이미지뷰
                                    ImageView iv = new ImageView(getContext());
                                    iv.setLayoutParams(new ViewGroup.LayoutParams(
                                            ViewGroup.LayoutParams.MATCH_PARENT,
                                            ViewGroup.LayoutParams.MATCH_PARENT));
                                    iv.setScaleType(ImageView.ScaleType.CENTER_CROP);
                                    iv.setImageBitmap(thumb);

                                    // ③ CardView 안에 넣기
                                    card.addView(iv);

                                    // 클릭 시 클립보드 복사
                                    Uri uri = ContentUris.withAppendedId(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, id);
                                    iv.setOnClickListener(v -> {
                                        ClipboardManager cm = (ClipboardManager) getContext().getSystemService(Context.CLIPBOARD_SERVICE);
                                        cm.setPrimaryClip(ClipData.newUri(getContext().getContentResolver(), "Image", uri));
                                        InputConnection ic = mMainKeyboardView.getInputConnection();
                                        if (ic != null) {
                                            // 컴포지션 확정
                                            ic.finishComposingText();
                                            // 최대한 많은 텍스트 요청
                                            ExtractedTextRequest req = new ExtractedTextRequest();
                                            req.hintMaxChars = Integer.MAX_VALUE;
                                            req.hintMaxLines = Integer.MAX_VALUE;
                                            ExtractedText et = ic.getExtractedText(req, 0);
                                            if (et != null && et.text != null) {
                                                int len = et.text.length();
                                                ic.beginBatchEdit();
                                                ic.setSelection(0, len);
                                                ic.commitText("", 1);
                                                ic.endBatchEdit();
                                            }
                                        }
                                    });

                                    // 길게 터치 시
                                    iv.setOnLongClickListener(v -> {
                                        // 1) 드래그 데이터에 URI 문자열 담기
                                        ClipData.Item item = new ClipData.Item(uri.toString());
                                        String[] mimeTypes = {ClipDescription.MIMETYPE_TEXT_URILIST};
                                        ClipData dragData = new ClipData("image_uri", mimeTypes, item);

                                        // 2) 그림자: 원본 뷰를 50% 투명으로 그리기
                                        DragShadowBuilder shadow = new DragShadowBuilder(iv) {
                                            @Override
                                            public void onProvideShadowMetrics(Point shadowSize, Point shadowTouchPoint) {
                                                int w = iv.getWidth(), h = iv.getHeight();
                                                shadowSize.set(w, h);
                                                shadowTouchPoint.set(w / 2, h / 2);
                                                iv.setAlpha(0.5f);
                                            }

                                            @Override
                                            public void onDrawShadow(Canvas canvas) {
                                                iv.draw(canvas);
                                            }
                                        };

                                        // 3) 드래그 시작 (API 24 이상은 startDragAndDrop())
                                        iv.startDragAndDrop(dragData, shadow, iv, 0);
                                        return true;
                                    });

                                    // ① 추가: 뷰를 0배율에서 시작
                                    card.setScaleX(0f);
                                    card.setScaleY(0f);

                                    // ② 컨테이너에 뷰 추가
                                    mPhotoBarContainer.addView(card);

                                    // ③ 순차적 스케일 애니메이션 (0 → 1.1 → 1.0)
                                    card.animate()
                                            .scaleX(1f)
                                            .scaleY(1f)
                                            .setStartDelay(i * 100L)                // 각 아이템마다 100ms씩 딜레이
                                            .setDuration(300L)                      // 300ms 동안 실행
                                            .setInterpolator(new OvershootInterpolator()) // 오버슈트 바운스 효과
                                            .start();
                                } catch (NumberFormatException ignored) {
                                }
                            }
                            /* 1) 썸네일 바 높이 지정 */
                            ViewGroup.LayoutParams barLp = mPhotoBar.getLayoutParams();
                            barLp.height = barSize;
                            mPhotoBar.setLayoutParams(barLp);

                            strip = SuggestionStripView.this; // SuggestionStripView 자신
                            startH = strip.getHeight();
                            endH = barSize + dpToPx(6);
                            ValueAnimator heightAnimator = ValueAnimator.ofInt(startH, endH);
                            heightAnimator.addUpdateListener(anim -> {
                                strip.getLayoutParams().height = (int) anim.getAnimatedValue();
                                strip.requestLayout();
                            });
                            heightAnimator.setDuration(500);
                            heightAnimator.setInterpolator(new FastOutSlowInInterpolator());
                            heightAnimator.start();

                            /* 3) 부모 레이아웃 재측정/재배치 */
                            requestLayout();

                            mPhotoBar.setVisibility(VISIBLE);

                            // 스크롤 툴팁
                            showScrollTip();

                            // 드래그 툴팁 예약
                            scheduleDragTipLoop();

                            // PHOTO_ONLY 모드에서 카드 뷰에 연쇄 버운스 애니메이션 추가
                            post(() -> {
                                Handler handler = new Handler(Looper.getMainLooper());
                                int count = mPhotoBarContainer.getChildCount();
                                if (count == 0) return;

                                long upDuration = 300L;    // ↑ 300ms
                                long downDuration = 300L;    // ↓ 300ms
                                long interDelay = 10L;    // 카드 간 고정 지연(10ms)
                                // 한 사이클 전체 길이 계산: (카드 수 - 1) * interDelay + upDuration + downDuration
                                long waveSpan = (count - 1) * interDelay + upDuration + downDuration;
                                // 원래 주기(2초)보다 waveSpan이 길어질 수 있으므로,
                                // 충분한 휴지(2000ms)를 더해준다.
                                long cycleInterval = waveSpan + 1500L;
                                // ────────────────────

                                // 부드러운 감속/가속용 인터폴레이터
                                Interpolator upInterp = new DecelerateInterpolator();
                                Interpolator downInterp = new AccelerateInterpolator();

                                // 카드별 애니 Runnable 생성
                                Runnable[] anims = new Runnable[count];
                                for (int i = 0; i < count; i++) {
                                    final View card = mPhotoBarContainer.getChildAt(i);
                                    anims[i] = () -> {
                                        card.animate()
                                                .translationY(-dpToPx(4))
                                                .setDuration(upDuration)
                                                .setInterpolator(upInterp)
                                                .withEndAction(() -> card.animate()
                                                        .translationY(0)
                                                        .setDuration(downDuration)
                                                        .setInterpolator(downInterp)
                                                        .start()
                                                )
                                                .start();
                                    };
                                }

                                // 마스터 사이클 Runnable
                                Runnable cycle = new Runnable() {
                                    @Override
                                    public void run() {
                                        for (int i = 0; i < count; i++) {
                                            handler.postDelayed(anims[i], interDelay * i);
                                        }
                                        handler.postDelayed(this, cycleInterval);
                                    }
                                };

                                // 최초 실행
                                handler.postDelayed(cycle, 2000L);
                            });


                            // ⬇️ “❌” 아이콘으로 바뀔 때 글로우 애니메이션 정리
                            if (mBorderPulseAnimator != null) {
                                mBorderPulseAnimator.cancel();
                                mBorderPulseAnimator = null;
                            }
                            // 원래 배경으로 복원
                            mSearchKey.setBackground(mOriginalSearchKeyBg);
                            // 레이어 타입도 기본으로 되돌리기
                            mSearchKey.setLayerType(View.LAYER_TYPE_NONE, null);

                            // 검색 아이콘 → ❌ 로 변경
                            mSearchKey.clearAnimation();
                            mSearchKey.setRepeatCount(0);
                            mSearchKey.setImageDrawable(mIconClose);
                            mPhotoOnlyLocked = true;
                            mKeyHighlighted = true;  // X 버튼 상태이므로 glow 금지

                            mAnswerShown = true;
                            break;
                        default:
                            throw new IllegalStateException("Unexpected value: " + mResponseType);
                    }
                    Toast.makeText(getContext(), "검색 완료", Toast.LENGTH_SHORT).show();
                });
                Log.d(TAG_NET, "✅ 결과 수신");
            }

            @Override
            public void onFailure(Call<MessageResponse> call, Throwable t) {
                post(() -> {
                    stopKeyboardAnimation();
                    // ① **스피너 숨기기**
                    mLoadingSpinner.setVisibility(GONE);

                    // ② **높이 원복**
                    ViewGroup.LayoutParams lp = getLayoutParams();
                    lp.height = mDefaultHeight;
                    setLayoutParams(lp);

                    mSearchPanel.clearLoadingBubble();
                    // 에러 시에도 버튼 복원
                    mSearchKey.setVisibility(VISIBLE);
                    mSearchKey.clearAnimation();
                    mKeyHighlighted = false;
                    mInSearchMode = false;

                    mTaskKey.setVisibility(VISIBLE);

                    Toast.makeText(getContext(), "검색 요청에 실패했습니다", Toast.LENGTH_SHORT).show();
                });
                Log.e(TAG_NET, "❌ onFailure", t);
            }
        });
    }

    /**
     * @return 현재 검색키가 ❌ 아이콘(mIconClose) 상태인지
     */
    public boolean isCloseIconVisible() {
        // mSearchKey에 Drawable로 세팅된 게 mIconClose 인지 비교
        Drawable current = mSearchKey.getDrawable();
        return current != null && current.getConstantState() == mIconClose.getConstantState();
    }
// =====================================================================

    /**
     * A connection back to the input method.
     *
     * @param listener
     */
    public void setListener(final Listener listener, final View inputView) {
        mListener = listener;
        mMainKeyboardView = inputView.findViewById(R.id.keyboard_view);

        mMainKeyboardView.post(this::startScanWave);
    }

    /**
     * 검색키 애니메이션과 JSON 활성화 상태만 해제합니다.
     */
    public void clearSearchKeyHighlight() {
        // 사진-모드에서는 ❌ 유지
        if (isPhotoOnlyLocked()) return;

        // Lottie 애니메이션 멈춤
        if (mSearchKey.isAnimating()) {
            mSearchKey.pauseAnimation();
        }
        // JSON 리셋
        mSearchKey.clearAnimation();
        mSearchKey.setAnimation("ic_search.json");
        mSearchKey.playAnimation();
//        mSearchKey.setProgress(0f);
//        mSearchKey.setRepeatCount(0);
        // 배경 원복
        mSearchKey.setBackground(mOriginalSearchKeyBg);
        mSearchKey.setLayerType(View.LAYER_TYPE_NONE, null);
        // glow pulse 취소
        if (mBorderPulseAnimator != null) {
            mBorderPulseAnimator.cancel();
            mBorderPulseAnimator = null;
        }
        // 강조 플래그 해제
        mKeyHighlighted = false;

        mIsPausedBlue = false;
    }

    public void updateVisibility(final boolean shouldBeVisible, final boolean isFullscreenMode) {
        final int visibility = shouldBeVisible ? VISIBLE : (isFullscreenMode ? GONE : INVISIBLE);
        setVisibility(visibility);

        // ───── ① PHOTO_ONLY 모드에서는 보조 버튼 전부 숨김 ─────
        if (mResponseType == ResponseType.PHOTO_ONLY) {
            mVoiceKey.setVisibility(GONE);
            mClipboardKey.setVisibility(GONE);
            mFetchClipboardKey.setVisibility(GONE);
            // 검색 키(X)는 그대로 두고, strip도 이미 GONE 상태
            return;
        }

        final SettingsValues currentSettingsValues = Settings.getInstance().getCurrent();
        mVoiceKey.setVisibility(VISIBLE);
        mClipboardKey.setVisibility(GONE);
        mSearchKey.setVisibility(VISIBLE);   // 항상 노출

        mTaskKey.setVisibility(VISIBLE);

        for (View btn : new View[]{mSearchKey, mVoiceKey, mClipboardKey,
                mFetchClipboardKey, mTaskKey}) {

            // PHOTO_ONLY 모드에서는 검색키는 호흡 애니메이션도 건들지 않음
            if (btn == mSearchKey && isPhotoOnlyLocked()) continue;

            if (btn.getVisibility() == VISIBLE) {
                startBreathing(btn);
            } else {
                stopBreathing(btn);
            }
        }
    }

    public void setSuggestions(final SuggestedWords suggestedWords, final boolean isRtlLanguage) {
        clear();
        mStripVisibilityGroup.setLayoutDirection(isRtlLanguage);
        mSuggestedWords = suggestedWords;
        mStartIndexOfMoreSuggestions = mLayoutHelper.layoutAndReturnStartIndexOfMoreSuggestions(getContext(), mSuggestedWords, mSuggestionsStrip, this);
        mStripVisibilityGroup.showSuggestionsStrip();
    }

    public void setMoreSuggestionsHeight(final int remainingHeight) {
        mLayoutHelper.setMoreSuggestionsHeight(remainingHeight);
    }

    public void clear() {
        mSuggestionsStrip.removeAllViews();
        removeAllDebugInfoViews();
        mStripVisibilityGroup.showSuggestionsStrip();
        dismissMoreSuggestionsPanel();
    }

    private void removeAllDebugInfoViews() {
        // The debug info views may be placed as children views of this {@link SuggestionStripView}.
        for (final View debugInfoView : mDebugInfoViews) {
            final ViewParent parent = debugInfoView.getParent();
            if (parent instanceof ViewGroup) {
                ((ViewGroup) parent).removeView(debugInfoView);
            }
        }
    }

    private final MoreSuggestionsListener mMoreSuggestionsListener = new MoreSuggestionsListener() {
        @Override
        public void onSuggestionSelected(final SuggestedWordInfo wordInfo) {
            mListener.pickSuggestionManually(wordInfo);
            dismissMoreSuggestionsPanel();
        }

        @Override
        public void onCancelInput() {
            dismissMoreSuggestionsPanel();
        }
    };

    private final MoreKeysPanel.Controller mMoreSuggestionsController = new MoreKeysPanel.Controller() {
        @Override
        public void onDismissMoreKeysPanel() {
            mMainKeyboardView.onDismissMoreKeysPanel();
        }

        @Override
        public void onShowMoreKeysPanel(final MoreKeysPanel panel) {
            mMainKeyboardView.onShowMoreKeysPanel(panel);
        }

        @Override
        public void onCancelMoreKeysPanel() {
            dismissMoreSuggestionsPanel();
        }
    };

    public boolean isShowingMoreSuggestionPanel() {
        return mMoreSuggestionsView.isShowingInParent();
    }

    public void dismissMoreSuggestionsPanel() {
        mMoreSuggestionsView.dismissMoreKeysPanel();
    }

    @Override
    public boolean onLongClick(final View view) {
        if (view == mClipboardKey) {
            ClipboardManager clipboardManager = (ClipboardManager) getContext().getSystemService(Context.CLIPBOARD_SERVICE);
            ClipData clipData = clipboardManager.getPrimaryClip();
            if (clipData != null && clipData.getItemCount() > 0 && clipData.getItemAt(0) != null) {
                String clipString = clipData.getItemAt(0).coerceToText(getContext()).toString();
                if (clipString.length() == 1) {
                    mListener.onTextInput(clipString);
                } else if (clipString.length() > 1) {
                    //awkward workaround
                    mListener.onTextInput(clipString.substring(0, clipString.length() - 1));
                    mListener.onTextInput(clipString.substring(clipString.length() - 1));
                }
            }
            AudioAndHapticFeedbackManager.getInstance().performHapticAndAudioFeedback(Constants.NOT_A_CODE, view);
            return true;
        }
        AudioAndHapticFeedbackManager.getInstance().performHapticAndAudioFeedback(Constants.NOT_A_CODE, view);
        return showMoreSuggestions();
    }

    boolean showMoreSuggestions() {
        // PHOTO_ONLY 모드에서는 절대로 팝업 뜨지 않도록
        if (mResponseType == ResponseType.PHOTO_ONLY) {
            Log.d(TAG_NET, "showMoreSuggestions() blocked in PHOTO_ONLY");
            return false;
        }
        final Keyboard parentKeyboard = mMainKeyboardView.getKeyboard();
        if (parentKeyboard == null) {
            return false;
        }
        final SuggestionStripLayoutHelper layoutHelper = mLayoutHelper;
        if (mSuggestedWords.size() <= mStartIndexOfMoreSuggestions) {
            return false;
        }
        final int stripWidth = getWidth();
        final View container = mMoreSuggestionsContainer;
        final int maxWidth = stripWidth - container.getPaddingLeft() - container.getPaddingRight();
        final MoreSuggestions.Builder builder = mMoreSuggestionsBuilder;
        builder.layout(mSuggestedWords, mStartIndexOfMoreSuggestions, maxWidth, (int) (maxWidth * layoutHelper.mMinMoreSuggestionsWidth), layoutHelper.getMaxMoreSuggestionsRow(), parentKeyboard);
        mMoreSuggestionsView.setKeyboard(builder.build());
        container.measure(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);

        final MoreKeysPanel moreKeysPanel = mMoreSuggestionsView;
        final int pointX = stripWidth / 2;
        final int pointY = -layoutHelper.mMoreSuggestionsBottomGap;
        moreKeysPanel.showMoreKeysPanel(this, mMoreSuggestionsController, pointX, pointY, mMoreSuggestionsListener);
        mOriginX = mLastX;
        mOriginY = mLastY;
        for (int i = 0; i < mStartIndexOfMoreSuggestions; i++) {
            mWordViews.get(i).setPressed(false);
        }
        return true;
    }

    /**
     * PHOTO_ONLY 최초 진입 시 짧게 나타나는 스크롤 가능 툴팁
     */
    private void showScrollTip() {
        if (mScrollTipShown) return;
//        mScrollTipShown = true;     // 최초 한 번만 보여주기

        ImageView tip = new ImageView(getContext());
        tip.setImageResource(R.drawable.ic_scroll_tip);

        int sz = dpToPx(32);
        LayoutParams lp = new LayoutParams(sz, sz);
        lp.addRule(ALIGN_PARENT_END);
        lp.addRule(CENTER_VERTICAL);
        lp.setMarginEnd(dpToPx(12));
        addView(tip, lp);

        // ▶ PhotoBar 위에 떠 있도록
        tip.bringToFront();
        tip.setElevation(dpToPx(8));

        long appear = 250, bounce = 280, disappear = 250;

        // ① 페이드-인 + 위치 정렬
        tip.setAlpha(0f);
        tip.setTranslationY(dpToPx(10));
        tip.animate()
                .alpha(1f).translationY(0f)
                .setDuration(appear)
                .withEndAction(() -> {
                    // ② ObjectAnimator 로 4회 바운스
                    ObjectAnimator bounceAnim =
                            ObjectAnimator.ofFloat(tip, "translationX", 0f, dpToPx(6));
                    bounceAnim.setDuration(bounce);
                    bounceAnim.setInterpolator(new FastOutSlowInInterpolator());
                    bounceAnim.setRepeatMode(ValueAnimator.REVERSE);
                    bounceAnim.setRepeatCount(7);      // 왕복 → 4회 바운스
                    bounceAnim.addListener(new AnimatorListenerAdapter() {
                        @Override
                        public void onAnimationEnd(Animator animation) {
                            // ③ 페이드-아웃 후 제거
                            tip.animate()
                                    .alpha(0f)
                                    .setDuration(disappear)
                                    .withEndAction(() -> removeView(tip))
                                    .start();
                        }
                    });
                    bounceAnim.start();
                })
                .start();
    }

    private GradientDrawable createRippleDrawable() {
        GradientDrawable d = new GradientDrawable();
        d.setShape(GradientDrawable.OVAL);
        d.setColor(Color.WHITE);          // 흰색
        d.setAlpha((int) (0.8f * 255));   // 알파 0.8
        return d;
    }

    private void showDragTip() {
        if (mDragTipView != null || mDragTipShown) return;

//        mDragTipShown = true;

        int size = dpToPx(24);

        /* ■ 컨테이너(Box) 만들기 ------------------------------------------------ */
        FrameLayout box = new FrameLayout(getContext());
        RelativeLayout.LayoutParams lpBox =
                new RelativeLayout.LayoutParams(size * 3, size * 3);
        lpBox.addRule(CENTER_IN_PARENT);
        addView(box, lpBox);          // 부모(RelativeLayout)에 한번만 add
        box.setElevation(dpToPx(8));  // 전부 띄우기

        box.setClipChildren(false);         // 자식이 box 밖으로 나가도 자르지 말기
        setClipChildren(false);             // SuggestionStripView 도 동일

        /* ■ Ripple View -------------------------------------------------------- */
        View ripple = new View(getContext());
        ripple.setBackground(createRippleDrawable());
        ripple.setScaleX(0f);
        ripple.setScaleY(0f);
        ripple.setAlpha(0f);
        box.addView(ripple,
                new FrameLayout.LayoutParams(
                        size * 2,
                        size * 2,
                        Gravity.CENTER));

        /* ■ 화살표 ImageView --------------------------------------------------- */
        ImageView arrow = new ImageView(getContext());
        arrow.setImageResource(R.drawable.ic_arrow_up);
        box.addView(arrow,
                new FrameLayout.LayoutParams(
                        size,
                        size,
                        Gravity.CENTER));

        mDragTipView = box;           // << 컨테이너 전체를 보관

        /* ■ 애니메이션 --------------------------------------------------------- */
        long fade = 200, hold = 1000, move = 400;
        float travelY = -getHeight() / 2f + dpToPx(24);

        // ─ 화살표 순차 애니
        ObjectAnimator fadeIn = ObjectAnimator.ofFloat(arrow, View.ALPHA, 0f, 1f);
        fadeIn.setDuration(fade);

        ObjectAnimator stay = ObjectAnimator.ofFloat(arrow, View.ALPHA, 1f, 1f);
        stay.setDuration(hold);

        ObjectAnimator up = ObjectAnimator.ofFloat(arrow,
                View.TRANSLATION_Y, 0f, travelY);
        up.setDuration(move);
        up.setInterpolator(new FastOutSlowInInterpolator());
        up.addListener(new AnimatorListenerAdapter() {
            @Override
            public void onAnimationEnd(Animator a) {
                arrow.setTranslationY(0f);
            }
        });

        // ─ Ripple 애니 (hold 구간마다 발생)
        ObjectAnimator rX = ObjectAnimator.ofFloat(ripple, View.SCALE_X, 0f, 3f);
        ObjectAnimator rY = ObjectAnimator.ofFloat(ripple, View.SCALE_Y, 0f, 3f);
        ObjectAnimator rA = ObjectAnimator.ofFloat(ripple, View.ALPHA, 0.8f, 0f);

        AnimatorSet rippleSet = new AnimatorSet();
        rippleSet.playTogether(rX, rY, rA);
        rippleSet.setDuration(hold);
        rippleSet.setInterpolator(new LinearInterpolator());
        rippleSet.addListener(new AnimatorListenerAdapter() {
            @Override
            public void onAnimationEnd(Animator a) {
                // 다음 싸이클을 위해 원복
                ripple.setScaleX(0f);
                ripple.setScaleY(0f);
                ripple.setAlpha(0f);
            }
        });

        // ─ 메인 싸이클
        AnimatorSet cycle = new AnimatorSet();
        cycle.playSequentially(fadeIn, stay, up);

        stay.addListener(new AnimatorListenerAdapter() {
            @Override
            public void onAnimationStart(Animator a) {
                rippleSet.start();     // hold 시작과 동시에 파동
            }
        });

        cycle.addListener(new AnimatorListenerAdapter() {
            @Override
            public void onAnimationEnd(Animator a) {
                cycle.start();         // 무한 반복
            }
        });

        // 태그에 저장(나중 cancel 용)
        box.setTag(R.id.tag_drag_tip_anim, cycle);
        cycle.start();
    }

    // 클래스 맨 아래쪽에
    private void scheduleDragTipLoop() {
        hideDragTipLoop();
        mDragTipRunnable = new Runnable() {
            @Override
            public void run() {
                // 실제 드래깅 전이라면
                if (!mIsDragging && mDragTipView == null) {
                    showDragTip();
                    // 3초 후 다시
                    mTipHandler.postDelayed(this, 3000);
                }
            }
        };
        // 3초 뒤부터 시작
        mTipHandler.postDelayed(mDragTipRunnable, 3000);
    }

    // ③ 숨기기 유틸
    private void hideDragTipLoop() {
        // 예약된 콜백 제거
        if (mDragTipRunnable != null) {
            mTipHandler.removeCallbacks(mDragTipRunnable);
            mDragTipRunnable = null;
        }
        // 애니메이터 취소 & 뷰 제거
        if (mDragTipView != null) {
            Animator a = (Animator) mDragTipView.getTag(R.id.tag_drag_tip_anim);
            if (a != null) a.cancel();                 // 루프 중지
            mDragTipView.animate().cancel();           // 혹시 남은 페이드-인 취소
            removeView(mDragTipView);
            mDragTipView = null;
        }
        mDragTipShown = false;
    }

    // Working variables for {@link onInterceptTouchEvent(MotionEvent)} and
    // {@link onTouchEvent(MotionEvent)}.
    private int mLastX;
    private int mLastY;
    private int mOriginX;
    private int mOriginY;
    private final int mMoreSuggestionsModalTolerance;
    private boolean mNeedsToTransformTouchEventToHoverEvent;
    private boolean mIsDispatchingHoverEventToMoreSuggestions;
    private final GestureDetector mMoreSuggestionsSlidingDetector;

    // 키보드 애니메이션 관련 변수
    private Drawable mOriginalKeyboardBackground;
    private ValueAnimator mKeyboardWaveAnimator;
    private boolean mIsAnimatingKeyboard = false;

    private final GestureDetector.OnGestureListener mMoreSuggestionsSlidingListener = new GestureDetector.SimpleOnGestureListener() {
        @Override
        public boolean onScroll(MotionEvent down, MotionEvent me, float deltaX, float deltaY) {
            final float dy = me.getY() - down.getY();
            if (deltaY > 0 && dy < 0) {
                return showMoreSuggestions();
            }
            return false;
        }
    };

    @Override
    public boolean onInterceptTouchEvent(final MotionEvent me) {
        // Detecting sliding up finger to show {@link MoreSuggestionsView}.
        if (!mMoreSuggestionsView.isShowingInParent()) {
            mLastX = (int) me.getX();
            mLastY = (int) me.getY();
            return mMoreSuggestionsSlidingDetector.onTouchEvent(me);
        }
        if (mMoreSuggestionsView.isInModalMode()) {
            return false;
        }

        final int action = me.getAction();
        final int index = me.getActionIndex();
        final int x = (int) me.getX(index);
        final int y = (int) me.getY(index);
        if (Math.abs(x - mOriginX) >= mMoreSuggestionsModalTolerance || mOriginY - y >= mMoreSuggestionsModalTolerance) {
            // Decided to be in the sliding suggestion mode only when the touch point has been moved
            // upward. Further {@link MotionEvent}s will be delivered to
            // {@link #onTouchEvent(MotionEvent)}.
            mNeedsToTransformTouchEventToHoverEvent = AccessibilityUtils.Companion.getInstance().isTouchExplorationEnabled();
            mIsDispatchingHoverEventToMoreSuggestions = false;
            return true;
        }

        if (action == MotionEvent.ACTION_UP || action == MotionEvent.ACTION_POINTER_UP) {
            // Decided to be in the modal input mode.
            mMoreSuggestionsView.setModalMode();
        }
        return false;
    }

    @Override
    public boolean dispatchPopulateAccessibilityEvent(final AccessibilityEvent event) {
        // Don't populate accessibility event with suggested words and voice key.
        return true;
    }

    @Override
    public boolean onTouchEvent(final MotionEvent me) {
        if (!mMoreSuggestionsView.isShowingInParent()) {
            // Ignore any touch event while more suggestions panel hasn't been shown.
            // Detecting sliding up is done at {@link #onInterceptTouchEvent}.
            return true;
        }
        // In the sliding input mode. {@link MotionEvent} should be forwarded to
        // {@link MoreSuggestionsView}.
        final int index = me.getActionIndex();
        final int x = mMoreSuggestionsView.translateX((int) me.getX(index));
        final int y = mMoreSuggestionsView.translateY((int) me.getY(index));
        me.setLocation(x, y);
        if (!mNeedsToTransformTouchEventToHoverEvent) {
            mMoreSuggestionsView.onTouchEvent(me);
            return true;
        }
        // In sliding suggestion mode with accessibility mode on, a touch event should be
        // transformed to a hover event.
        final int width = mMoreSuggestionsView.getWidth();
        final int height = mMoreSuggestionsView.getHeight();
        final boolean onMoreSuggestions = (x >= 0 && x < width && y >= 0 && y < height);
        if (!onMoreSuggestions && !mIsDispatchingHoverEventToMoreSuggestions) {
            // Just drop this touch event because dispatching hover event isn't started yet and
            // the touch event isn't on {@link MoreSuggestionsView}.
            return true;
        }
        final int hoverAction;
        if (onMoreSuggestions && !mIsDispatchingHoverEventToMoreSuggestions) {
            // Transform this touch event to a hover enter event and start dispatching a hover
            // event to {@link MoreSuggestionsView}.
            mIsDispatchingHoverEventToMoreSuggestions = true;
            hoverAction = MotionEvent.ACTION_HOVER_ENTER;
        } else if (me.getActionMasked() == MotionEvent.ACTION_UP) {
            // Transform this touch event to a hover exit event and stop dispatching a hover event
            // after this.
            mIsDispatchingHoverEventToMoreSuggestions = false;
            mNeedsToTransformTouchEventToHoverEvent = false;
            hoverAction = MotionEvent.ACTION_HOVER_EXIT;
        } else {
            // Transform this touch event to a hover move event.
            hoverAction = MotionEvent.ACTION_HOVER_MOVE;
        }
        me.setAction(hoverAction);
        mMoreSuggestionsView.onHoverEvent(me);
        return true;
    }

    @Override
    public void onClick(final View view) {
        AudioAndHapticFeedbackManager.getInstance().performHapticAndAudioFeedback(Constants.CODE_UNSPECIFIED, this);
        if (view == mVoiceKey) {
            mListener.onCodeInput(Constants.CODE_SHORTCUT, Constants.SUGGESTION_STRIP_COORDINATE, Constants.SUGGESTION_STRIP_COORDINATE, false /* isKeyRepeat */);
            return;
        }

        if (view == mClipboardKey) {
            mListener.onCodeInput(Constants.CODE_CLIPBOARD, Constants.SUGGESTION_STRIP_COORDINATE, Constants.SUGGESTION_STRIP_COORDINATE, false /* isKeyRepeat */);
            return;
        }

        if (view == mFetchClipboardKey) {
            AuthManager am = AuthManager.getInstance(getContext());
            String userId = am.getUserId();
            // ① null 체크, ② "null" 문자열 비교를 뒤집어서 호출
            if (userId == null || "null".equals(userId)) {
                Toast.makeText(getContext(), "로그인이 필요한 기능 입니다.", Toast.LENGTH_SHORT).show();
            } else {
                // API 호출 부분
                ClipboardService clipboardService = ApiClient.getClipboardService();
                clipboardService.getLatestClipboard(userId).enqueue(new Callback<ClipBoardResponse>() {
                    @Override
                    public void onResponse(Call<ClipBoardResponse> call, Response<ClipBoardResponse> response) {
                        if (response.isSuccessful() && response.body() != null) {
                            ClipBoardResponse clipboardData = response.body();
                            String clipboardText = clipboardData.getValue();

                            if (clipboardText != null && !clipboardText.isEmpty()) {
                                // 1. 텍스트 입력 (기존 기능 유지)
                                mListener.onTextInput(clipboardText);

                                // 2. 클립보드에 복사
                                ClipboardManager clipboardManager = (ClipboardManager) getContext().getSystemService(Context.CLIPBOARD_SERVICE);
                                ClipData clipData = ClipData.newPlainText("clipboard text", clipboardText);
                                clipboardManager.setPrimaryClip(clipData);

                                // 3. 토스트 메시지 표시
                                Toast.makeText(getContext(), "클립보드 내용 \"" + clipboardText + "\"이 입력되었습니다", Toast.LENGTH_SHORT).show();
                            } else {
                                Toast.makeText(getContext(), "클립보드가 비어있습니다", Toast.LENGTH_SHORT).show();
                            }
                        } else {
                            Toast.makeText(getContext(), "클립보드 데이터를 가져오는데 실패했습니다", Toast.LENGTH_SHORT).show();
                        }
                    }

                    @Override
                    public void onFailure(Call<ClipBoardResponse> call, Throwable t) {
                        Toast.makeText(getContext(), "네트워크 오류: " + t.getMessage(), Toast.LENGTH_SHORT).show();
                    }
                });
            }
            return;
        }

        if (view == mSearchKey) {
            // ❌ 클릭 시 닫기 애니메이션 (사진 역순 스케일 → strip 닫기)
            if (mResponseType == ResponseType.SHORT_TEXT || mResponseType == ResponseType.PHOTO_ONLY) {
                final View strip = SuggestionStripView.this;

                stopKeyboardAnimation();

                // — PHOTO_ONLY 모드면 사진을 역순으로 축소 —
                if (mResponseType == ResponseType.PHOTO_ONLY) {
                    int count = mPhotoBarContainer.getChildCount();
                    for (int i = count - 1; i >= 0; i--) {
                        View iv = mPhotoBarContainer.getChildAt(i);
                        iv.animate()
                                .scaleX(0f).scaleY(0f)
                                .setStartDelay(count - 1 - i)
                                .setDuration(300)
                                .setInterpolator(new FastOutSlowInInterpolator())
                                .start();
                    }
                }

                // — 사진 애니메이션 끝난 뒤에 strip 닫기 —
                long delay = (mResponseType == ResponseType.PHOTO_ONLY
                        ? mPhotoBarContainer.getChildCount() + 300
                        : 0);
                strip.postDelayed(() -> {
                    // 1) 높이 축소
                    if (mDefaultHeight > 0) {
                        int startH = strip.getHeight();
                        int endH = mDefaultHeight;
                        ValueAnimator collapse = ValueAnimator.ofInt(startH, endH);
                        collapse.setDuration(300);
                        collapse.setInterpolator(new FastOutSlowInInterpolator());
                        collapse.addUpdateListener(anim -> {
                            strip.getLayoutParams().height = (int) anim.getAnimatedValue();
                            strip.requestLayout();
                        });
                        collapse.start();
                    }

                    // 2) 페이드아웃
                    strip.animate()
                            .alpha(1f)
                            .setDuration(200)
                            .withEndAction(() -> {
                                //— 완전히 닫힌 뒤 원상복구 —
                                strip.getLayoutParams().height = mDefaultHeight;
                                strip.requestLayout();

                                mSearchAnswer.setVisibility(GONE);
                                mPhotoBar.setVisibility(GONE);
                                mSuggestionsStrip.setVisibility(GONE);
                                mVoiceKey.setVisibility(VISIBLE);
                                mClipboardKey.setVisibility(GONE);
                                mFetchClipboardKey.setVisibility(VISIBLE);
                                mTaskKey.setVisibility(VISIBLE);

                                startBreathing(mSearchKey);
                                startBreathing(mVoiceKey);
                                startBreathing(mFetchClipboardKey);
                                startBreathing(mTaskKey);

                                mSearchKey.clearAnimation();
                                mSearchKey.setAnimation("ic_search_backup.json");
                                mSearchKey.setProgress(0f);
                                mSearchKey.setRepeatCount(0);

                                mInSearchMode = false;
                                mAnswerShown = false;
                                mResponseType = null;
                                mLastResponse = null;
                                mIsPausedBlue = false;

                                hideTaskActivatedMessage(null);     // 라벨·버튼 위치 복귀
                                mTaskKey.setTranslationX(0f);
                            });
                    mKeyHighlighted = false;
                    mPhotoOnlyLocked = false;

                    hideDragTipLoop();
                }, delay);

                SuggestionStripView.this.setLayerType(View.LAYER_TYPE_NONE, null);
                return;
            }

            // 1) 검색 모드가 아니면 진입
            if (!mInSearchMode) {
                if (isSearchInputEmpty()) {
                    showEmptyToast();
                    return;
                }

                // 클릭 시 단발성 키보드 애니메이션 효과
                showKeyboardClickAnimation();

                enterSearchMode();
                return;
            }
            // 2) 아직 응답 안 왔으면 무시(깜빡임 계속)
            if (!mKeyHighlighted) {
                return;
            }
            // 3) LONG_TEXT 응답이 왔을 때, 첫 클릭은 말풍선 표시 + X 버튼으로 변환
            // 이제: 두 번째 클릭 때만 패널 띄우고 카드 UI
            if (!mAnswerShown) {
                showSearchPanel();
                mSearchPanel.bindLongTextCard(mLastQuery, mLastResponse);
                mSearchKey.setImageDrawable(mIconClose);
                mAnswerShown = true;
            } else {
                // 세 번째 클릭(❌): 패널 닫고 키보드 복귀
                mSearchPanel.dismissMoreKeysPanel();

                mSearchKey.setAnimation("ic_search_backup.json");  // 흑 정지된 JSON
                mSearchKey.playAnimation();
//                mSearchKey.setRepeatCount(0);
//                mSearchKey.setProgress(0f);

                mKeyHighlighted = false;
                mAnswerShown = false;
                mInSearchMode = false;
                mIsPausedBlue = false;
            }
            return;
        }

        if (view == mTaskKey) {
            if (!mTaskMatched || mMatchedTask == null) {
                Toast.makeText(getContext(),
                        "활성화된 기능이 없습니다.",
                        Toast.LENGTH_SHORT).show();
                return;
            }
            switch (mMatchedTask) {
                case "maps":
                    // 1) 만약 아직 서버 응답(mGeoAssistReady)이 안 왔다면 → “첫 번째 클릭” 플로우
                    if (!mGeoAssistReady) {
                        // (1) UI: 로딩 스피너 보여주기, 나머지 버튼 숨기기
                        mLoadingSpinner.setVisibility(VISIBLE);
                        mLoadingSpinner.bringToFront();

                        mVoiceKey.setVisibility(GONE);
                        mSearchKey.setVisibility(GONE);
                        mTaskKey.setVisibility(GONE);
                        mTaskLabel.setVisibility(GONE);
                        mFetchClipboardKey.setVisibility(GONE);

                        // (2) 위치 가져오기 (권한은 이미 SetupWizard에서 받았다고 가정)
                        //     위치 획득이 실패할 수도 있으니 예외 처리
                        if (ContextCompat.checkSelfPermission(getContext(),
                                Manifest.permission.ACCESS_FINE_LOCATION)
                                != PackageManager.PERMISSION_GRANTED) {
                            Toast.makeText(getContext(), "위치 권한이 필요합니다.", Toast.LENGTH_SHORT).show();
                            return;
                        }
                        mFusedLocationClient
                                .getCurrentLocation(Priority.PRIORITY_HIGH_ACCURACY, null)
                                .addOnSuccessListener(loc -> {
                                    if (loc == null) {
                                        // 위치 못 가져왔을 때
                                        Toast.makeText(getContext(),
                                                "위치 정보를 가져오지 못했습니다.",
                                                Toast.LENGTH_SHORT).show();
                                        // UI 복원
                                        mLoadingSpinner.setVisibility(GONE);
                                        restoreButtonsAfterLoading();
                                        return;
                                    }

                                    // (3) 현재 입력창 텍스트 가져오기
                                    String q = getCurrentInputText();

                                    // (4) 요청 바디 구성
                                    GeoAssistReq body = new GeoAssistReq();
                                    body.query = q;
                                    body.location.latitude  = loc.getLatitude();
                                    body.location.longitude = loc.getLongitude();

                                    // ▶ 요청 직전 JSON 형태를 로그로 출력
                                    String jsonBody = new Gson().toJson(body);
                                    Log.d("GEO API 호출", "요청 JSON: " + jsonBody);

                                    // (5) Retrofit으로 서버 호출
                                    ApiClient.getGeoAssistApi().geoAssist(body)
                                            .enqueue(new Callback<ResponseBody>() {
                                                @Override
                                                public void onResponse(Call<ResponseBody> call,
                                                                       Response<ResponseBody> response) {
                                                    // (6) 서버 응답이 왔을 때
                                                    mLoadingSpinner.setVisibility(GONE);      // 로딩 스피너 숨김
                                                    if (!response.isSuccessful()) {
                                                        // (1) 상태 코드 찍어보기
                                                        Log.e("GEO API 호출", "서버 오류 코드: " + response.code());

                                                        // (2) errorBody에 실제 서버가 내려준 텍스트(에러 메시지 등)가 있으면 찍어보기
                                                        if (response.errorBody() != null) {
                                                            try {
                                                                String errorText = response.errorBody().string();
                                                                Log.e("GEO API 호출", "서버 에러 상세 내용: " + errorText);
                                                            } catch (IOException e) {
                                                                Log.e("GEO API 호출", "errorBody 읽기 중 IOException", e);
                                                            }
                                                        }
                                                        return;
                                                    }
                                                    try {
                                                        String html = response.body().string();
                                                        Log.i("GEO API 호출", "받은 HTML 전체:\n" + html);
                                                        // → 이후 html 변수를 mGeoAssistHtml에 저장해 두고,
                                                        //    두 번째 버튼 터치 시 showWebViewDialog(html) 호출
                                                        mGeoAssistHtml = html;
                                                        mGeoAssistReady = true;
                                                        // Task 버튼 아이콘을 “확인” 모드로 바꾸기
                                                        mTaskKey.setImageResource(R.drawable.ic_arrow_up);
                                                        Toast.makeText(getContext(), "지도 결과가 준비되었습니다", Toast.LENGTH_SHORT).show();
                                                    } catch (IOException e) {
                                                        Log.e("GEO API 호출", "response.body().string() 읽기 실패", e);
                                                        Toast.makeText(getContext(),
                                                                "응답 처리 중 오류", Toast.LENGTH_SHORT).show();
                                                        restoreButtonsAfterLoading();
                                                        return;
                                                    }

                                                    // (7) 이제 “확인 상태”로 변경: 다음 클릭 시 WebView를 띄울 수 있도록 준비
                                                    mGeoAssistReady = true;

                                                    // 예를 들면 “확인” 아이콘으로 교체하거나, 버튼 배경을 바꿔줍니다.
                                                    mTaskKey.setImageResource(R.drawable.ic_arrow_up);      // 임시
                                                    // (ic_confirm 은 “확인” 아이콘으로 대체하세요)

                                                    // 맵 버튼을 다시 눌렀을 때 WebView를 띄울 수 있도록,
                                                    // 나머지 버튼들만 원래처럼 보이게 해 줍니다.
                                                    restoreButtonsAfterLoading();
                                                }

                                                @Override
                                                public void onFailure(Call<ResponseBody> call, Throwable t) {
                                                    mLoadingSpinner.setVisibility(GONE);
                                                    Toast.makeText(getContext(),
                                                            "네트워크 오류: " + t.getMessage(),
                                                            Toast.LENGTH_SHORT).show();
                                                    restoreButtonsAfterLoading();
                                                }
                                            });
                                })
                                .addOnFailureListener(e -> {
                                    // 위치 획득 자체가 실패했을 때
                                    Toast.makeText(getContext(),
                                            "위치 정보를 가져오는 중 오류",
                                            Toast.LENGTH_SHORT).show();
                                    mLoadingSpinner.setVisibility(GONE);
                                    restoreButtonsAfterLoading();
                                });
                        return;
                    }

                    // 2) 이미 mGeoAssistReady == true (서버 응답 완료)된 상태라면 → “두 번째 클릭” 플로우
                    showWebViewDialog(mGeoAssistHtml);

                    // (3) WebView를 띄운 뒤, 필요하다면 Task 버튼과 상태를 초기화
                    resetTaskAfterConfirm();
                    return;
                case "opencv":
                    /* opencv 작업 실행 */
                    break;
                case "gmail":
                    /* gmail 작업 실행 */
                    break;
                case "calendar":
                    /* calendar 작업 실행 */
                    break;
                case "airbnb":
                    /* airbnb 작업 실행 */
                    break;
                case "web":
                    /* web 작업 실행 */
                    break;
            }
            resetTaskButton();   // 실행 후 항상 리셋
            return;
        }

        final Object tag = view.getTag();
        // {@link Integer} tag is set at
        // {@link SuggestionStripLayoutHelper#setupWordViewsTextAndColor(SuggestedWords,int)} and
        // {@link SuggestionStripLayoutHelper#layoutPunctuationSuggestions(SuggestedWords,ViewGroup}
        if (tag instanceof Integer) {
            final int index = (Integer) tag;
            if (index >= mSuggestedWords.size()) {
                return;
            }
            final SuggestedWordInfo wordInfo = mSuggestedWords.getInfo(index);
            mListener.pickSuggestionManually(wordInfo);
        }
    }

    private void restoreButtonsAfterLoading() {
        // ① 음성, 클립보드, FetchClipboardKey 등 원래 보이던 버튼만 다시 보이게
        mVoiceKey.setVisibility(VISIBLE);
        mFetchClipboardKey.setVisibility(VISIBLE);

        // ② TaskKey(지도 버튼)를 다시 보여주기
        mTaskKey.setVisibility(VISIBLE);

        // ③ 검색 버튼도 다시 보여주기 (첫 클릭 때 GONE 처리했으므로 복원해 줘야 함)
        mSearchKey.setVisibility(VISIBLE);

        // ④ TaskKey 아이콘 리셋: 아직 mGeoAssistReady가 false라면 기본 아이콘(+)으로 돌려둠
        if (!mGeoAssistReady) {
            mTaskKey.setImageResource(DEFAULT_TASK_ICON);
        }
    }

    private void resetTaskAfterConfirm() {
        mGeoAssistReady = false;
        mGeoAssistHtml = null;
        mMatchedTask = null;
        mTaskMatched = false;

        // Task 버튼을 원래 아이콘(+)으로 복귀
        mTaskKey.setImageResource(DEFAULT_TASK_ICON);
    }

    private Dialog mWebDialog;        // (필요하면 필드로 꺼내놓고)
    private WebView mDialogWebView;   // (필요하면 WebView도 꺼내서 변수로 둡니다)
    /**
     * IME 영역(키보드 높이)만큼 WebView를 띄우는 예시.
     * BadTokenException(2012) 에러를 없애기 위해,
     * TYPE_INPUT_METHOD_DIALOG 대신 TYPE_APPLICATION_ATTACHED_DIALOG를 사용합니다.
     */
    private void showWebViewDialog(String htmlContent) {
        // 1) Dialog를 만들 때 Fullscreen 테마 대신 “일반 다이얼로그” 테마를 씁니다.
        Dialog dialog = new Dialog(getContext(),
                android.R.style.Theme_DeviceDefault_Light_NoActionBar);
        // → 풀스크린 테마가 아니므로, 기본적으로 화면 전체를 덮지는 않습니다.

        // 2) WindowManager.LayoutParams를 가져와서 IME용이 아닌 “애플리케이션 어태치드” 타입으로 설정
        Window window = dialog.getWindow();
        if (window == null) {
            // getWindow()가 null이면 안전하게 리턴
            return;
        }
        WindowManager.LayoutParams lp = window.getAttributes();
        // 아래와 같이 IME에서도 허용되는 타입을 사용해야 합니다.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            lp.type = WindowManager.LayoutParams.TYPE_APPLICATION_ATTACHED_DIALOG;
        } else {
            // 구버전 API용: IME가 올라갈 때 허용되는 패널 타입.
            lp.type = WindowManager.LayoutParams.TYPE_APPLICATION_ATTACHED_DIALOG;
        }

        // 4) IME 창 위에 뜨더라도 키보드 자체 포커스를 방해하지 않도록 플래그 지정
        lp.flags |= WindowManager.LayoutParams.FLAG_ALT_FOCUSABLE_IM;

        // 3) IME 내부(키보드 View)의 토큰을 강제로 붙여 줍니다.
        //    이게 있어야 “이 다이얼로그는 이 IME 창(키보드) 안에만 붙어 있다”고 시스템이 인식합니다.
        if (mMainKeyboardView != null && mMainKeyboardView.getWindowToken() != null) {
            lp.token = mMainKeyboardView.getWindowToken();
        }

        // 5) 속성을 다시 설정
        window.setAttributes(lp);

        // 3) FrameLayout(root) 생성: WebView+버튼을 담을 컨테이너
        FrameLayout container = new FrameLayout(getContext());
        container.setLayoutParams(
                new FrameLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT
                )
        );

        // 6) WebView 생성 및 설정
        WebView webView = new WebView(getContext());
        webView.getSettings().setJavaScriptEnabled(true);
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String scheme = uri.getScheme();
                String uriStr = uri.toString();

                // 1) "intent://" 형태로 넘어온 URL (예: <a href="intent://...">) 을 처리
                if (uriStr.startsWith("intent://")) {
                    try {
                        // Intent URI 스킴에서 Intent 객체를 파싱
                        Intent intent = Intent.parseUri(uriStr, Intent.URI_INTENT_SCHEME);

                        // FLAG_ACTIVITY_NEW_TASK 는 IME(=Activity Context가 아닌 ContextWrapper) 환경에서 꼭 필요
                        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);

                        // 해당 앱(패키지)이 설치되어 있는지 확인
                        PackageManager pm = view.getContext().getPackageManager();
                        if (intent.resolveActivity(pm) != null) {
                            view.getContext().startActivity(intent);
                        } else {
                            // 설치되어 있지 않은 경우, fallback URL(웹 브라우저)로 연결하거나 Play Store로 보낼 수 있음
                            String fallbackUrl = intent.getStringExtra("browser_fallback_url");
                            if (fallbackUrl != null) {
                                Intent fallbackIntent = new Intent(Intent.ACTION_VIEW, Uri.parse(fallbackUrl));
                                fallbackIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                                view.getContext().startActivity(fallbackIntent);
                            }
                        }
                    } catch (URISyntaxException e) {
                        // 파싱 실패 시 WebView 내부 로드로 넘길 수도 있고, 그냥 무시해도 됩니다.
                        e.printStackTrace();
                    }
                    return true;
                }

                // 2) "myapp://" 처럼 앱 전용 커스텀 스킴(예: kakaomap://, youtube:// 등)이 내려왔을 때 처리
                //    URI 스킴이 등록된 앱이 있으면 바로 startActivity, 없으면 WebView 로드
                if ("myapp".equalsIgnoreCase(scheme) || "kakaomap".equalsIgnoreCase(scheme)) {
                    Intent customIntent = new Intent(Intent.ACTION_VIEW, uri);
                    customIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);

                    PackageManager pm = view.getContext().getPackageManager();
                    if (customIntent.resolveActivity(pm) != null) {
                        view.getContext().startActivity(customIntent);
                        return true;
                    }
                    // 설치된 앱이 없으면 WebView에서 처리하거나, 마켓으로 유도하는 로직을 넣어도 됩니다.
                    return false;
                }

                // 3) 그 외—일반적인 http/https 링크(예: 네이버 지도, 혹은 우리가 처리하지 않을 링크)는 WebView 내에서 로드되게
                return false;
            }
        });
        webView.loadDataWithBaseURL(
                null,
                htmlContent,
                "text/html",
                "UTF-8",
                null
        );

        // 5) “뒤로가기 버튼” 생성 (ImageButton 예시)
        ImageButton backBtn = new ImageButton(getContext());
        backBtn.setImageResource(android.R.drawable.ic_media_previous); // 원하는 아이콘으로 교체
        backBtn.setBackgroundColor(Color.TRANSPARENT);                // 투명 배경
        // 클릭 시 WebView 뒤로가기 혹은 다이얼로그 닫기
        backBtn.setOnClickListener(v -> {
            if (webView.canGoBack()) {
                webView.goBack();
            } else {
                dialog.dismiss();
            }
        });

        // 6) 버튼 위치 조정 (예: 상단 좌측, margin 16dp)
        int marginDp = 16;
        int marginPx = Math.round(marginDp * getResources().getDisplayMetrics().density);
        FrameLayout.LayoutParams btnLp = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        );
        btnLp.gravity = Gravity.START | Gravity.TOP;
        btnLp.setMargins(marginPx, marginPx, marginPx, marginPx);
        backBtn.setLayoutParams(btnLp);

        // 7) 컨테이너에 WebView와 버튼을 추가
        container.addView(webView);
        container.addView(backBtn);

        // 7) Dialog에 WebView 붙이고 우선 show() 호출
        dialog.setContentView(container);
        dialog.show();

        // 8) “키보드 높이”만큼 다이얼로그가 올라오도록 사이즈를 조정
        //    (mMainKeyboardView.getHeight()를 사용하면, IME가 차지하던 높이와 똑같이 맞출 수 있습니다)
        //
        //    단, 이 값을 곧바로 가져오면 아직 0일 수 있으므로 post()로 한 프레임 뒤에 가져오거나,
        //    dialog.show() 직후에 mMainKeyboardView.getHeight()가 제대로 잡히는지 확인해야 합니다.
        int keyboardHeight = mMainKeyboardView.getHeight() + 230;
        if (keyboardHeight > 0) {
            window.setLayout(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    keyboardHeight
            );
        } else {
            // 레이아웃이 끝난 뒤에 높이가 잡히면 다시 한 번 세팅
            mMainKeyboardView.post(() -> {
                int h = mMainKeyboardView.getHeight();
                if (h > 0) {
                    window.setLayout(
                            ViewGroup.LayoutParams.MATCH_PARENT,
                            h
                    );
                }
            });
        }
        mDialogWebView = webView;
        // 10) 백 키를 다이얼로그가 우선 처리하도록 OnKeyListener를 등록
        dialog.setOnKeyListener(new DialogInterface.OnKeyListener() {
            @Override
            public boolean onKey(DialogInterface dlg, int keyCode, KeyEvent event) {
                if (keyCode == KeyEvent.KEYCODE_BACK && event.getAction() == KeyEvent.ACTION_UP) {
                    // 1) WebView에 뒤로 갈 수 있는 기록이 있으면 WebView.goBack()만
                    if (mDialogWebView != null && mDialogWebView.canGoBack()) {
                        mDialogWebView.goBack();
                        return true; // 여기를 true로 리턴하면 시스템이 이 백 키를 더 이상 숨기기(키보드 내리기) 용도로 사용하지 않습니다.
                    }
                    // 2) 기록이 없으면 다이얼로그 닫기
                    dlg.dismiss();
                    return true;
                }
                return false; // 그 외 키 이벤트는 기본 동작
            }
        });
    }

    private boolean isSearchInputEmpty() {
        InputConnection ic = mMainKeyboardView.getInputConnection();
        ExtractedText et = ic == null ? null : ic.getExtractedText(new ExtractedTextRequest(), 0);
        String q = (et != null && et.text != null) ? et.text.toString().trim() : "";
        return q.isEmpty();
    }

    private void showEmptyToast() {
        Toast.makeText(getContext(),
                        "활성화된 앱 입력창에 질문을 입력해주세요.",
                        Toast.LENGTH_SHORT)
                .show();
    }

    @Override
    protected void onAttachedToWindow() {
        super.onAttachedToWindow();
        if (!EventBus.getDefault().isRegistered(this)) {
            EventBus.getDefault().register(this);
        }
    }

    @Override
    protected void onDetachedFromWindow() {
        stopScanWave();
        super.onDetachedFromWindow();
        hideDragTipLoop();
        if (EventBus.getDefault().isRegistered(this)) {
            EventBus.getDefault().unregister(this);
        }
        dismissMoreSuggestionsPanel();
    }

    @Override
    protected void onSizeChanged(final int w, final int h, final int oldw, final int oldh) {
        // Called by the framework when the size is known. Show the important notice if applicable.
        // This may be overriden by showing suggestions later, if applicable.

        super.onSizeChanged(w, h, oldw, oldh);
        // 크기가 바뀌어 0이 아니게 되면 레이더 시작
        if (w > 0 && h > 0) {
            // 기존 애니메이터가 있으면 중지
            if (mScanAnimator != null) {
                mScanAnimator.cancel();
                mScanAnimator = null;
            }
            post(this::startScanWave);
        }
    }

    // SuggestionStripView 내부
    private void showSearchPanel() {
        if (mMainKeyboardView == null) {
            View root = getRootView();
            mMainKeyboardView = root.findViewById(R.id.keyboard_view);
        }
        if (mMainKeyboardView == null) return;

        MoreKeysPanel.Controller c = new MoreKeysPanel.Controller() {
            @Override
            public void onDismissMoreKeysPanel() {
                mMainKeyboardView.onDismissMoreKeysPanel();
            }

            @Override
            public void onShowMoreKeysPanel(MoreKeysPanel p) {
                mMainKeyboardView.onShowMoreKeysPanel(p);
            }

            @Override
            public void onCancelMoreKeysPanel() {
                mMainKeyboardView.onDismissMoreKeysPanel();
            }
        };
        int x = mMainKeyboardView.getWidth() / 2, y = 0;
        mSearchPanel.showMoreKeysPanel(mMainKeyboardView, c, x, y, (KeyboardActionListener) null);
    }

    private int dpToPx(int dp) {
        return Math.round(dp * getResources().getDisplayMetrics().density);
    }

    private void applyStripTypefaceRecursively(View v) {
        if (v instanceof TextView) {
            TextView tv = (TextView) v;
            tv.setTypeface(STRIP_TYPEFACE);
            tv.setTextSize(TypedValue.COMPLEX_UNIT_PX, tv.getTextSize() * STRIP_TEXT_SCALE);
        } else if (v instanceof ViewGroup) {
            ViewGroup vg = (ViewGroup) v;
            for (int i = 0; i < vg.getChildCount(); i++) {
                applyStripTypefaceRecursively(vg.getChildAt(i));
            }
        }
    }

    private void expandDragArea() {
        // 원래 높이 + 확장 크기
        int extra = dpToPx(417);
        mDragExtra = extra;
        mIsDragging = true;

        ViewGroup.LayoutParams lp = getLayoutParams();
        lp.height += extra;
        setLayoutParams(lp);

        // 2) 위쪽 패딩 추가 — 늘어난 빈 공간이 위에 생김
        setPadding(
                getPaddingLeft(),
                extra,
                getPaddingRight(),
                getPaddingBottom()
        );
        invalidate();
    }

    private void collapseDragArea() {
        mDragExtra = 0;
        mIsDragging = false;

        // 1) 위쪽 패딩 원복
        setPadding(
                getPaddingLeft(),
                0,
                getPaddingRight(),
                getPaddingBottom()
        );

        // PHOTO_ONLY 모드 때의 높이 (96dp 썸네일 + 6dp 여유)
        int barSize = dpToPx(96);
        int targetHeight = barSize + dpToPx(6);
        ViewGroup.LayoutParams lp = getLayoutParams();
        lp.height = targetHeight;
        setLayoutParams(lp);

        invalidate();

        hideDragTipLoop();
    }

    @Override
    public void draw(Canvas canvas) {
        if (mIsDragging && mDragExtra > 0) {
            // 1) 뷰의 “원래” 부분만 정상 렌더링
            int save = canvas.save();
            // y = mDragExtra 아래만 그리도록 클립
            canvas.clipRect(0, mDragExtra, getWidth(), getHeight());
            super.draw(canvas);
            canvas.restoreToCount(save);

            // hover 중이면 더 진한 페인트 사용
            Paint p = mDragHover ? mOverlayPaintHover : mOverlayPaint;
            canvas.drawRect(0, 0, getWidth(), mDragExtra, p);

            // ── 여기서 드롭 아이콘 그리기 ──
            if (mDropIcon != null) {
                int cx = getWidth() / 2;
                int cy = mDragExtra / 2;
                int half = mDropIconSize / 2;
                mDropIcon.setBounds(cx - half, cy - half, cx + half, cy + half);
                mDropIcon.draw(canvas);
            }
        } else {
            super.draw(canvas);
        }
    }

    /**
     * 자연스럽고 적당히 보이는 그라디언트 웨이브 애니메이션
     * 검색 모드 동안 지속되는 키보드 웨이브 애니메이션
     */
    private void showKeyboardClickAnimation() {
        if (mMainKeyboardView == null || mIsAnimatingKeyboard) return;

        // 원본 배경 저장
        if (mOriginalKeyboardBackground == null) {
            mOriginalKeyboardBackground = mMainKeyboardView.getBackground();
        }

        mIsAnimatingKeyboard = true;

        // 무한 반복되는 부드러운 웨이브 애니메이션
        mKeyboardWaveAnimator = ValueAnimator.ofFloat(0f, 1f);
        mKeyboardWaveAnimator.setDuration(3000); // 주기
        mKeyboardWaveAnimator.setRepeatCount(ValueAnimator.INFINITE);
        mKeyboardWaveAnimator.setRepeatMode(ValueAnimator.RESTART);
        mKeyboardWaveAnimator.setInterpolator(new android.view.animation.LinearInterpolator());

        mKeyboardWaveAnimator.addUpdateListener(animation -> {
            if (mIsAnimatingKeyboard) {
                float progress = (float) animation.getAnimatedValue();
                applyVisibleWaveEffect(progress);
            }
        });

        mKeyboardWaveAnimator.start();
        Log.d("KeyboardAnimation", "지속적인 웨이브 애니메이션 시작");
    }

    /**
     * 키보드 애니메이션 중지 및 원상복구
     */
    private void stopKeyboardAnimation() {
        if (mKeyboardWaveAnimator != null) {
            mKeyboardWaveAnimator.cancel();
            mKeyboardWaveAnimator = null;
        }

        mIsAnimatingKeyboard = false;

        // 키보드 원복
        if (mMainKeyboardView != null && mOriginalKeyboardBackground != null) {
            mMainKeyboardView.setBackground(mOriginalKeyboardBackground);
            mMainKeyboardView.setAlpha(1f);
        }

        Log.d("KeyboardAnimation", "키보드 애니메이션 중지 및 원상복구");
    }


    /**
     * 키보드 애니메이션 빈 여백 제거 - 빠른 수정
     * 기존 코드에서 이 부분만 교체하세요
     */
    private void applyVisibleWaveEffect(float progress) {
        if (mMainKeyboardView == null) return;

        // 자연스러운 물결 패턴
        double mainWave = Math.sin(progress * Math.PI);
        float wave1 = (float) Math.sin(progress * Math.PI * 3) * 0.2f;
        float wave2 = (float) Math.sin(progress * Math.PI * 1.5f) * 0.15f;

        float intensity = (float) (mainWave + wave1 + wave2);
        intensity = Math.max(0f, Math.min(1f, intensity));

        // 하늘색-보라색 계열
        int[] skyPurpleColors = {
                Color.parseColor("#87CEEB"), // 하늘색
                Color.parseColor("#6495ED"), // 콘플라워 블루
                Color.parseColor("#7B68EE"), // 미디엄 슬레이트 블루
                Color.parseColor("#9370DB"), // 보라색
                Color.parseColor("#BA68C8"), // 미디엄 오키드
                Color.parseColor("#8A2BE2")  // 블루 바이올렛
        };

        int colorIndex = (int) (progress * 2) % skyPurpleColors.length;
        int nextColorIndex = (colorIndex + 1) % skyPurpleColors.length;
        float colorProgress = (progress * 2) % 1f;

        int baseColor = interpolateColor(skyPurpleColors[colorIndex], skyPurpleColors[nextColorIndex], colorProgress);

        GradientDrawable waveDrawable = new GradientDrawable();
        waveDrawable.setShape(GradientDrawable.RECTANGLE);
        waveDrawable.setOrientation(GradientDrawable.Orientation.BOTTOM_TOP);

        int baseAlpha = (int) (intensity * 140);

        // ✨ 핵심 수정: 더 넓은 범위의 그라디언트로 여백까지 커버
        int[] gradientColors = new int[]{
                Color.argb(baseAlpha, Color.red(baseColor), Color.green(baseColor), Color.blue(baseColor)),           // 100%
                Color.argb(baseAlpha * 9 / 10, Color.red(baseColor), Color.green(baseColor), Color.blue(baseColor)),   // 90%
                Color.argb(baseAlpha * 8 / 10, Color.red(baseColor), Color.green(baseColor), Color.blue(baseColor)),   // 80%
                Color.argb(baseAlpha * 7 / 10, Color.red(baseColor), Color.green(baseColor), Color.blue(baseColor)),   // 70%
                Color.argb(baseAlpha * 6 / 10, Color.red(baseColor), Color.green(baseColor), Color.blue(baseColor)),   // 60%
                Color.argb(baseAlpha * 5 / 10, Color.red(baseColor), Color.green(baseColor), Color.blue(baseColor)),   // 50%
                Color.argb(baseAlpha * 4 / 10, Color.red(baseColor), Color.green(baseColor), Color.blue(baseColor)),   // 40%
                Color.argb(baseAlpha * 3 / 10, Color.red(baseColor), Color.green(baseColor), Color.blue(baseColor)),   // 30%
                Color.argb(baseAlpha * 2 / 10, Color.red(baseColor), Color.green(baseColor), Color.blue(baseColor)),   // 20%
                Color.argb(baseAlpha / 10, Color.red(baseColor), Color.green(baseColor), Color.blue(baseColor))      // 10%
        };

        waveDrawable.setColors(gradientColors);

        // 핵심 수정: 코너를 완전히 제거하여 전체 영역 채우기
        waveDrawable.setCornerRadius(0);

        mMainKeyboardView.setBackground(waveDrawable);

        // 미세한 투명도 변화
        float breathingAlpha = 0.95f + (intensity * 0.05f);
        mMainKeyboardView.setAlpha(breathingAlpha);
    }

    /**
     * 두 색상 사이의 부드러운 보간
     */
    private int interpolateColor(int colorA, int colorB, float progress) {
        int aA = Color.alpha(colorA);
        int rA = Color.red(colorA);
        int gA = Color.green(colorA);
        int bA = Color.blue(colorA);

        int aB = Color.alpha(colorB);
        int rB = Color.red(colorB);
        int gB = Color.green(colorB);
        int bB = Color.blue(colorB);

        return Color.argb(
                (int) (aA + (aB - aA) * progress),
                (int) (rA + (rB - rA) * progress),
                (int) (gA + (gB - gA) * progress),
                (int) (bA + (bB - bA) * progress)
        );
    }

    // SuggestionStripView 클래스 안, 아무 메서드 밑에 위치만 맞춰 추가
    private static void startBreathing(@NonNull View v) {
        // 이미 실행 중이면 중복 방지
        if (v.getTag(R.id.tag_breathing_anim) != null) return;

        // 구간별 시간(ms)
        long upDuration = 300;
        long downDuration = 300;
        long idleDuration = 2000;
        long total = upDuration + downDuration + idleDuration;

        // Keyframe 생성 (fraction, value)
        Keyframe kf0 = Keyframe.ofFloat(0f, 1f);   // 시작
        Keyframe kf1 = Keyframe.ofFloat(upDuration / (float) total, 1.1f); // 300ms 시점
        Keyframe kf2 = Keyframe.ofFloat((upDuration + downDuration) / (float) total, 1f); // 600ms 시점
        Keyframe kf3 = Keyframe.ofFloat(1f, 1f);   // 100%

        // 스케일 X/Y PropertyValuesHolder
        PropertyValuesHolder pvhX = PropertyValuesHolder.ofKeyframe("scaleX", kf0, kf1, kf2, kf3);
        PropertyValuesHolder pvhY = PropertyValuesHolder.ofKeyframe("scaleY", kf0, kf1, kf2, kf3);

        // ObjectAnimator 로 View 프로퍼티 직접 애니
        ObjectAnimator animator = ObjectAnimator.ofPropertyValuesHolder(v, pvhX, pvhY);
        animator.setDuration(total);
        animator.setInterpolator(new LinearInterpolator());
        animator.setRepeatCount(ValueAnimator.INFINITE);
        animator.start();

        // 나중에 cancel 용으로 태그에 저장
        v.setTag(R.id.tag_breathing_anim, animator);
    }

    private static void stopBreathing(@NonNull View v) {
        Object tag = v.getTag(R.id.tag_breathing_anim);
        if (tag instanceof Animator) {
            ((Animator) tag).cancel();
            v.setTag(R.id.tag_breathing_anim, null);
        }
    }

    private void startScanWave() {
        if (mMainKeyboardView == null || mScanAnimator != null) return;

        // 키보드 뷰 크기 기준 최대 반지름
        int w = mMainKeyboardView.getWidth();
        int h = mMainKeyboardView.getHeight();

        // 아직 사이즈가 없으면 한 프레임 뒤에 재시도
        if (w == 0 || h == 0) {
            mMainKeyboardView.post(this::startScanWave);
            return;
        }

        int maxR = Math.max(w, h) / 2;

        // 배경으로 ScanWaveDrawable 추가
        mScanWaveDrawable = new ScanWaveDrawable(maxR);
        LayerDrawable layer = new LayerDrawable(new Drawable[]{
                mOriginalKeyboardBackground != null ? mOriginalKeyboardBackground : new ColorDrawable(Color.TRANSPARENT),
                mScanWaveDrawable
        });
        mMainKeyboardView.setBackground(layer);

        // 0 → maxR, alpha 120 → 0 반복
        mScanAnimator = ValueAnimator.ofFloat(0f, 1f);
        mScanAnimator.setDuration(3000);
        mScanAnimator.setRepeatCount(ValueAnimator.INFINITE);
        mScanAnimator.setInterpolator(new LinearInterpolator());
        mScanAnimator.addUpdateListener(anim -> {
            float t = (float) anim.getAnimatedValue();
            float r = t * maxR;
            int a = (int) ((1 - t) * 120);  // 120 → 0 투명도
            mScanWaveDrawable.setWave(r, a);
        });
        mScanAnimator.start();
    }

    private void stopScanWave() {
        if (mScanAnimator != null) {
            mScanAnimator.cancel();
            mScanAnimator = null;
        }
        // 배경 복원
        if (mMainKeyboardView != null && mOriginalKeyboardBackground != null) {
            mMainKeyboardView.setBackground(mOriginalKeyboardBackground);
        }
    }

    private static class ScanWaveDrawable extends Drawable {
        private final Paint mPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private float radius;     // 현재 파동 반지름
        private int alpha;        // 현재 투명도
        private final int maxRadius;

        public ScanWaveDrawable(int maxRadius) {
            this.maxRadius = maxRadius;
            mPaint.setStyle(Paint.Style.FILL);
        }

        public void setWave(float r, int a) {
            this.radius = r;
            this.alpha = a;
            invalidateSelf();
        }

        @Override
        public void draw(Canvas canvas) {
            if (radius <= 1f) return;

            mPaint.setAlpha(alpha);

            float cx = canvas.getWidth() * 0.5f;
            float cy = canvas.getHeight() * 0.90f;

            // 실제 그릴 반경: 원래 radius 의 5배
            float drawR = radius * 5f;

            int innerColor = Color.argb(Math.min(alpha * 2, 255), 0, 120, 255);
            int outerColor = Color.argb(0, 0, 120, 255);

            Shader shader = new RadialGradient(
                    cx, cy, drawR,
                    innerColor,
                    outerColor,
                    Shader.TileMode.CLAMP
            );
            mPaint.setShader(shader);
            canvas.drawCircle(cx, cy, drawR, mPaint);
            mPaint.setShader(null);
        }

        @Override
        public void setAlpha(int a) {
        }

        @Override
        public void setColorFilter(ColorFilter cf) {
        }

        @Override
        public int getOpacity() {
            return PixelFormat.TRANSLUCENT;
        }

        @Override
        public int getIntrinsicWidth() {
            return maxRadius * 2;
        }

        @Override
        public int getIntrinsicHeight() {
            return maxRadius * 2;
        }
    }
}