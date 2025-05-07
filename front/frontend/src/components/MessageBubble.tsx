import React from 'react';
import { View, Image, Text } from 'react-native';
import tw from 'twrnc';
import PhotoThumb from './PhotoThumb';

const CAT_ICON = require('../assets/cat.png');
const USER_BG = '#FFF0B4';

export interface PhotoResult {
  score: number;
  id: string;
  text: string;
}
export interface InfoResult {
  score: number;
  id: string;
  text: string;
}
export interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
  query_type?: 'photo' | 'info' | 'ambiguous';
  answer?: string;
  photo_results?: PhotoResult[];
  info_results?: InfoResult[];
}

const MessageBubble: React.FC<{ item: Message }> = ({ item }) => {
  const isUser = item.sender === 'user';

  const showInfoList =
    item.sender === 'bot' &&
    item.query_type === 'info' &&
    item.info_results &&
    item.info_results.length > 0;

  const showPhotoGrid =
    item.sender === 'bot' && item.photo_results?.length;

  return (
    <View style={tw`flex-row my-[4px] ${isUser ? 'justify-end' : 'items-start'}`}>
      {!isUser && <Image source={CAT_ICON} style={tw`w-[32px] h-[32px] mr-[6px]`} />}

      <View
        style={tw`
          max-w-[78%] px-[12px] py-[8px] rounded-[12px]
          ${isUser
            ? `self-end bg-[${USER_BG}] rounded-br-none`
            : 'bg-white border border-[#E0E0E0] rounded-bl-none'}
        `}
      >
        {/* ---- 메인 텍스트 ---- */}
        <Text style={tw`text-[15px] leading-[20px]`}>{item.text}</Text>

        {/* ---- 사진 결과 ---- */}
        {showPhotoGrid && (
          <View style={tw`flex-row flex-wrap mt-[8px]`}>
            {item.photo_results!.map((photo, idx) => (
              <PhotoThumb
                key={`${item.id}-photo-${photo.id}-${idx}`}
                id={photo.id}
                score={photo.score}
              />
            ))}
          </View>
        )}

        {/* ---- info 결과 ---- */}
        {showInfoList && (
          <View style={tw`mt-[10px] pt-[8px] border-t border-[#EEE]`}>
            {item.info_results!.map(info => (
              <View key={`${item.id}-info-${info.id}`} style={tw`bg-[#f7f7f7] p-[10px] rounded-[6px] mb-[6px]`}>
                <Text style={tw`text-[13px] leading-[18px] text-[#333]`}>{info.text}</Text>
                <Text style={tw`text-[10px] text-[#555] text-right mt-[4px]`}>
                  {info.score.toFixed(2)}
                </Text>
              </View>
            ))}
          </View>
        )}

        <Text style={tw`text-[10px] text-[#999] self-end mt-[4px]`}>
          {item.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </Text>
      </View>
    </View>
  );
};

export default MessageBubble;
