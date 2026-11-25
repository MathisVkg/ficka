<script lang="ts">
  import type { Snippet } from 'svelte';
  import type { HTMLButtonAttributes } from 'svelte/elements';
  import { buttonClass, type ButtonVariant } from '#lib/components/layout/styles.js';

  interface Props extends HTMLButtonAttributes {
    /** primary, secondary (outline), ghost, danger (outline) or danger-solid (filled). */
    variant?: ButtonVariant;
    children: Snippet;
  }

  let { variant = 'primary', children, type = 'submit', class: extra, ...rest }: Props = $props();
</script>

<button {type} class={[buttonClass(variant), extra]} {...rest}>
  {@render children()}
</button>
