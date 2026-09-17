import { useEffect, useState, type RefObject } from 'react';

export function useScrollProgress(containerRef?: RefObject<HTMLElement | null>): number {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      if (containerRef && containerRef.current) {
        const el = containerRef.current;
        const rect = el.getBoundingClientRect();
        const totalHeight = el.offsetHeight - window.innerHeight;
        if (totalHeight <= 0) {
          setProgress(0);
          return;
        }
        const current = -rect.top;
        const p = Math.max(0, Math.min(1, current / totalHeight));
        setProgress(p);
      } else {
        const totalHeight = document.documentElement.scrollHeight - window.innerHeight;
        if (totalHeight <= 0) {
          setProgress(0);
          return;
        }
        const p = Math.max(0, Math.min(1, window.scrollY / totalHeight));
        setProgress(p);
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    window.addEventListener('resize', handleScroll, { passive: true });
    handleScroll();

    return () => {
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('resize', handleScroll);
    };
  }, [containerRef]);

  return progress;
}
