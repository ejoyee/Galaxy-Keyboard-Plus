import {Button, View} from 'react-native';

import AppNavigator from './navigation/AppNavigator';
import React from 'react';
import {useUserStore} from './stores/useUserStore';

export default function App() {
  // const userId = useUserStore(state => state.userId);

  return (
    <View style={{flex: 1}}>
      <AppNavigator />
    </View>
  );
}
