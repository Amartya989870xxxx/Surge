import React from 'react';
import { Navbar1 } from '../ui/navbar-1';

interface LandingNavProps {
  onOpenApp: () => void;
  onOpenSignIn?: () => void;
  onOpenSignUp?: () => void;
  onOpenWorkspace?: () => void;
  userProfile?: {
    display_name?: string | null;
    picture_url?: string | null;
    email?: string | null;
  } | null;
}

export const LandingNav: React.FC<LandingNavProps> = ({
  onOpenApp,
  onOpenSignIn,
  onOpenSignUp,
  onOpenWorkspace,
  userProfile,
}) => {
  const navItems = [
    {
      label: "WorkSpace",
      href: "/dashboard",
      onClick: (e: React.MouseEvent) => {
        e.preventDefault();
        if (onOpenWorkspace) {
          onOpenWorkspace();
        } else {
          window.location.hash = '#/dashboard';
        }
      },
    },
    {
      label: "FAQ",
      href: "#faq",
      onClick: (e: React.MouseEvent) => {
        e.preventDefault();
        const element = document.getElementById("faq");
        if (element) {
          element.scrollIntoView({ behavior: "smooth", block: "start" });
          window.history.pushState(null, "", "#faq");
        } else {
          window.location.hash = "faq";
        }
      },
    },
    { label: "Docs", href: "#docs" },
  ];

  return (
    <header className="fixed top-0 left-0 right-0 z-50 flex justify-center pointer-events-none">
      <div className="w-full flex justify-center pointer-events-auto">
        <Navbar1
          items={navItems}
          onGetStarted={onOpenSignIn || onOpenApp}
          ctaText="Log In"
          onSignUp={onOpenSignUp || onOpenApp}
          signUpText="Sign Up"
          userProfile={userProfile}
          onWorkspaceClick={onOpenWorkspace}
        />
      </div>
    </header>
  );
};
