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
  import Card from '#lib/components/layout/Card.svelte';
  import Page from '#lib/components/layout/Page.svelte';
  import PageHeader from '#lib/components/layout/PageHeader.svelte';
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

<Page>
  <PageHeader title={cp.name} back={{ href: resolve('/counterparties'), label: 'Counterparties' }}>
    {#snippet meta()}{ROLE_LABELS[cp.role]}{/snippet}
    {#snippet actions()}
      <Button type="button" variant="danger" onclick={() => (deleteOpen = true)}>
        Delete counterparty
      </Button>
    {/snippet}
  </PageHeader>

  <div class="flex flex-col gap-3">
    {#if result?.deleteMessage}<Notice tone="error">{result.deleteMessage}</Notice>{/if}

    <!-- Form on the left, statistics on the right on wide screens. -->
    <div
      class="grid grid-cols-1 items-start gap-3 min-[1600px]:grid-cols-[minmax(0,1fr)_400px] lg:grid-cols-[minmax(0,1fr)_360px]"
    >
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
        <Card label="Statistics">
          <div class="grid grid-cols-2 gap-2 md:grid-cols-4 lg:grid-cols-2">
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
          </div>
        </Card>
      </div>
    </div>
  </div>
</Page>

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
      <Button variant="danger-solid">Delete counterparty</Button>
    </form>
  {/snippet}
</ConfirmDialog>
