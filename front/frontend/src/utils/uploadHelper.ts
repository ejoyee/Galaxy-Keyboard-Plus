import {format} from 'date-fns';

/**
 * rag에 이미지 업로드 하는 api를 호출하는 메소드
 * service로 빼야 할 거 같기도 한데 일단 utils에 작성
 * 해당 메소드를 사용하여 auth hook이든 test용 uploader에서 사용
 */

export const uploadImagesToServer = async (
  images: {uri: string; filename: string; timestamp: number | Date}[],
  userId = 'dajeong',
) => {
  for (const image of images) {
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
          // Content-Type 생략: 자동 생성되게 둬야 boundary가 포함됨!
        },
      );

      const result = await response.json();
      console.log('✅ fetch 업로드 성공:', result);
    } catch (error) {
      console.error(`❌ fetch 업로드 오류 (${image.filename}):`, error);
    }
  }
};
