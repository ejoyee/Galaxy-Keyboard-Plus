package org.dslul.openboard.inputmethod.latin.settings;

import android.app.Fragment;
import android.content.ContentUris;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.provider.MediaStore;
import android.util.TypedValue;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.EditText;
import android.widget.ImageButton;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import org.dslul.openboard.inputmethod.latin.R;
import org.dslul.openboard.inputmethod.latin.network.ChatApiService;
import org.dslul.openboard.inputmethod.latin.network.InfoResult;
import org.dslul.openboard.inputmethod.latin.network.MessageRequest;
import org.dslul.openboard.inputmethod.latin.network.MessageResponse;
import org.dslul.openboard.inputmethod.latin.network.PhotoResult;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.concurrent.TimeUnit;

import okhttp3.OkHttpClient;
import okhttp3.logging.HttpLoggingInterceptor;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

public class SearchPageFragment extends Fragment {
    private RecyclerView rvMessages;
    private TextView tvStatus;
    private EditText etMessage;
    private ImageButton btnSend;

    private MessageAdapter adapter;
    private List<Message> messages = new ArrayList<>();

    // Retrofit 서비스
    private ChatApiService chatApiService;

    private ScrollView scrollResults;
    private LinearLayout llResultsContainer;

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup container,
                             Bundle savedInstanceState) {
        return inflater.inflate(R.layout.fragment_search_page, container, false);
    }

    @Override
    public void onViewCreated(View view, Bundle savedInstanceState) {
        rvMessages = view.findViewById(R.id.rvMessages);
        tvStatus   = view.findViewById(R.id.tvStatus);
        etMessage  = view.findViewById(R.id.etMessage);
        btnSend    = view.findViewById(R.id.btnSend);

        /* ▼ 1) 톱니 아이콘 참조 후 리스너 등록 -------------------- */
        ImageButton btnSettings = view.findViewById(R.id.btnSettings);
        btnSettings.setOnClickListener(v -> {
            // 설정 화면으로 진입
            startActivity(new Intent(getActivity(), SettingsActivity.class));
        });
        /* ▲------------------------------------------------------- */

        adapter = new MessageAdapter(messages);
        rvMessages.setLayoutManager(new LinearLayoutManager(getContext()));
        rvMessages.setAdapter(adapter);

        // 결과 컨테이너 바인딩
        scrollResults        = view.findViewById(R.id.scrollResults);
        llResultsContainer   = view.findViewById(R.id.llResultsContainer);

        // Retrofit + OkHttp 로깅 설정
        HttpLoggingInterceptor logging = new HttpLoggingInterceptor();
        logging.setLevel(HttpLoggingInterceptor.Level.BODY);
        OkHttpClient client = new OkHttpClient.Builder()
                .addInterceptor(logging)
                .connectTimeout(60, TimeUnit.SECONDS)   // 연결 타임아웃
                .readTimeout(60, TimeUnit.SECONDS)      // 읽기(응답 대기) 타임아웃
                .writeTimeout(60, TimeUnit.SECONDS)     // 쓰기(요청 바디 전송) 타임아웃
                .build();

        Retrofit retrofit = new Retrofit.Builder()
                .baseUrl("http://k12e201.p.ssafy.io:8090/") // 실제 베이스 URL 로 변경
                .client(client)
                .addConverterFactory(GsonConverterFactory.create())
                .build();

        chatApiService = retrofit.create(ChatApiService.class);

        btnSend.setOnClickListener(v -> {
            String text = etMessage.getText().toString().trim();
            if (text.isEmpty()) return;
            sendMessage(text);
        });
    }

    private void sendMessage(String text) {
        // 1) 사용자 메시지 추가
        Message userMsg = new Message(
                Message.Sender.USER,
                text,
                new Date()
        );
        messages.add(userMsg);
        adapter.notifyItemInserted(messages.size() - 1);
        rvMessages.scrollToPosition(messages.size() - 1);

        etMessage.setText("");
        showStatus("응답을 기다리는 중...", true);

        String userId = "36648ad3-ed4b-4eb0-bcf1-1dc66fa5d258";
        MessageRequest req = new MessageRequest(userId, text);

        // 2) 네트워크 호출
        chatApiService.search(req.getUserId(), req.getQuery())
                .enqueue(new Callback<MessageResponse>() {
                    @Override
                    public void onResponse(Call<MessageResponse> call, Response<MessageResponse> resp) {
                        showStatus("", false);
                        if (!resp.isSuccessful() || resp.body() == null) {
                            showStatus("서버 응답 오류", true);
                            return;
                        }
                        MessageResponse body = resp.body();
                        // getReply() 대신 getAnswer()
                        String botText = body.getAnswer() != null ? body.getAnswer() : "정보를 찾았습니다.";
                        Message botMsg = new Message(
                                Message.Sender.BOT,
                                botText,
                                new Date(),
                                body.getQueryType(),
                                body.getAnswer(),
                                body.getPhotoResults(),
                                body.getInfoResults()
                        );
                        messages.add(botMsg);
                        adapter.notifyItemInserted(messages.size() - 1);
                        rvMessages.scrollToPosition(messages.size() - 1);

                        displayFullResponse(body);
                    }

                    @Override
                    public void onFailure(Call<MessageResponse> call, Throwable t) {
                        showStatus("네트워크 오류: " + t.getMessage(), true);
                    }
                });
    }

    private void displayFullResponse(MessageResponse body) {
        // 1) 결과 컨테이너 보이기
        scrollResults.setVisibility(View.VISIBLE);
        llResultsContainer.removeAllViews();

        Context ctx = getContext();

        // 2) 답변 텍스트 추가
        TextView tvAnswer = new TextView(ctx);
        tvAnswer.setText(body.getAnswer());
        tvAnswer.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16);
        tvAnswer.setPadding(0, 0, 0, dpToPx(12));
        llResultsContainer.addView(tvAnswer);

        // 3) photo_results: MediaStore 에서 Uri 만들고 ImageView 추가
        List<PhotoResult> photos = body.getPhotoResults();
        if (photos != null && !photos.isEmpty()) {
            for (PhotoResult pr : photos) {
                long mediaId;
                try {
                    mediaId = Long.parseLong(pr.getId());
                } catch (NumberFormatException e) {
                    continue; // id 파싱 실패 시 건너뜀
                }
                Uri imgUri = ContentUris.withAppendedId(
                        MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
                        mediaId
                );

                ImageView iv = new ImageView(ctx);
                LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        dpToPx(200)
                );
                lp.setMargins(0, 0, 0, dpToPx(12));
                iv.setLayoutParams(lp);
                iv.setScaleType(ImageView.ScaleType.CENTER_CROP);
                iv.setImageURI(imgUri);  // MediaStore 에서 불러오기
                llResultsContainer.addView(iv);
            }
        }

        // 4) info_results
        List<InfoResult> infos = body.getInfoResults();
        if (infos != null && !infos.isEmpty()) {
            for (InfoResult ir : infos) {
                long mediaId;
                try {
                    mediaId = Long.parseLong(ir.getId());
                } catch (NumberFormatException e) {
                    continue;
                }
                Uri imgUri = ContentUris.withAppendedId(
                        MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
                        mediaId
                );

                ImageView ivInfo = new ImageView(ctx);
                LinearLayout.LayoutParams lpInfo = new LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        dpToPx(200)
                );
                lpInfo.setMargins(0, 0, 0, dpToPx(12));
                ivInfo.setLayoutParams(lpInfo);
                ivInfo.setScaleType(ImageView.ScaleType.CENTER_CROP);
                ivInfo.setImageURI(imgUri);
                llResultsContainer.addView(ivInfo);
            }
        }

        // 스크롤 최하단으로 이동
        scrollResults.post(() -> scrollResults.fullScroll(ScrollView.FOCUS_DOWN));
    }

    // dp → px 변환 헬퍼
    private int dpToPx(int dp) {
        return Math.round(dp * getResources().getDisplayMetrics().density);
    }

    private void showStatus(String msg, boolean visible) {
        tvStatus.setText(msg);
        tvStatus.setVisibility(visible ? View.VISIBLE : View.GONE);
    }
}
