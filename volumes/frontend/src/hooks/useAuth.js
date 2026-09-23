import { useContext } from 'react';
import { AuthContext } from '@/lib/authContext';

export function useAuth() {
  return useContext(AuthContext);
}
