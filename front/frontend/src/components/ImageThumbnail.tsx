// components/ImageThumbnail.tsx
import React from 'react';
import {View, Image} from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import {BasicImageItem} from '../types/imageTypes';
import tw from '../utils/tw';
import {generateUriFromAccessId} from '../types/imageTypes';

type Props = {
  item: BasicImageItem;
  size?: 'small' | 'large';
};

export const ImageThumbnail = ({item, size = 'large'}: Props) => {
  const uri = generateUriFromAccessId(item.accessId);
  const imageSize = size === 'small' ? 'w-22 h-22' : 'w-28 h-28';

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
