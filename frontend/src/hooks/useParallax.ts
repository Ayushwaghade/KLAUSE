import { useEffect, useRef } from 'react';

export function useParallax() {
  const mouseRef = useRef({ x: 0, y: 0, targetX: 0, targetY: 0 });
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      // Normalize coordinate offsets to range [-0.5, 0.5] relative to center
      const nx = (e.clientX / window.innerWidth) - 0.5;
      const ny = (e.clientY / window.innerHeight) - 0.5;
      
      mouseRef.current.targetX = nx;
      mouseRef.current.targetY = ny;
    };

    const updateParallax = () => {
      const mouse = mouseRef.current;
      
      // Buttery smooth linear interpolation (LERP) factor of 0.08
      mouse.x += (mouse.targetX - mouse.x) * 0.08;
      mouse.y += (mouse.targetY - mouse.y) * 0.08;
      
      // Update global CSS variables on the document element
      document.documentElement.style.setProperty('--mouse-x', mouse.x.toFixed(4));
      document.documentElement.style.setProperty('--mouse-y', mouse.y.toFixed(4));

      rafRef.current = requestAnimationFrame(updateParallax);
    };

    window.addEventListener('mousemove', handleMouseMove);
    rafRef.current = requestAnimationFrame(updateParallax);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, []);
}
