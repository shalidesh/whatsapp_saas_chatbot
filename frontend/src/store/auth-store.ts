import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User, Business } from '@/types';
import { apiClient } from '@/lib/api-client';

interface AuthState {
  user: User | null;
  businesses: Business[];
  selectedBusiness: Business | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  setUser: (user: User | null) => void;
  setBusinesses: (businesses: Business[]) => void;
  setSelectedBusiness: (business: Business | null) => void;
  login: (email: string, password: string) => Promise<void>;
  register: (data: {
    email: string;
    password: string;
    first_name: string;
    last_name: string;
    phone: string;
    business_name: string;
  }) => Promise<void>;
  logout: () => void;
  verifyAuth: () => Promise<boolean>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      businesses: [],
      selectedBusiness: null,
      isAuthenticated: false,
      isLoading: false,

      setUser: (user) => set({ user, isAuthenticated: !!user }),

      setBusinesses: (businesses) => {
        set({ businesses });
        if (businesses.length > 0 && !get().selectedBusiness) {
          set({ selectedBusiness: businesses[0] });
        }
      },

      setSelectedBusiness: (business) => set({ selectedBusiness: business }),

      login: async (email, password) => {
        set({ isLoading: true });
        try {
          const response = await apiClient.login({ email, password });
          apiClient.setToken(response.token);
          set({
            user: response.user,
            businesses: response.businesses || [],
            selectedBusiness: response.businesses?.[0] || null,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      register: async (data) => {
        set({ isLoading: true });
        try {
          const response = await apiClient.register(data);
          apiClient.setToken(response.token);
          set({
            user: response.user,
            businesses: response.business ? [response.business] : [],
            selectedBusiness: response.business || null,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      logout: () => {
        apiClient.removeToken();
        set({
          user: null,
          businesses: [],
          selectedBusiness: null,
          isAuthenticated: false,
        });
      },

      verifyAuth: async () => {
        const token = apiClient['getToken']();
        if (!token) {
          set({ isAuthenticated: false, user: null });
          return false;
        }

        try {
          const response = await apiClient.verifyToken();
          if (response.valid) {
            set({ user: response.user, isAuthenticated: true });
            return true;
          }
          return false;
        } catch (error) {
          set({ isAuthenticated: false, user: null });
          return false;
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        businesses: state.businesses,
        selectedBusiness: state.selectedBusiness,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
