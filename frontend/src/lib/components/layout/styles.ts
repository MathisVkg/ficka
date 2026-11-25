/**
 * Shared control styles: one height (44px), one border, one radius, one focus ring.
 * Every input, select trigger, combobox, date input and button uses these, so form rows
 * line up on every page. Change the look here, not in the pages.
 */

/** Text inputs, date inputs, the combobox input and the select trigger. */
export const controlClass =
  'h-[44px] w-full min-w-0 rounded-md border border-border bg-surface px-1.5 text-base text-ink ' +
  'transition-colors duration-150 ease-out placeholder:text-muted ' +
  'focus:border-accent focus:outline-2 focus:outline-offset-1 focus:outline-accent ' +
  'aria-invalid:border-expense disabled:bg-bg disabled:text-muted';

/** Checkboxes: one accent focus ring (no browser ring on top of it). */
export const checkboxClass =
  'size-2.5 shrink-0 cursor-pointer accent-(--color-accent) outline-none ' +
  'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent';

/** The one label style. Labels never wrap. */
export const labelClass = 'block truncate text-sm font-medium text-ink';

export const hintClass = 'text-xs text-muted';
export const errorClass = 'text-sm text-expense';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'danger-solid';

const variants: Record<ButtonVariant, string> = {
  primary: 'bg-accent text-white hover:bg-accent-hover',
  secondary: 'border border-border bg-surface text-ink hover:bg-nav',
  ghost: 'text-muted hover:bg-nav hover:text-ink',
  danger: 'border border-expense/50 bg-surface text-expense hover:bg-expense/10',
  'danger-solid': 'bg-expense text-white hover:bg-expense/90'
};

/** Buttons and links that look like buttons. */
export function buttonClass(variant: ButtonVariant = 'primary'): string {
  return (
    'inline-flex h-[44px] shrink-0 items-center justify-center gap-1 rounded-md px-2.5 text-sm ' +
    'font-medium whitespace-nowrap transition-colors duration-150 ease-out ' +
    'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ' +
    'disabled:cursor-not-allowed disabled:opacity-60 ' +
    variants[variant]
  );
}
