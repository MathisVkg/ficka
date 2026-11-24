<script lang="ts">
  import type { Snippet } from 'svelte';
  import type { HTMLButtonAttributes } from 'svelte/elements';

  interface Props extends HTMLButtonAttributes {
    variant?: 'primary' | 'ghost';
    children: Snippet;
  }

  let { variant = 'primary', children, type = 'submit', class: extra, ...rest }: Props = $props();
</script>

<button
  {type}
  class={[
    'inline-flex min-h-[44px] items-center justify-center rounded-md px-2.5 text-sm font-medium transition-colors duration-150 ease-out focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-60',
    variant === 'primary'
      ? 'bg-accent text-white hover:bg-accent-hover'
      : 'text-muted hover:bg-surface/60 hover:text-ink',
    extra
  ]}
  {...rest}
>
  {@render children()}
</button>
