// src/screens/ChatScreen.tsx
import React, {useState, useCallback, useRef, useEffect} from 'react';
import {
  View,
  Text,
  TextInput,
  FlatList,
  Image,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  SafeAreaView,
} from 'react-native';
import MaterialCommunityIcons from 'react-native-vector-icons/MaterialCommunityIcons';
import axios from 'axios'; // axios 임포트
import {useHeaderHeight} from '@react-navigation/elements'; // 네비게이터 헤더 높이 hook

interface PhotoResult {
  score: number;
  id: string;
  text: string; // 사진 설명
}

interface InfoResult {
  score: number;
  id: string;
  text: string; // 정보 텍스트
}

interface Message {
  id: string;
  text: string; // 사용자 입력 또는 봇의 주 답변/요약
  sender: 'user' | 'bot';
  timestamp: Date;
  query_type?: 'photo' | 'info' | 'ambiguous'; // API로부터 받은 봇 메시지용
  answer?: string; // API로부터 받은 'info' 또는 'ambiguous' 타입의 봇 메시지용
  photo_results?: PhotoResult[]; // 봇 메시지용
  info_results?: InfoResult[]; // 봇 메시지용
}

const CAT_ICON = require('../assets/cat.png'); // 🐈 아바타 이미지 경로

export default function ChatScreen() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const flatListRef = useRef<FlatList<Message>>(null);
  const headerHeight = useHeaderHeight(); // 네비게이터 헤더 높이 가져오기

  /* -------------------- 메시지 전송 -------------------- */
  const handleSend = useCallback(async () => {
    const trimmedInput = inputText.trim();
    if (!trimmedInput) return;

    // 1. 사용자 메시지 즉시 표시
    const newUserMsg: Message = {
      id: `${Date.now()}_user`,
      text: trimmedInput,
      sender: 'user',
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, newUserMsg]);
    setIsLoading(true);
    setError(null);
    setInputText(''); // 입력창 비우기

    // 2. 검색 API 호출
    try {
      const formData = new URLSearchParams();
      formData.append('user_id', 'dajeong'); // 예시 user_id, 필요시 동적으로 변경
      formData.append('query', trimmedInput);

      // axios를 사용하여 API 호출
      // const response = await axios.post('https://10.0.2.2:8090/rag/search', formData, {
      const response = await axios.post(
        'http://k12e201.p.ssafy.io:8090/rag/search/',
        formData.toString(),
        {
          headers: {
            // axios는 URLSearchParams를 보낼 때 자동으로 Content-Type을 설정하지만,
            // 명시적으로 지정하는 것이 좋을 수 있습니다.
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        },
      );

      // axios는 응답 데이터를 response.data에 담아줍니다.
      // HTTP 상태 코드가 2xx 범위가 아니면 자동으로 에러를 throw 합니다.
      const apiResponse = response.data;

      // 3. 봇 응답 메시지 포맷팅
      let botMessageText = '';
      // apiResponse가 객체인지, 그리고 query_type 속성이 있는지 확인
      if (
        typeof apiResponse !== 'object' ||
        apiResponse === null ||
        !apiResponse.query_type
      ) {
        console.error('잘못된 API 응답 형식:', apiResponse);
        throw new Error('서버로부터 유효한 응답을 받지 못했습니다.');
      }

      if (
        apiResponse.query_type === 'info' ||
        apiResponse.query_type === 'ambiguous'
      ) {
        botMessageText = apiResponse.answer || '정보를 찾았습니다.';
      } else if (apiResponse.query_type === 'photo') {
        botMessageText = '사진 검색 결과입니다.';
      } else {
        botMessageText = '검색 결과를 확인해주세요.'; // 기본 메시지
      }

      const botResponseMessage: Message = {
        id: `${Date.now()}_bot`,
        text: botMessageText,
        sender: 'bot',
        timestamp: new Date(),
        query_type: apiResponse.query_type,
        answer: apiResponse.answer, // API의 answer 필드
        photo_results: apiResponse.photo_results,
        info_results: apiResponse.info_results,
      };
      setMessages(prev => [...prev, botResponseMessage]);
    } catch (e: any) {
      console.error('메시지 전송 또는 응답 수신 실패:', e);
      if (axios.isAxiosError(e)) {
        // Axios 에러인 경우 더 자세한 정보 로깅 가능
        console.error(
          'Axios error details:',
          e.response?.data,
          e.response?.status,
          e.config,
        );
        setError(
          e.response?.data?.message ||
            e.message ||
            '서버 통신 중 오류가 발생했습니다.',
        );
      } else {
        setError(
          e.message ||
            '검색 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
        );
      }
      // 선택적으로 채팅에 오류 메시지 추가
      // const errorBotMsg: Message = {
      //   id: `${Date.now()}_bot_error`,
      //   text: "오류가 발생하여 답변을 가져올 수 없습니다.",
      //   sender: "bot",
      //   timestamp: new Date(),
      // };
      // setMessages(prev => [...prev, errorBotMsg]);
    } finally {
      setIsLoading(false);
    }
  }, [inputText]); // inputText에 의존

  /* -------------------- 자동 스크롤 -------------------- */
  useEffect(() => {
    if (flatListRef.current) {
      flatListRef.current.scrollToEnd({animated: true});
    }
  }, [messages]);

  /* -------------------- 메시지 렌더러 -------------------- */
  const renderMessage = ({item}: {item: Message}) => {
    const isUser = item.sender === 'user';
    return (
      <View style={[styles.row, isUser ? styles.rowUser : styles.rowBot]}>
        {!isUser && (
          <Image source={CAT_ICON} style={styles.avatar} resizeMode="contain" />
        )}

        <View
          style={[
            styles.bubble,
            isUser ? styles.bubbleUser : styles.bubbleBot,
          ]}>
          <Text style={styles.bubbleText}>{item.text}</Text>

          {/* 사진 검색 결과 (봇 전용) */}
          {item.sender === 'bot' &&
            item.photo_results &&
            item.photo_results.length > 0 && (
              <View style={styles.grid}>
                {item.photo_results.map(photo => (
                  <View key={photo.id} style={styles.gridItem}>
                    <Text style={styles.gridItemText} numberOfLines={3}>
                      {photo.text}
                    </Text>
                    <Text style={styles.resultScoreText}>
                      유사도: {photo.score.toFixed(2)}
                    </Text>
                  </View>
                ))}
              </View>
            )}

          {/* 정보 검색 결과 (봇 전용) */}
          {item.sender === 'bot' &&
            item.info_results &&
            item.info_results.length > 0 && (
              <View style={styles.infoResultsContainer}>
                {/* 'ambiguous' 타입이고, item.text (주 답변)과 item.answer가 다를 경우,
                  또는 'info' 타입에서 item.text가 이미 item.answer를 포함하지 않을 경우
                  item.answer를 별도로 표시할 수 있습니다.
                  현재는 item.text가 주 답변을 포함한다고 가정합니다. */}
                {/* <Text style={styles.infoResultsTitle}>관련 정보:</Text> */}
                {item.info_results.map(info => (
                  <View key={info.id} style={styles.infoResultItem}>
                    <Text style={styles.infoResultText}>{info.text}</Text>
                    <Text style={styles.resultScoreText}>
                      (유사도: {info.score.toFixed(2)})
                    </Text>
                  </View>
                ))}
              </View>
            )}

          <Text style={styles.time}>
            {item.timestamp.toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </Text>
        </View>
      </View>
    );
  };

  /* -------------------- UI -------------------- */
  return (
    <SafeAreaView style={styles.safe}>
      {/* 📌 상단 헤더 */}
      <View style={styles.header}>
        <Text style={styles.title}>캐릭터 이름</Text>
        <View style={styles.headerBtns}>
          <TouchableOpacity>
            <MaterialCommunityIcons name="archive-outline" size={24} />
          </TouchableOpacity>
          <TouchableOpacity style={{marginLeft: 12}}>
            <MaterialCommunityIcons name="cog-outline" size={24} />
          </TouchableOpacity>
        </View>
      </View>

      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={headerHeight} // 네비게이터 헤더 높이만큼 오프셋
      >
        <FlatList
          ref={flatListRef}
          data={messages}
          keyExtractor={m => m.id}
          renderItem={renderMessage}
          contentContainerStyle={{paddingHorizontal: 12, paddingBottom: 12}}
          showsVerticalScrollIndicator={false}
        />

        {isLoading && <Text style={styles.loading}>응답을 기다리는 중…</Text>}
        {error && <Text style={styles.error}>{error}</Text>}

        {/* 입력창 */}
        <View style={styles.inputBar}>
          <TextInput
            style={styles.input}
            placeholder="메시지를 입력하세요…"
            value={inputText}
            onChangeText={setInputText}
            onSubmitEditing={handleSend}
            editable={!isLoading}
          />
          <TouchableOpacity
            style={styles.sendBtn}
            onPress={handleSend}
            disabled={isLoading}>
            <MaterialCommunityIcons name="send" size={20} color="#fff" />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

/* -------------------- 스타일 -------------------- */
const HEADER_BG = '#FFEBD6';
const USER_BG = '#FFF0B4';

const styles = StyleSheet.create({
  safe: {flex: 1, backgroundColor: HEADER_BG},
  flex: {flex: 1},

  /* 헤더 */
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: HEADER_BG,
  },
  title: {fontSize: 16, fontWeight: '600'},
  headerBtns: {flexDirection: 'row', alignItems: 'center'},

  /* 채팅 영역 */
  row: {flexDirection: 'row', marginVertical: 4},
  rowBot: {alignItems: 'flex-start'},
  rowUser: {justifyContent: 'flex-end'}, // 사용자 메시지 행을 오른쪽으로 정렬
  avatar: {width: 32, height: 32, marginRight: 6},

  bubble: {
    maxWidth: '78%',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 12,
  },
  bubbleUser: {
    alignSelf: 'flex-end',
    backgroundColor: USER_BG,
    borderBottomRightRadius: 0,
  },
  bubbleBot: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#E0E0E0',
    borderBottomLeftRadius: 0,
  },
  bubbleText: {fontSize: 15, lineHeight: 20},

  time: {
    fontSize: 10,
    color: '#999',
    alignSelf: 'flex-end',
    marginTop: 4,
  },

  /* 이미지 그리드 (3×2) */
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 8,
  },
  gridItem: {
    width: '48%', // 2열 그리드, 약간의 간격 포함
    aspectRatio: 1.2, // 아이템 비율 (너비 대비 높이)
    backgroundColor: '#DDD',
    margin: 2,
    borderRadius: 6,
    padding: 8,
    justifyContent: 'space-between', // 텍스트와 점수를 양 끝으로
  },
  gridItemText: {
    fontSize: 12,
    lineHeight: 16,
  },

  /* 입력 바 */
  inputBar: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 10,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderColor: '#DDD',
  },
  input: {
    flex: 1,
    height: 42,
    paddingHorizontal: 14,
    backgroundColor: '#F9F9F9',
    borderRadius: 20,
    fontSize: 15,
  },
  sendBtn: {
    backgroundColor: '#FF8E25',
    width: 42,
    height: 42,
    borderRadius: 21,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 8,
  },

  /* 기타 */
  loading: {textAlign: 'center', color: '#777', paddingVertical: 4},
  error: {textAlign: 'center', color: 'red', paddingVertical: 4},

  /* 검색 결과 공통 스타일 */
  resultScoreText: {
    fontSize: 10,
    color: '#555',
    textAlign: 'right',
    marginTop: 4,
  },

  /* 정보 검색 결과 스타일 */
  infoResultsContainer: {
    marginTop: 10,
    paddingTop: 8,
    borderTopWidth: 1,
    borderColor: '#EEE',
  },
  infoResultItem: {
    backgroundColor: '#f7f7f7',
    padding: 10,
    borderRadius: 6,
    marginBottom: 6,
  },
  infoResultText: {fontSize: 13, lineHeight: 18, color: '#333'},
});
