import { useState } from "react";
import { SignInPage, type Testimonial } from "@/components/ui/sign-in";
import { Navbar1 } from "@/components/ui/navbar-1";
import { AnimatedJobCard, type JobCardProps } from "@/components/ui/animated-card";
import { cn } from "@/lib/utils";

// --- SVG ICONS FOR DEMO ---
export const SlackIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 2447.6 2452.5">
    <g clipRule="evenodd" fillRule="evenodd">
      <path d="m897.4 0c-135.3.1-244.8 109.9-244.7 245.2-.1 135.3 109.5 245.1 244.8 245.2h244.8v-245.1c.1-135.3-109.5-245.1-244.9-245.3.1 0 .1 0 0 0m0 654h-652.6c-135.3.1-244.9 109.9-244.8 245.2-.2 135.3 109.4 245.1 244.7 245.3h652.7c135.3-.1 244.9-109.9 244.8-245.2.1-135.4-109.5-245.2-244.8-245.3z" fill="#36c5f0"/>
      <path d="m2447.6 899.2c.1-135.3-109.5-245.1-244.8-245.2-135.3.1-244.9 109.9-244.8 245.2v245.3h244.8c135.3-.1 244.9-109.9 244.8-245.3zm-652.7 0v-654c.1-135.2-109.4-245-244.7-245.2-135.3.1-244.9 109.9-244.8 245.2v654c-.2 135.3 109.4 245.1 244.7 245.3 135.3-.1 244.9-109.9 244.8-245.3z" fill="#2eb67d"/>
      <path d="m1550.1 2452.5c135.3-.1 244.9-109.9 244.8-245.2.1-135.3-109.5-245.1-244.8-245.2h-244.8v245.2c-.1 135.2 109.5 245 244.8 245.2zm0-654.1h652.7c135.3-.1 244.9-109.9 244.8-245.2.2-135.3-109.4-245.1-244.7-245.3h-652.7c-135.3.1-244.9 109.9-244.8 245.2-.1 135.4 109.4 245.2 244.7 245.3z" fill="#ecb22e"/>
      <path d="m0 1553.2c-.1 135.3 109.5 245.1 244.8 245.2 135.3-.1 244.9-109.9 244.8-245.2v-245.2h-244.8c-135.3.1-244.9 109.9-244.8 245.2zm652.7 0v654c-.2 135.3 109.4 245.1 244.7 245.3 135.3-.1 244.9-109.9 244.8-245.2v-653.9c.2-135.3-109.4-245.1-244.7-245.3-135.4 0-244.9 109.8-244.8 245.1 0 0 0 .1 0 0" fill="#e01e5a"/>
    </g>
  </svg>
);

export const GoogleIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 256 262" preserveAspectRatio="xMidYMid">
    <path d="M255.878 133.451c0-10.734-.871-18.567-2.756-26.69H130.55v48.448h71.947c-1.45 12.04-9.283 30.172-26.69 42.356l-.244 1.622 38.755 30.023 2.685.268c24.659-22.774 38.875-56.282 38.875-96.027" fill="#4285F4"/>
    <path d="M130.55 261.1c35.248 0 64.839-11.605 86.453-31.622l-41.196-31.913c-11.024 7.688-25.82 13.055-45.257 13.055-34.523 0-63.824-22.773-74.269-54.25l-1.531.13-40.298 31.187-.527 1.465C35.393 231.798 79.49 261.1 130.55 261.1" fill="#34A853"/>
    <path d="M56.281 156.37c-2.756-8.123-4.351-16.827-4.351-25.82 0-8.994 1.595-17.697 4.206-25.82l-.073-1.73L15.26 71.312l-1.335.635C5.077 89.644 0 109.517 0 130.55s5.077 40.905 13.925 58.602l42.356-32.782" fill="#FBBC05"/>
    <path d="M130.55 50.479c24.514 0 41.05 10.589 50.479 19.438l36.844-35.974C195.245 12.91 165.798 0 130.55 0 79.49 0 35.393 29.301 13.925 71.947l42.211 32.783c10.59-31.477 39.891-54.251 74.414-54.251" fill="#EB4335"/>
  </svg>
);

const initialJobs: JobCardProps[] = [
  {
    companyLogo: <SlackIcon />,
    companyName: "Slack",
    jobTitle: "Senior UI Designer",
    salary: "$3,500-5,500 net",
    tags: ["Project Based", "Remote"],
    postedDate: "Posted 2 Day Ago",
    variant: "pink",
  },
  {
    companyLogo: <GoogleIcon />,
    companyName: "Google",
    jobTitle: "Lead UX Designer",
    salary: "$4,000-6,000 net",
    tags: ["Full Time", "B2B"],
    postedDate: "Posted Yesterday",
    variant: "yellow",
  },
  {
    companyLogo: <SlackIcon />,
    companyName: "Slack",
    jobTitle: "Lead Product Designer",
    salary: "$3,500-5,500 net",
    tags: ["Full Time", "Remote"],
    postedDate: "Posted 2 Day Ago",
    variant: "blue",
  },
];

export function AnimatedJobCardDemo() {
  const [cards, setCards] = useState(initialJobs);

  const cardTransforms = [
    "rotate-[-8deg] translate-x-[-30%] translate-y-[10%] z-0",
    "rotate-[0deg] translate-y-[-5%] z-20",
    "rotate-[8deg] translate-x-[30%] translate-y-[10%] z-10",
  ];

  const handleCardClick = (index: number) => {
    if (index === 1) return;
    const newCards = [...cards];
    const clickedCard = newCards.splice(index, 1)[0];
    newCards.splice(1, 0, clickedCard);
    setCards(newCards);
  };

  return (
    <div className="relative flex h-[500px] w-full items-center justify-center bg-[#050507]">
      <div className="relative h-full w-full max-w-4xl" style={{ perspective: "1000px" }}>
        {cards.map((job, index) => (
          <AnimatedJobCard
            key={job.jobTitle + job.companyName}
            {...job}
            onClick={() => handleCardClick(index)}
            className={cn(
              "absolute left-0 right-0 top-1/4 mx-auto",
              "w-96",
              cardTransforms[index]
            )}
          />
        ))}
      </div>
    </div>
  );
}

export const sampleTestimonials: Testimonial[] = [
  {
    avatarSrc: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop&q=80",
    name: "Sarah Chen",
    handle: "@sarahdigital",
    text: "Amazing platform! The user experience is seamless and the features are exactly what I needed."
  },
  {
    avatarSrc: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&auto=format&fit=crop&q=80",
    name: "Marcus Johnson",
    handle: "@marcustech",
    text: "This service has transformed how I work. Clean design, powerful features, and excellent support."
  },
  {
    avatarSrc: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&auto=format&fit=crop&q=80",
    name: "David Martinez",
    handle: "@davidcreates",
    text: "I've tried many platforms, but this one stands out. Intuitive, reliable, and genuinely helpful for productivity."
  },
];

export const SignInPageDemo = () => {
  return (
    <div className="bg-[#050507] text-white">
      <SignInPage testimonials={sampleTestimonials} />
    </div>
  );
};

export const Demo = () => {
  return (
    <>
      <Navbar1 />
    </>
  );
};

export { default as IntegrationsSectionDemo } from "@/components/ui/integrations-3";
export { default as DemoIntegrations } from "@/components/ui/integrations-02";
export { default as RuixenMoonChat, default as RuixenMoonChatDemo } from "@/components/ui/ruixen-moon-chat";

export default AnimatedJobCardDemo;
