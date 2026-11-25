<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    /** Most columns at full width: 1 / 2 / 3 / 4, stepping up with the window width. */
    columns?: 1 | 2 | 3 | 4;
    class?: string;
    children: Snippet;
  }

  let { columns = 4, class: extra, children }: Props = $props();

  // Static class strings, so Tailwind sees them.
  const grids = {
    1: 'grid-cols-1',
    2: 'grid-cols-1 sm:grid-cols-2',
    3: 'grid-cols-1 sm:grid-cols-2 xl:grid-cols-3',
    4: 'grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4'
  } as const;
</script>

<!-- 16px row and column gaps; fields are top-aligned so labels and controls line up. -->
<div class={['grid items-start gap-2', grids[columns], extra]}>
  {@render children()}
</div>
