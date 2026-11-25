<script lang="ts">
  import type { HTMLInputAttributes } from 'svelte/elements';
  import Field from '#lib/components/layout/Field.svelte';
  import { controlClass } from '#lib/components/layout/styles.js';

  interface Props extends HTMLInputAttributes {
    label: string;
    name: string;
    /** Error shown under the field (also marks the input invalid for assistive tech). */
    error?: string | null;
    hint?: string;
    hideLabel?: boolean;
  }

  let {
    label,
    name,
    error = null,
    hint,
    hideLabel = false,
    id,
    class: extra,
    ...rest
  }: Props = $props();

  const inputId = $derived(id ?? `field-${name}`);
</script>

<Field {label} for={inputId} {hint} {error} {hideLabel}>
  <input
    id={inputId}
    {name}
    aria-invalid={error ? 'true' : undefined}
    aria-describedby={error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined}
    class={[controlClass, extra]}
    {...rest}
  />
</Field>
