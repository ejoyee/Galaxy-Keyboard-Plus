import React, {useEffect} from 'react';
import {View, Text, Button, StyleSheet} from 'react-native';
import {requestStoragePermission} from '../utils/permissions';
// useNavigation과 함께 NavigationProp 타입을 임포트합니다.
import {useNavigation, NavigationProp} from '@react-navigation/native';

// 앱 전체의 네비게이션 파라미터 목록을 정의합니다.
// 이 타입은 보통 앱의 네비게이션 설정을 담당하는 파일 (예: App.tsx 또는 navigators/index.ts)에 위치시키고,
// 각 화면에서 임포트하여 사용하는 것이 좋습니다.
export type RootStackParamList = {
  HomeScreen: undefined; // HomeScreen은 파라미터를 받지 않습니다.
  ChatScreen: undefined; // ChatScreen은 파라미터를 받지 않습니다. (파라미터가 있다면 { userId: string } 와 같이 정의)
  // 다른 화면들과 해당 화면이 받는 파라미터 타입을 여기에 추가합니다.
};

export default function HomeScreen() {
  const navigation = useNavigation<NavigationProp<RootStackParamList>>();

  useEffect(() => {
    requestStoragePermission();
  }, []);

  const goToChatScreen = () => {
    navigation.navigate('ChatScreen');
    // 만약 ChatScreen으로 파라미터를 전달해야 한다면:
    // navigation.navigate('ChatScreen', { userId: '123' }); // RootStackParamList에 맞게 정의 필요
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>홈 화면입니다</Text>
      <Button
        title="백업 테스트"
        onPress={() => console.log('백업 버튼 클릭')}
      />
      <Button title="채팅방으로 이동하기" onPress={goToChatScreen}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  title: {
    fontSize: 24,
    marginBottom: 16,
  },
});
