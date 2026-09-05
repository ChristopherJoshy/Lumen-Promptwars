import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-full px-6 text-base font-semibold transition-colors duration-200 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary: "bg-primary text-white hover:bg-primary-deep",
        outline: "border border-line bg-white text-ink hover:border-primary hover:text-primary",
        quiet: "text-primary hover:bg-signal/10",
      },
    },
    defaultVariants: { variant: "primary" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export function Button({ className, variant, ...props }: ButtonProps) {
  return <button className={cn(buttonVariants({ variant }), className)} {...props} />;
}
