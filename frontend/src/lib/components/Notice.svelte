<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    tone?: 'info' | 'warning' | 'error' | 'success';
    title?: string;
    children: Snippet;
    id?: string;
  }

  let { tone = 'info', title, children, id }: Props = $props();

  const tones = {
    info: 'border-border bg-nav text-ink',
    warning: 'border-warning/30 bg-warning/5 text-ink',
    error: 'border-expense/40 bg-expense/5 text-ink',
    success: 'border-income/30 bg-income/5 text-ink'
  };
</script>

<div
  {id}
  role={tone === 'error' ? 'alert' : 'status'}
  tabindex="-1"
  class={['rounded-lg border px-2 py-1.5 text-sm outline-none', tones[tone]]}
>
  {#if title}<p class="font-medium">{title}</p>{/if}
  <div class={[title && 'mt-0.5', 'text-muted']}>{@render children()}</div>
</div>
