// src/utils/getScreenshotUri.ts
import {CameraRoll, PhotoIdentifier} from '@react-native-camera-roll/camera-roll';

export async function getScreenshotUriById(
  id: string,
  batchSize = 200,          // 한 번에 몇 장씩 가져올지 (적당히 조절)
): Promise<string | null> {
  let after: string | undefined;   // 페이징 커서
  let found: string | null = null;

  do {
    const {edges, page_info} = await CameraRoll.getPhotos({
      first: batchSize,
      groupName: 'Screenshots',    // 필요하면 제거하거나 다른 이름으로 변경
      assetType: 'Photos',
      after,                       // undefined → 첫 페이지
    });

    const match = edges.find(e =>
      e.node.image.filename?.startsWith(id),
    );

    if (match) {
      found = match.node.image.uri;
      break;
    }

    // 다음 페이지로 넘어갈 준비
    after = page_info.has_next_page ? page_info.end_cursor : undefined;
  } while (after);

  return found;  // 찾지 못하면 null
}
