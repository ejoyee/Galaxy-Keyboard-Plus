// components/ImageThumbnail.tsx

import {Image, View} from 'react-native';

import {BasicImageItem} from '../types/imageTypes';
import Icon from 'react-native-vector-icons/Ionicons';
import React from 'react';
import {generateUriFromAccessId} from '../types/imageTypes';
import tw from '../utils/tw';

type Props = {
  item: BasicImageItem;
  size?: 'small' | 'large';
};

export const ImageThumbnail = ({item, size = 'large'}: Props) => {
  const imageSize = size === 'small' ? 'w-22 h-22' : 'w-28 h-28';

  // ✅ uri가 있으면 그걸 쓰고, 없으면 accessId 기반으로 조합
  const uri = (item as any).uri ?? generateUriFromAccessId(item.accessId);

  console.log('🍧 uri : ', uri);

  return (
    <View style={tw`relative mr-2 mb-2`}>
      <Image source={{uri}} style={tw`${imageSize} rounded-lg bg-gray-200`} />
      {item.star && (
        <View style={tw`absolute bottom-1 right-1`}>
          <Icon name="star" size={16} color="white" />
        </View>
      )}
    </View>
  );
};
