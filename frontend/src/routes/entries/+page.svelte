<script lang="ts">
  import { tick } from 'svelte';
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import Amount from '#lib/components/Amount.svelte';
  import PaymentBadge from '#lib/components/PaymentBadge.svelte';
  import SelectField from '#lib/components/SelectField.svelte';
  import SourceIcon from '#lib/components/SourceIcon.svelte';
  import Toast from '#lib/components/Toast.svelte';
  import { PERIODS } from '#lib/dates.js';
  import { formatDate } from '#lib/money.js';
  import { PAYMENT_STATUS_LABELS, type PaymentStatus } from '#lib/types.js';
  import type { PageProps } from './$types';

  let { data }: PageProps = $props();

  let filterForm = $state<HTMLFormElement>();
  const deleted = $derived(page.url.searchParams.get('deleted') === '1');

  const filters = $derived(data.filters);
  const list = $derived(data.list);
  const result = $derived(list.summary.income_net_cents - list.summary.expense_net_cents);
  const firstRow = $derived(list.total === 0 ? 0 : (filters.page - 1) * data.pageSize + 1);
  const lastRow = $derived(Math.min(filters.page * data.pageSize, list.total));
  const hasFilters = $derived(
    Boolean(
      filters.direction ||
      filters.period !== 'all' ||
      filters.paymentStatus ||
      filters.categoryId ||
      filters.counterpartyId ||
      filters.q
    )
  );

  const categoryItems = $derived([
    { value: 'any', label: 'All categories' },
    ...data.categories
      .filter((c) => !filters.direction || c.direction === filters.direction)
      .map((c) => ({
        value: String(c.id),
        label: filters.direction
          ? c.name
          : `${c.name} (${c.direction === 'income' ? 'income' : 'expense'})`
      }))
  ]);
  const statusItems = [
    { value: 'any', label: 'Any payment status' },
    ...(Object.keys(PAYMENT_STATUS_LABELS) as PaymentStatus[]).map((s) => ({
      value: s,
      label: PAYMENT_STATUS_LABELS[s]
    }))
  ];
  const periodItems = PERIODS.map((p) => ({ value: p.value, label: p.label }));

  let period = $derived<string>(filters.period);

  /** The current filters as a query string, with some keys changed or removed. */
  function query(changes: Record<string, string | number | null>): '' | `?${string}` {
    const parts: string[] = [];
    const current: Record<string, string | number | null> = {
      direction: filters.direction,
      period: filters.period === 'all' ? null : filters.period,
      from: filters.from,
      to: filters.to,
      payment_status: filters.paymentStatus,
      category_id: filters.categoryId,
      counterparty_id: filters.counterpartyId,
      q: filters.q || null,
      page: filters.page > 1 ? filters.page : null
    };
    for (const [key, value] of Object.entries({ ...current, ...changes })) {
      if (value !== null && value !== '' && value !== 'any') {
        parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`);
      }
    }
    return parts.length ? `?${parts.join('&')}` : '';
  }

  async function submitFilters() {
    await tick();
    filterForm?.requestSubmit();
  }

  const tabs = [
    { value: null, label: 'All' },
    { value: 'income', label: 'Income' },
    { value: 'expense', label: 'Expenses' }
  ] as const;
</script>

<svelte:head>
  <title>Entries · Ficka</title>
</svelte:head>

{#if deleted}<Toast message="Entry deleted" />{/if}

<div class="flex flex-col gap-3">
  <header class="flex flex-wrap items-center justify-between gap-2">
    <h1 class="text-3xl font-semibold tracking-tight">Entries</h1>
    <a
      href={resolve('/entries/new')}
      class="inline-flex min-h-[44px] items-center rounded-md bg-accent px-2.5 text-sm font-medium text-white transition-colors duration-150 ease-out hover:bg-accent-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
    >
      New entry
    </a>
  </header>

  <!-- Filters: a GET form, so every filter lives in the URL. -->
  <form
    bind:this={filterForm}
    method="GET"
    class="flex flex-col gap-2 rounded-xl border border-border bg-surface p-2"
    data-sveltekit-keepfocus
  >
    <nav aria-label="Direction" class="flex flex-wrap gap-0.5">
      {#each tabs as tab (tab.label)}
        {@const active = filters.direction === tab.value}
        <a
          href={resolve(
            `/entries${query({ direction: tab.value, page: null, category_id: null })}`
          )}
          aria-current={active ? 'page' : undefined}
          class={[
            'inline-flex min-h-[44px] items-center rounded-md px-2 text-sm transition-colors duration-150 ease-out focus-visible:outline-2 focus-visible:outline-accent',
            active ? 'bg-nav font-medium text-ink' : 'text-muted hover:text-ink'
          ]}
        >
          {tab.label}
        </a>
      {/each}
    </nav>
    {#if filters.direction}<input type="hidden" name="direction" value={filters.direction} />{/if}
    {#if filters.counterpartyId}
      <input type="hidden" name="counterparty_id" value={filters.counterpartyId} />
    {/if}

    <div class="grid grid-cols-1 gap-1.5 sm:grid-cols-2 lg:grid-cols-4">
      <SelectField
        label="Period"
        name="period"
        items={periodItems}
        bind:value={period}
        onchange={(value) => value !== 'custom' && submitFilters()}
      />
      <SelectField
        label="Payment"
        name="payment_status"
        items={statusItems}
        value={filters.paymentStatus ?? 'any'}
        onchange={submitFilters}
      />
      <SelectField
        label="Category"
        name="category_id"
        items={categoryItems}
        value={filters.categoryId ? String(filters.categoryId) : 'any'}
        onchange={submitFilters}
      />
      <div class="flex flex-col gap-0.5">
        <label for="entries-q" class="text-sm font-medium text-ink">Search</label>
        <div class="flex gap-0.5">
          <input
            id="entries-q"
            name="q"
            type="search"
            value={filters.q}
            placeholder="Description, invoice no., counterparty"
            class="min-h-[44px] w-full min-w-0 rounded-md border border-border bg-surface px-1.5 text-base text-ink placeholder:text-muted focus:border-accent focus:outline-2 focus:outline-offset-1 focus:outline-accent"
          />
          <button
            type="submit"
            class="min-h-[44px] rounded-md border border-border px-1.5 text-sm font-medium text-ink hover:bg-nav focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            Search
          </button>
        </div>
      </div>
    </div>

    {#if period === 'custom'}
      <div class="flex flex-wrap items-end gap-1.5">
        <div class="flex flex-col gap-0.5">
          <label for="entries-from" class="text-sm font-medium">From</label>
          <input
            id="entries-from"
            name="from"
            type="date"
            value={filters.from ?? ''}
            class="min-h-[44px] rounded-md border border-border bg-surface px-1.5 focus:border-accent focus:outline-2 focus:outline-offset-1 focus:outline-accent"
          />
        </div>
        <div class="flex flex-col gap-0.5">
          <label for="entries-to" class="text-sm font-medium">To</label>
          <input
            id="entries-to"
            name="to"
            type="date"
            value={filters.to ?? ''}
            class="min-h-[44px] rounded-md border border-border bg-surface px-1.5 focus:border-accent focus:outline-2 focus:outline-offset-1 focus:outline-accent"
          />
        </div>
        <button
          type="submit"
          class="min-h-[44px] rounded-md border border-border px-1.5 text-sm font-medium hover:bg-nav focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          Apply
        </button>
      </div>
    {/if}

    {#if data.counterparty || hasFilters}
      <div class="flex flex-wrap items-center gap-1 text-sm text-muted">
        {#if data.counterparty}
          <span>
            Counterparty: <span class="font-medium text-ink">{data.counterparty.name}</span>
          </span>
          <a
            class="underline underline-offset-2 hover:text-ink"
            href={resolve(`/entries${query({ counterparty_id: null, page: null })}`)}
          >
            Remove
          </a>
          <span aria-hidden="true">·</span>
        {/if}
        {#if hasFilters}
          <a class="underline underline-offset-2 hover:text-ink" href={resolve('/entries')}>
            Clear filters
          </a>
        {/if}
      </div>
    {/if}
  </form>

  <!-- Summary for everything matching the filters (not just this page). -->
  <section aria-label="Summary" class="grid grid-cols-1 gap-1.5 sm:grid-cols-3">
    <div class="rounded-xl border border-border bg-surface p-2">
      <p class="text-sm text-muted">Income</p>
      <p class="mt-0.5 text-xl font-semibold">
        <Amount cents={list.summary.income_net_cents} direction="income" />
      </p>
      <p class="text-xs text-muted">
        <Amount cents={list.summary.income_gross_cents} /> incl. VAT
      </p>
    </div>
    <div class="rounded-xl border border-border bg-surface p-2">
      <p class="text-sm text-muted">Expenses</p>
      <p class="mt-0.5 text-xl font-semibold">
        <Amount cents={list.summary.expense_net_cents} direction="expense" />
      </p>
      <p class="text-xs text-muted">
        <Amount cents={list.summary.expense_gross_cents} /> incl. VAT
      </p>
    </div>
    <div class="rounded-xl border border-border bg-surface p-2">
      <p class="text-sm text-muted">Result</p>
      <p class={['mt-0.5 text-xl font-semibold', result < 0 && 'text-expense']}>
        <Amount cents={result} />
      </p>
      <p class="text-xs text-muted">excl. VAT</p>
    </div>
  </section>

  {#if list.items.length === 0}
    <div class="rounded-xl border border-border bg-surface px-3 py-5 text-center">
      {#if hasFilters}
        <p class="text-muted">No entries match these filters.</p>
        <a
          href={resolve('/entries')}
          class="mt-2 inline-flex min-h-[44px] items-center rounded-md border border-border px-2.5 text-sm font-medium hover:bg-nav focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          Clear filters
        </a>
      {:else}
        <p class="text-muted">No entries yet. Record your first income or expense.</p>
        <a
          href={resolve('/entries/new')}
          class="mt-2 inline-flex min-h-[44px] items-center rounded-md bg-accent px-2.5 text-sm font-medium text-white hover:bg-accent-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          New entry
        </a>
      {/if}
    </div>
  {:else}
    <div class="overflow-x-auto rounded-xl border border-border bg-surface">
      <table class="w-full min-w-[760px] text-left text-sm">
        <thead class="border-b border-border text-xs text-muted">
          <tr>
            <th scope="col" class="px-2 py-1.5 font-medium">Date</th>
            <th scope="col" class="px-2 py-1.5 font-medium">Counterparty</th>
            <th scope="col" class="px-2 py-1.5 font-medium">Description</th>
            <th scope="col" class="px-2 py-1.5 font-medium">Category</th>
            <th scope="col" class="px-2 py-1.5 font-medium">Payment</th>
            <th scope="col" class="px-2 py-1.5 text-right font-medium">Amount</th>
          </tr>
        </thead>
        <tbody>
          {#each list.items as entry (entry.id)}
            <tr
              class="relative border-b border-border transition-colors duration-150 last:border-b-0 hover:bg-bg"
            >
              <td class="px-2 py-1.5 whitespace-nowrap">
                <span class="flex items-center gap-1">
                  <SourceIcon source={entry.source} />
                  <a
                    href={resolve('/entries/[id]', { id: String(entry.id) })}
                    class="amount after:absolute after:inset-0 after:content-[''] focus-visible:outline-2 focus-visible:outline-accent"
                  >
                    {formatDate(entry.invoice_date)}
                  </a>
                  {#if entry.status === 'proposed'}
                    <span class="rounded-full bg-accent/10 px-1 text-xs font-medium text-accent">
                      Proposed
                    </span>
                  {/if}
                </span>
              </td>
              <td class="max-w-[200px] truncate px-2 py-1.5">
                {entry.counterparty?.name ?? '—'}
              </td>
              <td class="max-w-[260px] truncate px-2 py-1.5 text-muted">
                {entry.description ?? entry.invoice_number ?? ''}
              </td>
              <td class="px-2 py-1.5 text-muted">{entry.category?.name ?? '—'}</td>
              <td class="px-2 py-1.5"><PaymentBadge status={entry.payment_status} /></td>
              <td class="px-2 py-1.5 text-right font-medium">
                <Amount cents={entry.total_gross_cents} direction={entry.direction} />
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <nav aria-label="Pagination" class="flex flex-wrap items-center justify-between gap-2">
      <p class="text-sm text-muted amount">{firstRow}–{lastRow} of {list.total}</p>
      <div class="flex gap-1">
        {#if filters.page > 1}
          <a
            href={resolve(`/entries${query({ page: filters.page - 1 })}`)}
            class="inline-flex min-h-[44px] items-center rounded-md border border-border px-2 text-sm hover:bg-nav focus-visible:outline-2 focus-visible:outline-accent"
          >
            Previous
          </a>
        {/if}
        {#if lastRow < list.total}
          <a
            href={resolve(`/entries${query({ page: filters.page + 1 })}`)}
            class="inline-flex min-h-[44px] items-center rounded-md border border-border px-2 text-sm hover:bg-nav focus-visible:outline-2 focus-visible:outline-accent"
          >
            Next
          </a>
        {/if}
      </div>
    </nav>
  {/if}
</div>
