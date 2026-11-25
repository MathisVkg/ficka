<script lang="ts">
  import type { Snippet } from 'svelte';
  import { errorClass, hintClass, labelClass } from '#lib/components/layout/styles.js';

  interface Props {
    label: string;
    /** The control's id (the label points to it). */
    for: string;
    hint?: string | null;
    /** Rich hint (e.g. live text); rendered instead of `hint`. */
    hintContent?: Snippet;
    error?: string | null;
    /** Visually hide the label (it stays for screen readers). */
    hideLabel?: boolean;
    /** Extra text after the label, e.g. a "Suggested" chip. */
    labelExtra?: Snippet;
    class?: string;
    children: Snippet;
  }

  let {
    label,
    for: controlId,
    hint = null,
    hintContent,
    error = null,
    hideLabel = false,
    labelExtra,
    class: extra,
    children
  }: Props = $props();
</script>

<!-- Label, control, then hint or error. Top-aligned, so rows line up in a FormGrid. -->
<div class={['flex min-w-0 flex-col gap-0.5', extra]}>
  <div class={['flex min-h-[20px] items-center gap-1', hideLabel && 'sr-only']}>
    <label for={controlId} class={labelClass}>{label}</label>
    {#if labelExtra}{@render labelExtra()}{/if}
  </div>
  {@render children()}
  {#if error}
    <p id="{controlId}-error" class={errorClass}>{error}</p>
  {:else if hintContent}
    <div id="{controlId}-hint" class={hintClass}>{@render hintContent()}</div>
  {:else if hint}
    <p id="{controlId}-hint" class={hintClass}>{hint}</p>
  {/if}
</div>
