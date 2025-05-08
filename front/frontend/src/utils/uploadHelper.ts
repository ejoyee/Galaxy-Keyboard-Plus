import {format} from 'date-fns';
import { useAuthStore } from '../stores/authStore';

/**
 * rag에 이미지 업로드 하는 api를 병렬로 호출하는 메소드
 */
export const uploadImagesToServer = async (
  images: {uri: string; filename: string; timestamp: number | Date}[],
) => {
  // 1) zustand에서 userId 꺼내기
  const { userId } = useAuthStore.getState();
  if (!userId) {
    throw new Error('로그인이 필요합니다.');
  }

  // 2) 각 이미지에 대해 formData 구성 & fetch
  const uploadPromises = images.map(async image => {
    const accessId = image.filename.replace(/\.[^/.]+$/, '');
    const imageTime = format(image.timestamp, 'yyyy:MM:dd HH:mm:ss');

    const formData = new FormData();
    formData.append('user_id', userId);
    formData.append('access_id', accessId);
    formData.append('image_time', imageTime);
    formData.append('file', {
      uri: image.uri,
      type: 'image/jpeg',
      name: image.filename,
    });

    console.log('📤 fetch 업로드 시도:', {
      uri: image.uri,
      filename: image.filename,
      accessId,
      imageTime,
    });

    try {
      const response = await fetch(
        'http://k12e201.p.ssafy.io:8090/rag/upload-image/',
        {
          method: 'POST',
          body: formData,
        },
      );

      const result = await response.json();
      console.log('✅ fetch 업로드 성공:', result);
    } catch (error) {
      console.error(`❌ fetch 업로드 오류 (${image.filename}):`, error);
    }
  });

  // 병렬 실행
  await Promise.all(uploadPromises);
};