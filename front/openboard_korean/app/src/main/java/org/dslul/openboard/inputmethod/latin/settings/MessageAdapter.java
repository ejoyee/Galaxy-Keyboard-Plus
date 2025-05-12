// File: app/src/main/java/org/dslul/openboard/inputmethod/latin/settings/MessageAdapter.java
package org.dslul.openboard.inputmethod.latin.settings;

import android.content.ContentUris;
import android.net.Uri;
import android.provider.MediaStore;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.GridLayout;
import android.widget.ImageView;
import android.widget.TextView;

import androidx.recyclerview.widget.RecyclerView;

import org.dslul.openboard.inputmethod.latin.R;
import org.dslul.openboard.inputmethod.latin.network.InfoResult;
import org.dslul.openboard.inputmethod.latin.network.PhotoResult;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public class MessageAdapter extends RecyclerView.Adapter<RecyclerView.ViewHolder> {
    private static final int VIEW_TYPE_USER = 0;
    private static final int VIEW_TYPE_BOT  = 1;

    private final List<Message> messages;

    public MessageAdapter(List<Message> messages) {
        this.messages = messages;
    }

    @Override
    public int getItemViewType(int position) {
        return messages.get(position).getSender() == Message.Sender.USER
            ? VIEW_TYPE_USER
            : VIEW_TYPE_BOT;
    }

    @Override
    public RecyclerView.ViewHolder onCreateViewHolder(ViewGroup parent, int viewType) {
        LayoutInflater inflater = LayoutInflater.from(parent.getContext());
        if (viewType == VIEW_TYPE_USER) {
            View view = inflater.inflate(R.layout.item_message_user, parent, false);
            return new UserViewHolder(view);
        } else {
            View view = inflater.inflate(R.layout.item_message_bot, parent, false);
            return new BotViewHolder(view);
        }
    }

    @Override
    public void onBindViewHolder(RecyclerView.ViewHolder holder, int position) {
        Message msg = messages.get(position);
        String text = msg.getText()
            + "\n"
            + new SimpleDateFormat("HH:mm", Locale.getDefault()).format(msg.getTimestamp());

        if (holder instanceof UserViewHolder) {
            ((UserViewHolder) holder).tvMessage.setText(text);
        } else if (holder instanceof BotViewHolder) {
            ((BotViewHolder) holder).bind(msg);
            ((BotViewHolder) holder).tvMessage.setText(text);
        }
    }

    @Override
    public int getItemCount() {
        return messages.size();
    }

    static class UserViewHolder extends RecyclerView.ViewHolder {
        final TextView tvMessage;
        UserViewHolder(View itemView) {
            super(itemView);
            tvMessage = itemView.findViewById(R.id.tvUserMessage);
        }
    }

    static class BotViewHolder extends RecyclerView.ViewHolder {
        final TextView tvMessage;
        final GridLayout glImages;

        BotViewHolder(View v) {
            super(v);
            tvMessage = v.findViewById(R.id.tvBotMessage);
            glImages  = v.findViewById(R.id.glBotImages);
        }

        void bind(Message m) {
            String body = m.getAnswer() == null ? m.getText() : m.getAnswer();
            tvMessage.setText(body);

            /* id → Uri 변환 */
            List<Uri> uris = new ArrayList<>();
            addUrisFromPhotos(m.getPhotoResults(), uris);
            addUrisFromInfos (m.getInfoResults(),  uris);

            /* 그리드 채우기 */
            glImages.removeAllViews();
            if (uris.isEmpty()) {
                glImages.setVisibility(View.GONE);
                return;
            }
            glImages.setVisibility(View.VISIBLE);

            final int size = dpToPx(120, glImages);
            for (Uri u : uris) {
                ImageView iv = new ImageView(glImages.getContext());
                GridLayout.LayoutParams lp = new GridLayout.LayoutParams();
                lp.width = size; lp.height = size;
                lp.setMargins(0, 0, dpToPx(4, glImages), dpToPx(4, glImages));
                iv.setLayoutParams(lp);
                iv.setScaleType(ImageView.ScaleType.CENTER_CROP);
                iv.setImageURI(u);
                glImages.addView(iv);
            }
        }

        /* ---------- 헬퍼 ---------- */
        private void addUrisFromPhotos(List<PhotoResult> list, List<Uri> out) {
            if (list == null) return;
            for (PhotoResult r : list) {
                try {
                    long id = Long.parseLong(r.getId());
                    out.add(ContentUris.withAppendedId(
                            MediaStore.Images.Media.EXTERNAL_CONTENT_URI, id));
                } catch (NumberFormatException ignored) {}
            }
        }
        private void addUrisFromInfos(List<InfoResult> list, List<Uri> out) {
            if (list == null) return;
            for (InfoResult r : list) {
                try {
                    long id = Long.parseLong(r.getId());
                    out.add(ContentUris.withAppendedId(
                            MediaStore.Images.Media.EXTERNAL_CONTENT_URI, id));
                } catch (NumberFormatException ignored) {}
            }
        }
        private int dpToPx(int dp, View v){
            return Math.round(dp * v.getResources().getDisplayMetrics().density);
        }
    }
}
