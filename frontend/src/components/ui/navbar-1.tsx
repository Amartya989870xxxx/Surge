"use client" 

import * as React from "react"
import { useState } from "react"
import { motion, AnimatePresence } from "motion/react"
import { Menu, X } from "lucide-react"

export interface NavItem {
  label: string;
  href?: string;
  onClick?: (e: React.MouseEvent) => void;
}

export interface Navbar1Props {
  items?: (string | NavItem)[];
  onGetStarted?: () => void;
  ctaText?: string;
  onSignUp?: () => void;
  signUpText?: string;
  userProfile?: {
    display_name?: string | null;
    picture_url?: string | null;
    email?: string | null;
  } | null;
  onWorkspaceClick?: () => void;
}

const defaultItems: (string | NavItem)[] = [
  { label: "WorkSpace", href: "/dashboard" },
  { label: "FAQ", href: "#faq" },
  { label: "Docs", href: "#docs" },
]

const Navbar1: React.FC<Navbar1Props> = ({
  items = defaultItems,
  onGetStarted,
  ctaText = "Log In",
  onSignUp,
  signUpText = "Sign Up",
  userProfile = null,
  onWorkspaceClick,
}) => {
  const [isOpen, setIsOpen] = useState(false)

  const toggleMenu = () => setIsOpen(!isOpen)

  const normalizedItems: NavItem[] = items.map((item) =>
    typeof item === "string"
      ? {
          label: item,
          href: item.toLowerCase() === "workspace" ? "/dashboard" : `#${item.toLowerCase()}`,
        }
      : item
  )

  const handleCtaClick = (e: React.MouseEvent) => {
    if (onGetStarted) {
      e.preventDefault()
      onGetStarted()
    }
  }

  const handleSignUpClick = (e: React.MouseEvent) => {
    if (onSignUp) {
      e.preventDefault()
      onSignUp()
    }
  }

  const handleWorkspaceAction = (e: React.MouseEvent) => {
    e.preventDefault()
    if (onWorkspaceClick) {
      onWorkspaceClick()
    } else {
      window.location.hash = '#/dashboard'
    }
  }

  return (
    <div className="flex justify-center w-full py-6 px-4">
      <div className="flex items-center justify-between px-6 py-3 bg-white rounded-full shadow-lg w-full max-w-3xl relative z-10">
        <div className="flex items-center">
          <motion.div
            className="w-8 h-8 mr-6 cursor-pointer flex items-center justify-center rounded-full overflow-hidden bg-[#021117] ring-1 ring-black/10 shadow-sm"
            initial={{ scale: 0.8 }}
            animate={{ scale: 1 }}
            whileHover={{ scale: 1.08 }}
            transition={{ duration: 0.3 }}
            onClick={onWorkspaceClick || (() => { window.location.hash = '#/dashboard'; })}
          >
            <video
              autoPlay
              loop
              muted
              playsInline
              poster="/favicon.png"
              className="w-full h-full object-cover rounded-full pointer-events-none"
              aria-label="Surge Agent"
            >
              <source src="/agent_avatar.webm" type="video/webm" />
              <source src="/agent_avatar.mp4" type="video/mp4" />
              <img
                src="/favicon.png"
                alt="Surge Agent"
                className="w-full h-full object-cover"
              />
            </video>
          </motion.div>
        </div>
        
        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center space-x-8">
          {normalizedItems.map((item) => (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              whileHover={{ scale: 1.05 }}
            >
              <a
                href={item.href || "#"}
                onClick={(e) => {
                  if (item.onClick) {
                    item.onClick(e)
                  }
                }}
                className="text-sm text-gray-900 hover:text-gray-600 transition-colors font-medium"
              >
                {item.label}
              </a>
            </motion.div>
          ))}
        </nav>

        {/* Desktop CTA Buttons */}
        <motion.div
          className="hidden md:flex items-center gap-2"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3, delay: 0.2 }}
        >
          {userProfile ? (
            <div className="flex items-center">
              <a
                href="#/dashboard"
                onClick={handleWorkspaceAction}
                className="inline-flex items-center justify-center px-4 py-2 text-xs text-white bg-black rounded-full hover:bg-gray-800 transition-colors cursor-pointer font-medium shadow-sm"
              >
                Workspace →
              </a>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <a
                href="#"
                onClick={handleCtaClick}
                className="inline-flex items-center justify-center px-4 py-2 text-xs text-gray-800 hover:text-black hover:bg-gray-100 rounded-full transition-colors cursor-pointer font-semibold"
              >
                {ctaText}
              </a>
              {onSignUp && (
                <a
                  href="#"
                  onClick={handleSignUpClick}
                  className="inline-flex items-center justify-center px-4 py-2 text-xs text-white bg-black rounded-full hover:bg-gray-800 transition-colors cursor-pointer font-semibold shadow-sm"
                >
                  {signUpText}
                </a>
              )}
            </div>
          )}
        </motion.div>

        {/* Mobile Menu Button */}
        <motion.button className="md:hidden flex items-center cursor-pointer" onClick={toggleMenu} whileTap={{ scale: 0.9 }}>
          <Menu className="h-6 w-6 text-gray-900" />
        </motion.button>
      </div>

      {/* Mobile Menu Overlay */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            className="fixed inset-0 bg-white z-50 pt-24 px-6 md:hidden"
            initial={{ opacity: 0, x: "100%" }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
          >
            <motion.button
              className="absolute top-6 right-6 p-2 cursor-pointer"
              onClick={toggleMenu}
              whileTap={{ scale: 0.9 }}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
            >
              <X className="h-6 w-6 text-gray-900" />
            </motion.button>
            <div className="flex flex-col space-y-6">
              {normalizedItems.map((item, i) => (
                <motion.div
                  key={item.label}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.1 + 0.1 }}
                  exit={{ opacity: 0, x: 20 }}
                >
                  <a
                    href={item.href || "#"}
                    className="text-base text-gray-900 font-medium"
                    onClick={(e) => {
                      if (item.onClick) {
                        item.onClick(e)
                      }
                      toggleMenu()
                    }}
                  >
                    {item.label}
                  </a>
                </motion.div>
              ))}

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                exit={{ opacity: 0, y: 20 }}
                className="pt-6 space-y-3"
              >
                {userProfile ? (
                  <a
                    href="#/dashboard"
                    className="inline-flex items-center justify-center w-full px-5 py-3 text-base text-white bg-black rounded-full hover:bg-gray-800 transition-colors cursor-pointer font-medium"
                    onClick={(e) => {
                      handleWorkspaceAction(e)
                      toggleMenu()
                    }}
                  >
                    Go to Workspace →
                  </a>
                ) : (
                  <>
                    <a
                      href="#"
                      className="inline-flex items-center justify-center w-full px-5 py-3 text-base text-white bg-black rounded-full hover:bg-gray-800 transition-colors cursor-pointer font-medium"
                      onClick={(e) => {
                        handleCtaClick(e)
                        toggleMenu()
                      }}
                    >
                      {ctaText}
                    </a>
                    {onSignUp && (
                      <a
                        href="#"
                        className="inline-flex items-center justify-center w-full px-5 py-3 text-base text-gray-900 bg-gray-100 rounded-full hover:bg-gray-200 transition-colors cursor-pointer font-medium"
                        onClick={(e) => {
                          handleSignUpClick(e)
                          toggleMenu()
                        }}
                      >
                        {signUpText}
                      </a>
                    )}
                  </>
                )}
              </motion.div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export { Navbar1 }
