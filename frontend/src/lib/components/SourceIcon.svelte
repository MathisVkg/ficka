<script lang="ts">
  import type { EntrySource } from '#lib/types.js';

  let { source }: { source: EntrySource } = $props();

  const labels: Record<EntrySource, string> = {
    manual: 'Entered by hand',
    recurring: 'From a recurring template',
    document: 'From a document',
    bank: 'From a bank statement'
  };
</script>

<svg
  role="img"
  aria-label={labels[source]}
  viewBox="0 0 16 16"
  class="size-2 shrink-0 text-muted/70"
  fill="none"
  stroke="currentColor"
  stroke-width="1.4"
  stroke-linecap="round"
  stroke-linejoin="round"
>
  <title>{labels[source]}</title>
  {#if source === 'recurring'}
    <path d="M3 6.5A5 5 0 0 1 12.2 4M13 9.5A5 5 0 0 1 3.8 12" />
    <path d="M12.5 1.5V4.3H9.7M3.5 14.5v-2.8h2.8" />
  {:else if source === 'document'}
    <path d="M4 1.5h5.5L12.5 4.5v10h-8.5z" /><path d="M9.5 1.5v3h3M6 8h4.5M6 10.5h4.5" />
  {:else if source === 'bank'}
    <path d="M2 6.5 8 2.5l6 4M3 6.5h10M4 6.5v6M7 6.5v6M9 6.5v6M12 6.5v6M2.5 13.5h11" />
  {:else}
    <path d="M10.5 2.5l3 3-8 8H2.5v-3z" /><path d="M9 4l3 3" />
  {/if}
</svg>
