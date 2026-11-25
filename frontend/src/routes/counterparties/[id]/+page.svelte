<script lang="ts">
  import { replaceState } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import Amount from '#lib/components/Amount.svelte';
  import Button from '#lib/components/Button.svelte';
  import ConfirmDialog from '#lib/components/ConfirmDialog.svelte';
  import CounterpartyForm from '#lib/components/CounterpartyForm.svelte';
  import Notice from '#lib/components/Notice.svelte';
  import Toast from '#lib/components/Toast.svelte';
  import { ROLE_LABELS, type CounterpartyFormValues } from '#lib/types.js';
  import type { PageProps } from './$types';

  let { data, form }: PageProps = $props();

  const cp = $derived(data.counterparty);
  const stats = $derived(cp.stats);
  const saved = $derived(page.url.searchParams.get('saved') === '1');
  let deleteOpen = $state(false);

  type Result = {
    values?: CounterpartyFormValues;
    errors?: Record<string, string>;
    message?: string | null;
    deleteMessage?: string;
  };
  const result = $derived((form ?? null) as Result | null);

  const values = $derived(
    result?.values ?? {
      name: cp.name,
      role: cp.role,
      vat_number: cp.vat_number ?? '',
      ibans: cp.ibans,
      default_category_id: cp.default_category_id ? String(cp.default_category_id) : '',
      default_vat_rate_bp: cp.default_vat_rate_bp === null ? '' : String(cp.default_vat_rate_bp),
      notes: cp.notes ?? ''
    }
  );

  function dismissSaved() {
    void replaceState(resolve('/counterparties/[id]', { id: String(cp.id) }), page.state);
  }
</script>

<svelte:head>
  <title>{cp.name} · Ficka</title>
</svelte:head>

{#if saved}<Toast message="Saved" onclose={dismissSaved} />{/if}

<div class="flex flex-col gap-3">
  <header class="flex flex-wrap items-start justify-between gap-2">
    <div>
      <a href={resolve('/counterparties')} class="text-sm text-muted hover:text-ink">
        ← Counterparties
      </a>
      <h1 class="mt-0.5 text-3xl font-semibold tracking-tight">{cp.name}</h1>
      <p class="mt-0.5 text-sm text-muted">{ROLE_LABELS[cp.role]}</p>
    </div>
    <Button
      type="button"
      variant="ghost"
      class="border border-border hover:text-expense"
      onclick={() => (deleteOpen = true)}
    >
      Delete
    </Button>
  </header>

  {#if result?.deleteMessage}<Notice tone="error">{result.deleteMessage}</Notice>{/if}

  <!-- Form on the left, statistics on the right on wide screens. -->
  <div class="grid grid-cols-1 items-start gap-3 lg:grid-cols-[minmax(0,1fr)_360px]">
    <div class="min-w-0 lg:order-1">
      {#key form}
        <CounterpartyForm
          {values}
          categories={data.categories}
          rates={data.rates}
          errors={result?.errors ?? {}}
          message={result?.message ?? null}
          action="?/save"
        />
      {/key}
    </div>
    <div class="lg:sticky lg:top-4 lg:order-2">
      <section
        aria-label="Statistics"
        class="grid grid-cols-2 gap-1.5 rounded-xl border border-border bg-surface p-2 md:grid-cols-4 md:p-3 lg:grid-cols-2"
      >
        <div>
          <p class="text-xs text-muted">Entries</p>
          <p class="mt-0.5 text-lg font-semibold amount">{stats.entries_count}</p>
        </div>
        <div>
          <p class="text-xs text-muted">Income</p>
          <p class="mt-0.5 text-lg font-semibold">
            <Amount cents={stats.income_total_cents} direction="income" />
          </p>
        </div>
        <div>
          <p class="text-xs text-muted">Expenses</p>
          <p class="mt-0.5 text-lg font-semibold">
            <Amount cents={stats.expense_total_cents} direction="expense" />
          </p>
        </div>
        <div>
          <p class="text-xs text-muted">Open balance</p>
          <p class="mt-0.5 text-lg font-semibold">
            {#if stats.open_balance_cents === 0}<span class="text-muted">—</span>{:else}
              <Amount
                cents={Math.abs(stats.open_balance_cents)}
                direction={stats.open_balance_cents > 0 ? 'income' : 'expense'}
              />
            {/if}
          </p>
        </div>
        <p class="col-span-2 text-xs text-muted md:col-span-4 lg:col-span-2">
          Confirmed entries, amounts incl. VAT.
          <a
            href={resolve(`/entries?counterparty_id=${cp.id}`)}
            class="font-medium text-accent hover:underline"
          >
            View entries
          </a>
        </p>
      </section>
    </div>
  </div>
</div>

<ConfirmDialog bind:open={deleteOpen} title="Delete {cp.name}?">
  {#snippet description()}
    {#if data.linkedEntries > 0}
      {data.linkedEntries}
      {data.linkedEntries === 1 ? 'entry keeps' : 'entries keep'} their amounts and dates but will no
      longer be linked to a counterparty.
    {:else}
      No entries are linked to this counterparty.
    {/if}
    This can’t be undone.
  {/snippet}
  {#snippet action()}
    <form method="POST" action="?/delete">
      <button
        type="submit"
        class="inline-flex min-h-[44px] items-center rounded-md bg-expense px-2.5 text-sm font-medium text-white hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        Delete counterparty
      </button>
    </form>
  {/snippet}
</ConfirmDialog>
