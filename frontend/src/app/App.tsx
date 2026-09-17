import React, { useState, useEffect } from 'react';
import { LandingPage } from '../components/landing/LandingPage';
import { SignInModal } from '../components/auth/SignInModal';
import { PersonaAndGoalOnboarding } from '../components/onboarding/PersonaAndGoalOnboarding';
import { ConnectorsScreen } from '../components/connectors/ConnectorsScreen';
import { DashboardScreen } from '../components/dashboard/DashboardScreen';
import { AgentConsole } from '../components/investigation/AgentConsole';
import { FinalReport } from '../components/investigation/FinalReport';
import { EvaluationsPage } from '../components/workspace/EvaluationsPage';
import { ProfilePage } from '../components/profile/ProfilePage';
import { getProfile, type ProfileOut } from '../lib/api/auth';
import { onAuthChanged } from '../lib/auth/firebase';
import { listInvestigations, createInvestigation } from '../lib/api/investigations';
import { WorkspaceFaviconButton } from '../components/ui/WorkspaceFaviconButton';

import { signOutUser } from '../lib/auth/firebase';

export const App: React.FC = () => {
  const [currentRoute, setCurrentRoute] = useState<string>(() => {
    const hash = window.location.hash.replace(/^#/, '');
    const pathname = window.location.pathname;
    if (pathname.includes('/connectors') || hash.includes('/connectors')) {
      return '/connectors';
    }
    return hash || pathname || '/';
  });

  const [signInOpen, setSignInOpen] = useState(false);
  const [signInMode, setSignInMode] = useState<'signin' | 'signup'>('signin');
  const [userProfile, setUserProfile] = useState<ProfileOut | null>(() => {
    try {
      const cached = localStorage.getItem('surge_cached_profile');
      return cached ? JSON.parse(cached) : null;
    } catch {
      return null;
    }
  });
  const connectedCallbackApp = new URLSearchParams(window.location.search).get('connected');

  // Track Firebase auth state and sync with persistent local cache
  useEffect(() => {
    const unsubscribe = onAuthChanged(async (user) => {
      if (user) {
        try {
          const profile = await getProfile();
          setUserProfile(profile);
          try {
            localStorage.setItem('surge_cached_profile', JSON.stringify(profile));
          } catch {}
        } catch {
          // Ignore fetch error on sign-in
        }
      } else {
        setUserProfile(null);
        try {
          localStorage.removeItem('surge_cached_profile');
        } catch {}
      }
    });

    return () => unsubscribe();
  }, []);

  // Sync hash routing
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace(/^#/, '') || '/';
      setCurrentRoute(hash);
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const navigate = (path: string) => {
    window.location.hash = path;
    setCurrentRoute(path);
  };

  const handleOpenSignIn = (mode: 'signin' | 'signup' = 'signin') => {
    setSignInMode(mode);
    setSignInOpen(true);
  };

  const handleAuthSuccess = (profile: ProfileOut, isSignUp = false) => {
    setUserProfile(profile);
    try {
      localStorage.setItem('surge_cached_profile', JSON.stringify(profile));
    } catch {}

    // When a user is logging in (not signing up for the first time), or if onboarding is already completed:
    // Do not show the onboarding ("create now") page or the integration page again!
    // Send them directly to the main workspace/dashboard!
    if (!isSignUp || profile.onboarding_completed) {
      navigate('/dashboard');
    } else {
      // Only brand new first-time sign-ups proceed through setup
      navigate('/onboarding');
    }
  };

  const handleDemoMode = () => {
    navigate('/dashboard');
  };

  const handleSignOut = async () => {
    setUserProfile(null);
    try {
      localStorage.removeItem('surge_cached_profile');
    } catch {}
    await signOutUser();
    navigate('/');
  };

  const handleViewInvestigationSample = async (id?: string) => {
    if (id) {
      navigate(`/investigations/${id}?view=report`);
      return;
    }
    try {
      const list = await listInvestigations({ limit: 1 });
      if (list.items && list.items.length > 0) {
        navigate(`/investigations/${list.items[0].id}?view=report`);
      } else {
        // Launch a sample run
        const created = await createInvestigation({
          request: 'Investigate the conversion rate decline from Sep 12 14:00 UTC',
          scenario_id: 'checkout_regression_01',
        });
        navigate(`/investigations/${created.id}`);
      }
    } catch {
      navigate('/dashboard');
    }
  };

  // ==================== ROUTE RENDERING ====================

  // Screen 1: Landing Page
  if (currentRoute === '/' || currentRoute === '') {
    return (
      <>
        <LandingPage
          userProfile={userProfile}
          onOpenApp={() => handleOpenSignIn('signin')}
          onOpenSignIn={() => handleOpenSignIn('signin')}
          onOpenSignUp={() => handleOpenSignIn('signup')}
          onViewInvestigation={handleViewInvestigationSample}
          onViewReliability={() => navigate('/evaluations')}
          onNavigateWorkspace={() => navigate('/dashboard')}
        />
        <SignInModal
          isOpen={signInOpen}
          initialMode={signInMode}
          onClose={() => setSignInOpen(false)}
          onSuccess={handleAuthSuccess}
          onDemoMode={handleDemoMode}
        />
      </>
    );
  }

  // Screens 3 & 4: Persona and Goal Onboarding
  if (currentRoute === '/onboarding') {
    // If user already has an active onboarded profile, route straight to workspace
    if (userProfile?.onboarding_completed) {
      navigate('/dashboard');
      return null;
    }
    return (
      <PersonaAndGoalOnboarding
        initialProfile={userProfile}
        onComplete={() => navigate('/connectors')}
      />
    );
  }

  // Screen 5: Connect Apps
  if (currentRoute === '/connectors' || currentRoute.startsWith('/connectors')) {
    return (
      <ConnectorsScreen
        connectedCallbackApp={connectedCallbackApp}
        initialViewMode={userProfile?.onboarding_completed ? 'integrations' : undefined}
        onContinueToWorkspace={() => navigate('/dashboard')}
      />
    );
  }

  // Screen 6: Dashboard / Workspace (pitch black)
  if (currentRoute === '/dashboard' || currentRoute === '/app' || currentRoute === '/workspace') {
    return (
      <>
        <DashboardScreen
          onSelectInvestigation={(id, isTerminal) => {
            navigate(`/investigations/${id}${isTerminal ? '?view=report' : ''}`);
          }}
          onOpenConnectors={() => navigate('/connectors')}
          onOpenEvaluations={() => navigate('/evaluations')}
          onOpenProfile={() => navigate('/profile')}
          onSignOut={handleSignOut}
        />
        <SignInModal
          isOpen={signInOpen}
          initialMode={signInMode}
          onClose={() => setSignInOpen(false)}
          onSuccess={handleAuthSuccess}
          onDemoMode={handleDemoMode}
        />
      </>
    );
  }

  // Screen: Operator Profile Page
  if (currentRoute === '/profile' || currentRoute === '/app/profile') {
    return (
      <ProfilePage
        onBack={() => navigate('/dashboard')}
        onSignOut={handleSignOut}
        onManageConnectors={() => navigate('/connectors')}
      />
    );
  }

  // Screens 7 & 8: Investigation Routes (/investigations/:id or /app/investigations/:id)
  const isInvestigationRoute =
    currentRoute.startsWith('/investigations/') || currentRoute.startsWith('/app/investigations/');

  if (isInvestigationRoute) {
    const rawPath = currentRoute.replace('/app/investigations/', '').replace('/investigations/', '');
    const [invId, queryString] = rawPath.split('?');
    const query = new URLSearchParams(queryString || '');
    const isReportView = query.get('view') === 'report';

    if (isReportView) {
      return (
        <FinalReport
          investigationId={invId}
          onBackToDashboard={() => navigate('/dashboard')}
        />
      );
    }

    return (
      <AgentConsole
        investigationId={invId}
        onComplete={(id) => navigate(`/investigations/${id}?view=report`)}
        onBackToDashboard={() => navigate('/dashboard')}
      />
    );
  }

  // Evaluations / Reliability Suite Page
  if (currentRoute === '/evaluations' || currentRoute === '/app/evaluations') {
    return (
      <div className="min-h-screen bg-[#000000] text-[#F5F5F5] font-mono flex flex-col relative">
        <WorkspaceFaviconButton onNavigateWorkspace={() => navigate('/dashboard')} />
        <div className="flex-1 p-6 pt-16 max-w-6xl mx-auto w-full">
          <EvaluationsPage
            onOpenInvestigation={(id) => navigate(`/investigations/${id}?view=report`)}
          />
        </div>
      </div>
    );
  }

  // Fallback to Dashboard
  return (
    <DashboardScreen
      onSelectInvestigation={(id, isTerminal) => {
        navigate(`/investigations/${id}${isTerminal ? '?view=report' : ''}`);
      }}
      onOpenConnectors={() => navigate('/connectors')}
      onOpenEvaluations={() => navigate('/evaluations')}
      onSignOut={() => {
        setUserProfile(null);
        navigate('/');
      }}
    />
  );
};
