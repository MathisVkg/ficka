<script lang="ts">
  import { enhance } from '$app/forms';
  import { replaceState } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import Amount from '#lib/components/Amount.svelte';
  import Button from '#lib/components/Button.svelte';
  import ConfirmDialog from '#lib/components/ConfirmDialog.svelte';
  import Notice from '#lib/components/Notice.svelte';
  import PaymentBadge from '#lib/components/PaymentBadge.svelte';
  import SourceIcon from '#lib/components/SourceIcon.svelte';
  import TextField from '#lib/components/TextField.svelte';
  import Toast from '#lib/components/Toast.svelte';
  import EntryForm from '#lib/components/entry/EntryForm.svelte';
  import Page from '#lib/components/layout/Page.svelte';
  import PageHeader from '#lib/components/layout/PageHeader.svelte';
  import type { ResolvedPathname } from '$app/types';
  import { todayIso } from '#lib/dates.js';
  import { centsToInput, formatCents, formatDate } from '#lib/money.js';
  import type { PageProps } from './$types';

  let { data, form }: PageProps = $props();

  const entry = $derived(data.entry);
  const title = $derived(
    entry.counterparty?.name ??
      entry.description ??
      (entry.direction === 'income' ? 'Income' : 'Expense')
  );
  const toast = $derived(
    page.url.searchParams.get('saved') === '1'
      ? 'Saved'
      : page.url.searchParams.get('marked') === '1'
        ? 'Marked as paid'
        : null
  );
  let deleteOpen = $state(false);
  // `from` is validated on the server (same-site relative path, /entries otherwise).
  const from = $derived(data.from as ResolvedPathname);
  /** Action URLs keep `from`, so redirects after the action still know the way back. */
  const actionUrl = (name: string) => `?from=${encodeURIComponent(data.from)}&/${name}`;

  type FormResult = {
    action?: string;
    errors?: Record<string, string>;
    message?: string | null;
    payment?: { errors: Record<string, string>; values: Record<string, string> };
    paymentAdded?: boolean;
  };
  const result = $derived((form ?? null) as FormResult | null);
  const saveErrors = $derived(result && !result.action ? (result.errors ?? {}) : {});
  const saveMessage = $derived(result && !result.action ? (result.message ?? null) : null);
  const paymentErrors = $derived(result?.payment?.errors ?? {});
  const paymentValues = $derived(result?.payment?.values);
  const actionMessage = $derived(result?.action && result.message ? result.message : null);

  function dismissToast() {
    const path = resolve('/entries/[id]', { id: String(entry.id) });
    void replaceState(
      `${path}?from=${encodeURIComponent(data.from)}` as ResolvedPathname,
      page.state
    );
  }
</script>

<svelte:head>
  <title>{title} · Ficka</title>
</svelte:head>

{#if toast}
  <Toast message={toast} onclose={dismissToast} />
{/if}

<Page>
  <PageHeader {title} back={{ href: from, label: 'Entries' }}>
    {#snippet meta()}
      <SourceIcon source={entry.source} />
      <span>{entry.direction === 'income' ? 'Income' : 'Expense'}</span>
      <span aria-hidden="true">·</span>
      <span class="amount">{formatDate(entry.invoice_date)}</span>
      {#if entry.invoice_number}
        <span aria-hidden="true">·</span><span>No. {entry.invoice_number}</span>
      {/if}
      <span aria-hidden="true">·</span>
      <Amount cents={entry.total_gross_cents} direction={entry.direction} class="font-medium" />
      <PaymentBadge status={entry.payment_status} />
      {#if entry.status === 'proposed'}
        <span class="rounded-full bg-accent/10 px-1 text-xs font-medium text-accent">
          Proposed
        </span>
      {/if}
    {/snippet}
    {#snippet actions()}
      {#if entry.remaining_cents > 0}
        <form method="POST" action={actionUrl('markPaid')} use:enhance>
          <Button variant="secondary">Mark as paid</Button>
        </form>
      {/if}
      {#if entry.status === 'proposed'}
        <form method="POST" action={actionUrl('confirm')} use:enhance>
          <Button>Confirm</Button>
        </form>
      {/if}
    {/snippet}
  </PageHeader>

  <div class="flex flex-col gap-3">
    {#if actionMessage}
      <Notice tone="error">{actionMessage}</Notice>
    {/if}

    {#if entry.warnings.length > 0}
      <Notice tone="warning" title="Worth a look">
        <ul class="list-disc pl-2">
          {#each entry.warnings as warning (warning.code)}<li>{warning.message}</li>{/each}
        </ul>
      </Notice>
    {/if}

    {#key entry.updated_at + entry.paid_cents}
      <EntryForm
        {entry}
        categories={data.categories}
        rates={data.rates}
        serverErrors={saveErrors}
        serverMessage={saveMessage}
        action={actionUrl('save')}
        cancelHref={from}
        ondelete={() => (deleteOpen = true)}
      >
        {#snippet details()}
          {#if entry.payments.length > 1 || (entry.paid_cents > 0 && entry.remaining_cents > 0)}
            {@render payments()}
          {/if}
        {/snippet}
      </EntryForm>
    {/key}
  </div>
</Page>

{#snippet payments()}
  <section aria-labelledby="payments-heading" class="border-t border-border pt-3">
    <div class="flex flex-wrap items-center justify-between gap-1">
      <h2 id="payments-heading" class="text-base font-semibold">Payments</h2>
      <div class="flex items-center gap-1 text-sm">
        <PaymentBadge status={entry.payment_status} />
        <span class="text-muted">
          Paid <span class="amount">{formatCents(entry.paid_cents)}</span> of
          <span class="amount">{formatCents(entry.total_gross_cents)}</span>
        </span>
      </div>
    </div>

    <ul class="mt-2 divide-y divide-border rounded-lg border border-border">
      {#each entry.payments as payment (payment.id)}
        <li class="flex flex-wrap items-center justify-between gap-1 px-1.5 py-1">
          <span class="flex flex-wrap items-center gap-1.5 text-sm">
            <span class="amount">{formatDate(payment.paid_on)}</span>
            <span class="font-medium amount">{formatCents(payment.amount_cents)}</span>
            {#if payment.note}<span class="text-muted">{payment.note}</span>{/if}
            {#if payment.source !== 'manual'}
              <span class="text-xs text-muted">({payment.source})</span>
            {/if}
          </span>
          <form method="POST" action={actionUrl('deletePayment')} use:enhance>
            <input type="hidden" name="payment_id" value={payment.id} />
            <Button
              variant="danger"
              aria-label="Delete the payment of {formatCents(payment.amount_cents)} on {formatDate(
                payment.paid_on
              )}"
            >
              Delete
            </Button>
          </form>
        </li>
      {/each}
    </ul>

    {#if entry.remaining_cents > 0}
      <form
        method="POST"
        action={actionUrl('addPayment')}
        use:enhance={() =>
          async ({ update }) => {
            await update({ reset: false });
          }}
        class="mt-2 grid grid-cols-1 items-start gap-1.5 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,2fr)_auto]"
      >
        <TextField
          label="Paid on"
          name="paid_on"
          id="payment-paid-on"
          type="date"
          required
          value={paymentValues?.paid_on ?? todayIso()}
          error={paymentErrors.paid_on}
        />
        <TextField
          label="Amount"
          name="amount"
          id="payment-amount"
          inputmode="decimal"
          required
          class="amount"
          value={paymentValues?.amount ?? centsToInput(entry.remaining_cents)}
          error={paymentErrors.amount_cents}
        />
        <TextField
          label="Note"
          name="note"
          id="payment-note"
          maxlength={500}
          value={paymentValues?.note ?? ''}
        />
        <div class="sm:pt-[26px]">
          <Button variant="secondary">Add payment</Button>
        </div>
      </form>
      {#if paymentErrors.form}<p class="mt-1 text-sm text-expense">{paymentErrors.form}</p>{/if}
    {/if}
  </section>
{/snippet}

<ConfirmDialog bind:open={deleteOpen} title="Delete this entry?">
  {#snippet description()}
    {entry.direction === 'income' ? 'Income' : 'Expense'} “{title}” of {formatCents(
      entry.total_gross_cents
    )} on {formatDate(entry.invoice_date)}, with its lines and payments, will be deleted. This can’t
    be undone.
  {/snippet}
  {#snippet action()}
    <form method="POST" action={actionUrl('delete')}>
      <input type="hidden" name="from" value={data.from} />
      <Button variant="danger-solid">Delete entry</Button>
    </form>
  {/snippet}
</ConfirmDialog>
