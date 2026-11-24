<script lang="ts">
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';

  let { message, onclose }: { message: string; onclose?: () => void } = $props();

  let visible = $state(true);

  onMount(() => {
    const timer = setTimeout(() => {
      visible = false;
      onclose?.();
    }, 3500);
    return () => clearTimeout(timer);
  });
</script>

{#if visible}
  <div
    role="status"
    aria-live="polite"
    transition:fade={{ duration: 200 }}
    class="fixed right-2 bottom-2 z-50 rounded-lg border border-border bg-ink px-2 py-1.5 text-sm font-medium text-white shadow-[0_8px_24px_rgba(29,30,32,0.16)]"
  >
    {message}
  </div>
{/if}
