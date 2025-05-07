import { CameraRoll } from '@react-native-camera-roll/camera-roll';

/**
 * 이미 다른 화면에서 권한을 얻었다고 가정
 * @param id  예) "0002"
 * @returns   content://…  URI   (찾지 못하면 null)
 */
export async function getScreenshotUriById(id: string): Promise<string | null> {
  // 'Screenshots' 앨범에서 최근 100개만 검색
  const { edges } = await CameraRoll.getPhotos({
    first: 100,
    groupName: 'Screenshots',
    assetType: 'Photos',
  });

  const edge = edges.find(e => e.node.image.filename?.startsWith(id));
  return edge?.node.image.uri ?? null;
}
