import {format} from 'date-fns';
import {useAuthStore} from '../stores/authStore';
import {useBackupStore} from '../stores/useBackupStore';

export const uploadImagesToServer = async (
  images: {uri: string; filename: string; timestamp: number | Date}[],
  onSuccess?: (filename: string) => void,
) => {
  const {userId} = useAuthStore.getState();
  const {setLastUploadedAt} = useBackupStore.getState();
  if (!userId) throw new Error('로그인이 필요합니다.');

  let latestUploaded = 0;

  const uploadTasks = images.map(async image => {
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

    try {
      const response = await fetch(
        'http://k12e201.p.ssafy.io:8090/rag/upload-image/',
        {
          method: 'POST',
          body: formData,
        },
      );

      const result = await response.json();
      const filename = image.filename;
      const timestamp = Number(image.timestamp);

      if (result?.status === 'skipped') {
        console.warn(`⚠️ 중복된 이미지 스킵됨: ${filename}`);
        onSuccess?.(filename); // 중복이더라도 backedUp에 추가
        return;
      }

      console.log('✅ 업로드 성공:', result);
      latestUploaded = Math.max(latestUploaded, timestamp);
      onSuccess?.(filename);
    } catch (error) {
      console.error(`❌ 업로드 실패 (${image.filename}):`, error);
    }
  });

  await Promise.all(uploadTasks);

  if (latestUploaded > 0) {
    setLastUploadedAt(latestUploaded);
  }
};
