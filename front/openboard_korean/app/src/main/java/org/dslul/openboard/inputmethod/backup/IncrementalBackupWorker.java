package org.dslul.openboard.inputmethod.backup;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.provider.MediaStore;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.work.Constraints;
import androidx.work.ExistingWorkPolicy;
import androidx.work.OneTimeWorkRequest;
import androidx.work.WorkManager;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import java.time.Duration;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * MediaStore.Images 변화(새 사진 추가)마다 실행되는 증분 백업 워커
 */
public class IncrementalBackupWorker extends Worker {
    private static final String UNIQUE_NAME = "incremental_backup";
    // 지연 시간 (초)
    private static final long DELAY_SEC = 5;

    public IncrementalBackupWorker(@NonNull Context context,
                                   @NonNull WorkerParameters params) {
        super(context, params);
    }

    @NonNull
    @Override
    public Result doWork() {
        Context ctx = getApplicationContext();

        // ① 워커 시작 시점에 바로 “다음 증분” 워크 재스케줄
        Constraints cons = new Constraints.Builder()
            .addContentUriTrigger(
                MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
                /* triggerForDescendants= */ true
            )
            .setTriggerContentUpdateDelay(Duration.ofSeconds(DELAY_SEC))
            .build();

        OneTimeWorkRequest next =
            new OneTimeWorkRequest.Builder(IncrementalBackupWorker.class)
                .setConstraints(cons)
                .build();

        WorkManager.getInstance(ctx)
            .enqueueUniqueWork(
                UNIQUE_NAME,
                ExistingWorkPolicy.REPLACE,
                next
            );

        // ② 실제 증분 백업 수행 (BackupManager가 이미 백업된 사진은 걸러줌)
        AtomicInteger totalCount = new AtomicInteger(0);
        BackupManager.startBackup(
                ctx,
                total -> {
                    // 업로드 시작 시 총 개수 저장 & 토스트
                    totalCount.set(total);
                    new Handler(Looper.getMainLooper()).post(() ->
                            Toast.makeText(ctx,
                                    total + "개 새 사진 백업 시작",
                                    Toast.LENGTH_SHORT
                            ).show()
                    );
                },
                done -> {
                    // 진행률 업데이트 토스트
                    new Handler(Looper.getMainLooper()).post(() ->
                            Toast.makeText(ctx,
                                    done + "/" + totalCount.get() + " 백업 중…",
                                    Toast.LENGTH_SHORT
                            ).show()
                    );
                },
                () -> {
                    // 완료 시 토스트
                    new Handler(Looper.getMainLooper()).post(() ->
                            Toast.makeText(ctx,
                                    "새 사진 증분 백업 완료 🎉",
                                    Toast.LENGTH_SHORT
                            ).show()
                    );
                }
        );

        return Result.success();
    }
}
