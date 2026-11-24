<script lang="ts">
  import type { HTMLInputAttributes } from 'svelte/elements';

  interface Props extends HTMLInputAttributes {
    label: string;
    name: string;
    /** Error shown under the field (also marks the input invalid for assistive tech). */
    error?: string | null;
    hint?: string;
  }

  let { label, name, error = null, hint, id, ...rest }: Props = $props();

  const inputId = $derived(id ?? `field-${name}`);
  const describedBy = $derived(
    [hint ? `${inputId}-hint` : null, error ? `${inputId}-error` : null]
      .filter(Boolean)
      .join(' ') || undefined
  );
</script>

<div class="flex flex-col gap-0.5">
  <label for={inputId} class="text-sm font-medium text-ink">{label}</label>
  <input
    id={inputId}
    {name}
    aria-invalid={error ? 'true' : undefined}
    aria-describedby={describedBy}
    class="min-h-[44px] w-full rounded-md border border-border bg-surface px-1.5 text-base text-ink transition-colors duration-150 ease-out placeholder:text-muted focus:border-accent focus:outline-2 focus:outline-offset-1 focus:outline-accent aria-invalid:border-expense"
    {...rest}
  />
  {#if hint}
    <p id="{inputId}-hint" class="text-xs text-muted">{hint}</p>
  {/if}
  {#if error}
    <p id="{inputId}-error" class="text-sm text-expense">{error}</p>
  {/if}
</div>
