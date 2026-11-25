<script lang="ts">
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';

  interface Props {
    message: string;
    /** Optional link in the toast, e.g. "View entry" (pass a resolve()d href). */
    link?: { href: string; label: string } | null;
    onclose?: () => void;
  }

  let { message, link = null, onclose }: Props = $props();

  let visible = $state(true);

  onMount(() => {
    const timer = setTimeout(
      () => {
        visible = false;
        onclose?.();
      },
      link ? 6000 : 3500
    );
    return () => clearTimeout(timer);
  });
</script>

{#if visible}
  <div
    role="status"
    aria-live="polite"
    transition:fade={{ duration: 200 }}
    class="fixed right-2 bottom-2 z-50 flex items-center gap-2 rounded-lg border border-border bg-ink px-2 py-1.5 text-sm font-medium text-white shadow-[0_8px_24px_rgba(29,30,32,0.16)]"
  >
    <span>{message}</span>
    {#if link}
      <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- callers pass resolve()d hrefs -->
      <a href={link.href} class="underline underline-offset-2 hover:no-underline">{link.label}</a>
    {/if}
  </div>
{/if}
