import React, {useEffect} from 'react';
import {View, Text, Button, StyleSheet} from 'react-native';
import {requestStoragePermission} from '../utils/permissions';

export default function HomeScreen() {
  useEffect(() => {
    requestStoragePermission();
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>홈 화면입니다</Text>
      <Button
        title="백업 테스트"
        onPress={() => console.log('백업 버튼 클릭')}
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
