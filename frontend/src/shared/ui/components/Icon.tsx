import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

const base = (size: number, strokeWidth: number): SVGProps<SVGSVGElement> => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
});

export function ChevronLeftIcon({ size = 22, ...p }: IconProps) {
  return (
    <svg {...base(size, 2.25)} {...p}>
      <path d="m15 18-6-6 6-6" />
    </svg>
  );
}

export function CheckIcon({ size = 16, ...p }: IconProps) {
  return (
    <svg {...base(size, 3)} {...p}>
      <path d="m5 12 4.5 4.5L19 7" />
    </svg>
  );
}

export function SunIcon({ size = 20, ...p }: IconProps) {
  return (
    <svg {...base(size, 2)} {...p}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
    </svg>
  );
}

export function MoonIcon({ size = 20, ...p }: IconProps) {
  return (
    <svg {...base(size, 2)} {...p}>
      <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z" />
    </svg>
  );
}

export function PhoneIcon({ size = 14, ...p }: IconProps) {
  return (
    <svg {...base(size, 2.5)} {...p}>
      <rect x="6" y="2" width="12" height="20" rx="3" />
      <path d="M11 18h2" />
    </svg>
  );
}
