import {request, PERMISSIONS, RESULTS} from 'react-native-permissions';

export const requestStoragePermission = async () => {
  const result = await request(PERMISSIONS.ANDROID.READ_MEDIA_IMAGES);
  if (result === RESULTS.GRANTED) {
    console.log('✅ 이미지 접근 권한 허용됨');
  } else {
    console.warn('❌ 권한 거부됨');
  }
};
