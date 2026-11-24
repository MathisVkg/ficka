<script lang="ts">
  import { Select } from 'bits-ui';

  interface Item {
    value: string;
    label: string;
  }

  interface Props {
    label: string;
    items: Item[];
    value?: string;
    /** Submitted with the form (bits-ui renders a hidden input). */
    name?: string;
    id?: string;
    placeholder?: string;
    error?: string | null;
    /** Visually hide the label (it stays available to screen readers). */
    hideLabel?: boolean;
    disabled?: boolean;
    class?: string;
    onchange?: (value: string) => void;
  }

  let {
    label,
    items,
    value = $bindable(''),
    name,
    id,
    placeholder = 'Choose…',
    error = null,
    hideLabel = false,
    disabled = false,
    class: extra,
    onchange
  }: Props = $props();

  const triggerId = $derived(id ?? `select-${name ?? label.toLowerCase().replace(/\W+/g, '-')}`);
  const selected = $derived(items.find((item) => item.value === value));
</script>

<div class={['flex flex-col gap-0.5', extra]}>
  <span id="{triggerId}-label" class={['text-sm font-medium text-ink', hideLabel && 'sr-only']}>
    {label}
  </span>
  <Select.Root
    type="single"
    bind:value
    {items}
    {name}
    {disabled}
    onValueChange={(next: string) => onchange?.(next)}
  >
    <Select.Trigger
      id={triggerId}
      aria-labelledby="{triggerId}-label {triggerId}"
      aria-invalid={error ? 'true' : undefined}
      aria-describedby={error ? `${triggerId}-error` : undefined}
      class="flex min-h-[44px] w-full items-center justify-between gap-1 rounded-md border border-border bg-surface px-1.5 text-left text-base text-ink transition-colors duration-150 ease-out focus-visible:border-accent focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent disabled:opacity-60 aria-invalid:border-expense"
    >
      <span class={['truncate', !selected && 'text-muted']}>{selected?.label ?? placeholder}</span>
      <svg aria-hidden="true" viewBox="0 0 16 16" class="size-2 shrink-0 text-muted">
        <path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.5" />
      </svg>
    </Select.Trigger>
    <Select.Portal>
      <Select.Content
        sideOffset={4}
        class="z-50 max-h-[320px] min-w-(--bits-select-anchor-width) overflow-y-auto rounded-lg border border-border bg-surface p-0.5 shadow-[0_8px_24px_rgba(29,30,32,0.08)]"
      >
        {#each items as item (item.value)}
          <Select.Item
            value={item.value}
            label={item.label}
            class="flex min-h-[40px] cursor-pointer items-center justify-between gap-2 rounded-md px-1.5 text-sm text-ink outline-none data-highlighted:bg-nav"
          >
            {#snippet children({ selected: isSelected })}
              <span>{item.label}</span>
              {#if isSelected}<span aria-hidden="true" class="text-accent">✓</span>{/if}
            {/snippet}
          </Select.Item>
        {/each}
      </Select.Content>
    </Select.Portal>
  </Select.Root>
  {#if error}
    <p id="{triggerId}-error" class="text-sm text-expense">{error}</p>
  {/if}
</div>
