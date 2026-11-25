<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    title: string;
    /** Optional back link shown above the title (pass a resolve()d href). */
    back?: { href: string; label: string };
    /** Optional line under the title. */
    meta?: Snippet;
    /** Buttons on the right, vertically centered with the title. */
    actions?: Snippet;
  }

  let { title, back, meta, actions }: Props = $props();
</script>

<header class="mb-3 flex flex-col gap-0.5">
  {#if back}
    <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- callers pass resolve()d hrefs -->
    <a href={back.href} class="w-fit text-sm text-muted hover:text-ink">← {back.label}</a>
  {/if}
  <div class="flex min-h-[44px] flex-wrap items-center justify-between gap-x-2 gap-y-1">
    <h1 class="min-w-0 truncate text-3xl font-semibold tracking-tight">{title}</h1>
    {#if actions}
      <div class="flex flex-wrap items-center gap-1">{@render actions()}</div>
    {/if}
  </div>
  {#if meta}
    <div class="flex flex-wrap items-center gap-1 text-sm text-muted">{@render meta()}</div>
  {/if}
</header>
