const MOCK = true;

export const uploadImagesToServer = async (
  images: {
    uri: string;
    contentId: string;
    filename: string;
    timestamp: number;
  }[],
  userId: string,
): Promise<void> => {
  for (const image of images) {
    // 🍧 더미
    if (MOCK) {
      console.log('[MOCK] 업로드 준비 완료:', {
        user_id: userId,
        image_id: image.contentId,
        file: image.uri,
      });
      continue; // 실제 전송 안 함
    }
    try {
      const formData = new FormData();

      formData.append('user_id', userId);
      formData.append('image_id', image.contentId);
      formData.append('file', {
        uri: image.uri,
        type: 'image/jpeg', // 또는 image/png
        name: image.filename,
      } as any); // RN FormData는 타입 추론 오류가 있어 any로 우회

      const res = await fetch('http://your-backend-url/rag/upload-image', {
        method: 'POST',
        body: formData,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const json = await res.json();

      if (!res.ok || json.status !== 'success') {
        console.warn('❌ 업로드 실패:', json);
      } else {
        console.log('✅ 업로드 성공:', json);
      }
    } catch (err) {
      console.error('업로드 중 오류 발생:', err);
    }
  }
};
