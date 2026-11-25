<script lang="ts">
  import type { Snippet } from 'svelte';

  /**
   * The content area next to the navigation: full width (no max-width, ever),
   * 32px padding on desktop and 16px below 768px.
   */
  let { children }: { children: Snippet } = $props();
</script>

<div class="flex w-full min-w-0 flex-col p-2 md:p-4">
  {@render children()}
</div>
