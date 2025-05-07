import {Button, View} from 'react-native';

import AppNavigator from './navigation/AppNavigator';
import React from 'react';
import {useAutoBackup} from './hooks/useAutoBackup';
import {useUserStore} from './stores/useUserStore';

export default function App() {
  // const userId = useUserStore(state => state.userId);
  // const {backupNow} = useAutoBackup(userId); // ✅ 훅은 항상 컴포넌트 최상단에서 호출

  return (
    <View style={{flex: 1}}>
      <AppNavigator />
      {/* <Button title="수동 백업 테스트" onPress={backupNow} /> */}
    </View>
  );
}
