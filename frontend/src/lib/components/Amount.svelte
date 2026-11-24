<script lang="ts">
  import { formatCents, formatSigned } from '#lib/money.js';
  import type { Direction } from '#lib/types.js';

  interface Props {
    cents: number;
    /** With a direction: "+" in the income color, or "−" for expenses. */
    direction?: Direction;
    class?: string;
  }

  let { cents, direction, class: extra }: Props = $props();
</script>

<span class={['whitespace-nowrap amount', direction === 'income' && 'text-income', extra]}>
  {direction ? formatSigned(cents, direction) : formatCents(cents)}
</span>
