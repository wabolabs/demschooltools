import { useState, useCallback, useContext } from 'react';
import { SnackbarContext } from '../contexts';
import { useCustodiaApi } from './useCustodiaApi';

export function useSwipeLogic() {
  const [swipeState, setSwipeState] = useState({ student: null, missingDirection: null, missingTime: '' });
  const { swipeStudent } = useCustodiaApi();
  const { setSnackbar } = useContext(SnackbarContext);

  const validateSignDirection = useCallback((student, direction) => {
    if (direction === 'in' && student.last_swipe_type === 'in' && student.in_today) {
      setSwipeState({ student, missingDirection: 'out', missingTime: '' });
    } else if (direction === 'out' && student.last_swipe_type === 'out' && student.in_today) {
      setSwipeState({ student, missingDirection: 'in', missingTime: '' });
    } else {
      doSwipe(student, direction);
    }
  }, []);

  const doSwipe = useCallback(async (student, direction, overrideTime) => {
    try {
      await swipeStudent(student, direction, overrideTime);
      if (!overrideTime) {
        setSnackbar({ message: `${student.name} swiped successfully!`, severity: 'success' });
      }
    } catch (e) {
      setSnackbar({ message: `Swipe failed: ${e.message}`, severity: 'error' });
    }
    setSwipeState({ student: null, missingDirection: null, missingTime: '' });
  }, [swipeStudent, setSnackbar]);

  const handleSwipeComplete = useCallback(async () => {
    await doSwipe(swipeState.student, swipeState.missingDirection, swipeState.missingTime);
  }, [doSwipe, swipeState]);

  const handleSwipeCancel = useCallback(() => {
    setSwipeState({ student: null, missingDirection: null, missingTime: '' });
  }, []);

  const updateMissingTime = useCallback((time) => {
    setSwipeState(prev => ({ ...prev, missingTime: time }));
  }, []);

  return { swipeState, validateSignDirection, handleSwipeComplete, handleSwipeCancel, updateMissingTime };
}
