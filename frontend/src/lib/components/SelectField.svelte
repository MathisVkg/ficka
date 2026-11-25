<script lang="ts">
  import { Select } from 'bits-ui';
  import type { Snippet } from 'svelte';
  import Field from '#lib/components/layout/Field.svelte';
  import { controlClass } from '#lib/components/layout/styles.js';

  interface Item {
    value: string;
    label: string;
    disabled?: boolean;
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
    hint?: string | null;
    /** Visually hide the label (it stays available to screen readers). */
    hideLabel?: boolean;
    disabled?: boolean;
    labelExtra?: Snippet;
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
    hint = null,
    hideLabel = false,
    disabled = false,
    labelExtra,
    class: extra,
    onchange
  }: Props = $props();

  const triggerId = $derived(id ?? `select-${name ?? label.toLowerCase().replace(/\W+/g, '-')}`);
  const selected = $derived(items.find((item) => item.value === value));
</script>

<Field {label} for={triggerId} {error} {hint} {hideLabel} {labelExtra} class={extra}>
  <Select.Root
    type="single"
    bind:value
    {items}
    {name}
    {disabled}
    onValueChange={(next: string) => onchange?.(next)}
  >
    <!-- Looks exactly like a text input: same height, border, radius, padding, focus ring. -->
    <Select.Trigger
      id={triggerId}
      aria-invalid={error ? 'true' : undefined}
      aria-describedby={error ? `${triggerId}-error` : hint ? `${triggerId}-hint` : undefined}
      class={[
        controlClass,
        'flex items-center justify-between gap-1 text-left focus-visible:border-accent focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent'
      ]}
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
            disabled={item.disabled}
            class="flex h-[40px] cursor-pointer items-center justify-between gap-2 rounded-md px-1.5 text-sm text-ink outline-none data-disabled:cursor-not-allowed data-disabled:opacity-50 data-highlighted:bg-nav"
          >
            {#snippet children({ selected: isSelected })}
              <span class="truncate">{item.label}</span>
              <span aria-hidden="true" class={['text-accent', !isSelected && 'invisible']}>✓</span>
            {/snippet}
          </Select.Item>
        {/each}
      </Select.Content>
    </Select.Portal>
  </Select.Root>
</Field>
