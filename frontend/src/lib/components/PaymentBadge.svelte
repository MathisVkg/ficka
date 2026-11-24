<script lang="ts">
  import { PAYMENT_STATUS_LABELS, type PaymentStatus } from '#lib/types.js';

  let { status }: { status: PaymentStatus } = $props();

  const styles: Record<PaymentStatus, string> = {
    paid: 'bg-income/10 text-income',
    partial: 'bg-warning/10 text-warning',
    overdue: 'bg-expense/10 text-expense',
    unpaid: 'bg-nav text-muted'
  };
</script>

<span
  class={[
    'inline-flex items-center rounded-full px-1 py-0.5 text-xs font-medium whitespace-nowrap',
    styles[status]
  ]}
>
  {PAYMENT_STATUS_LABELS[status]}
</span>
