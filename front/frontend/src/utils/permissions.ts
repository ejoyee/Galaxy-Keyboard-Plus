import {PERMISSIONS, RESULTS, request} from 'react-native-permissions';

import {Platform} from 'react-native';

export const requestStoragePermission = async () => {
  if (Platform.OS !== 'android') return true;

  const permission =
    Platform.Version >= 33
      ? PERMISSIONS.ANDROID.READ_MEDIA_IMAGES
      : PERMISSIONS.ANDROID.READ_EXTERNAL_STORAGE;

  const result = await request(permission);

  if (result === RESULTS.GRANTED) {
    console.log('✅ 이미지 접근 권한 허용됨');
    return true;
  } else {
    console.warn('❌ 권한 거부됨');
    return false;
  }
};
