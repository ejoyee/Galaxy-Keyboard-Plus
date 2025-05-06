import React from 'react';
import {View, FlatList, Image} from 'react-native';
import Icon from 'react-native-vector-icons/Ionicons';
import {useImageStore} from '../stores/useImageStore';
import tw from '../utils/tw';
import {ImageItem} from '../stores/useImageStore';

const FavoriteGallery = () => {
  const favorites = useImageStore(state =>
    state.images.filter(img => img.isFavorite),
  );

  const renderItem = ({item}: {item: ImageItem}) => (
    <View style={tw`relative m-1`}>
      <Image
        source={{uri: item.uri}}
        style={tw`w-20 h-20 rounded-lg bg-gray-200`}
      />
      <View style={tw`absolute bottom-1 right-1`}>
        <Icon name="star" size={16} color="white" />
      </View>
    </View>
  );

  return (
    <FlatList
      data={favorites}
      renderItem={renderItem}
      keyExtractor={item => item.imageUuid}
      numColumns={4}
      contentContainerStyle={tw`p-3`}
    />
  );
};

export default FavoriteGallery;
