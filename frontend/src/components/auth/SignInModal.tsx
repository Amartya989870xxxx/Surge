import React, { useState } from 'react';
import { signInWithGoogle, signInWithEmail, signUpWithEmail } from '../../lib/auth/firebase';
import { getProfile, type ProfileOut } from '../../lib/api/auth';
import { SignInPage } from '../ui/sign-in';

interface SignInModalProps {
  isOpen: boolean;
  initialMode?: 'signin' | 'signup';
  onClose: () => void;
  onSuccess: (profile: ProfileOut, isSignUp?: boolean) => void;
  onDemoMode: () => void;
}

export const SignInModal: React.FC<SignInModalProps> = ({
  isOpen,
  initialMode = 'signin',
  onClose,
  onSuccess,
  onDemoMode,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleGoogleSignIn = async () => {
    setLoading(true);
    setError(null);
    try {
      await signInWithGoogle();
      // Fetch user profile from backend (which auto-creates/loads the User row using Firebase UID)
      const profile = await getProfile();
      try {
        localStorage.setItem('surge_cached_profile', JSON.stringify(profile));
      } catch {}
      // Brand new sign-up only if the modal was opened in sign-up mode AND onboarding was never completed
      const isSignUp = initialMode === 'signup' && !profile.onboarding_completed;
      onSuccess(profile, isSignUp);
      onClose();
    } catch (err: any) {
      console.error('Sign-in error:', err);
      setError(
        err.message?.includes('popup-closed-by-user')
          ? 'Sign-in popup was closed before completing.'
          : err.message || 'Failed to sign in with Google'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleFormSignIn = async (
    event: React.FormEvent<HTMLFormElement>,
    isSignUp: boolean,
    rememberMe: boolean
  ) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    const formData = new FormData(event.currentTarget);
    const email = (formData.get('email') as string)?.trim();
    const password = formData.get('password') as string;

    if (!email || !password) {
      setError('Please provide both email and password.');
      setLoading(false);
      return;
    }

    try {
      if (isSignUp) {
        await signUpWithEmail(email, password);
      } else {
        await signInWithEmail(email, password);
      }

      // Remember only the email for autofill convenience. Firebase's own browserLocalPersistence
      // (see lib/auth/firebase.ts) already keeps the user signed in securely - it never needs the
      // raw password. Storing the actual password in localStorage would put it in plaintext,
      // readable by any script that can run on the page (e.g. via XSS), with no protection at all.
      try {
        if (rememberMe) {
          localStorage.setItem('surge_remembered_email', email);
        } else {
          localStorage.removeItem('surge_remembered_email');
        }
      } catch {}

      const profile = await getProfile();
      try {
        localStorage.setItem('surge_cached_profile', JSON.stringify(profile));
      } catch {}
      onSuccess(profile);
      onClose();
    } catch (err: any) {
      console.error('Email auth error:', err);
      let message = err.message || 'Authentication failed.';

      if (err.code === 'auth/operation-not-allowed') {
        message = 'Email & Password sign-in is not yet enabled in your Firebase Console. Enable it at: https://console.firebase.google.com/project/surge-72250/authentication/providers';
      } else if (err.code === 'auth/email-already-in-use') {
        message = 'An account with this email already exists. Click "Log In" below to sign in.';
      } else if (
        err.code === 'auth/invalid-credential' ||
        err.code === 'auth/user-not-found' ||
        err.code === 'auth/wrong-password'
      ) {
        message = 'Invalid email or password. If you are new here, click "Create your account" below.';
      } else if (err.code === 'auth/weak-password') {
        message = 'Password must be at least 6 characters.';
      } else if (err.code === 'auth/invalid-email') {
        message = 'Please enter a valid email address.';
      }

      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 md:p-6 bg-black/80 backdrop-blur-md overflow-y-auto"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <SignInPage
        isModal
        initialMode={initialMode}
        brandName="Surge"
        title={<span className="font-light text-white tracking-tight">{initialMode === 'signup' ? "Create your account" : "Welcome Back"}</span>}
        description="Surge uses Google Firebase Authentication. Your sessions, personal investigation history, and connector credentials will be tied securely to your account."
        onClose={onClose}
        onGoogleSignIn={handleGoogleSignIn}
        onSignIn={handleFormSignIn}
        onDemoMode={() => {
          onClose();
          onDemoMode();
        }}
        loading={loading}
        error={error}
        quote={{
          text: "Surge proved root cause across Google Sheets and GitHub in 8 seconds, and verified provider state without human delay.",
          author: "Ali Hassan",
        }}
      />
    </div>
  );
};
