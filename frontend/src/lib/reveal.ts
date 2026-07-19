import { useRef, RefObject } from "react";
import { gsap } from "gsap";
import { useGSAP } from "@gsap/react";

gsap.registerPlugin(useGSAP);

/**
 * Standard page reveal — header fade/slide + staggered content.
 * Matches the dashboard motion language. Reduced-motion safe.
 * Mark elements with `data-reveal` (staggered) and `data-reveal-head` (leads).
 */
export function usePageReveal<T extends HTMLElement = HTMLDivElement>(
  deps: unknown[] = []
): RefObject<T | null> {
  const scope = useRef<T>(null);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add("(prefers-reduced-motion: no-preference)", () => {
        const tl = gsap.timeline({ defaults: { ease: "power2.out" } });
        if (scope.current?.querySelector("[data-reveal-head]")) {
          tl.fromTo(
            "[data-reveal-head]", 
            { opacity: 0, y: 16 }, 
            { opacity: 1, y: 0, duration: 0.5, clearProps: "all" }
          );
        }
        if (scope.current?.querySelector("[data-reveal]")) {
          tl.fromTo(
            "[data-reveal]",
            { opacity: 0, y: 20 },
            { opacity: 1, y: 0, duration: 0.5, stagger: 0.08, clearProps: "all" },
            "-=0.2"
          );
        }
      });
      return () => mm.revert();
    },
    { scope, dependencies: deps }
  );

  return scope;
}

/**
 * Stagger a set of rows whenever their identity changes (e.g. live data).
 * Mark rows with the given selector (default `[data-row]`).
 */
export function useRowStagger<T extends HTMLElement = HTMLDivElement>(
  key: string | undefined,
  selector = "[data-row]"
): RefObject<T | null> {
  const scope = useRef<T>(null);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add("(prefers-reduced-motion: no-preference)", () => {
        gsap.fromTo(
          selector,
          { opacity: 0, x: -8 },
          {
            opacity: 1,
            x: 0,
            duration: 0.4,
            stagger: 0.04,
            ease: "power1.out",
            clearProps: "all"
          }
        );
      });
      return () => mm.revert();
    },
    { scope, dependencies: [key] }
  );

  return scope;
}
