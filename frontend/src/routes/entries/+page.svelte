<script lang="ts">
  import { tick } from 'svelte';
  import { enhance } from '$app/forms';
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import { replaceState } from '$app/navigation';
  import Amount from '#lib/components/Amount.svelte';
  import Card from '#lib/components/layout/Card.svelte';
  import Field from '#lib/components/layout/Field.svelte';
  import FormGrid from '#lib/components/layout/FormGrid.svelte';
  import Page from '#lib/components/layout/Page.svelte';
  import PageHeader from '#lib/components/layout/PageHeader.svelte';
  import { buttonClass, controlClass } from '#lib/components/layout/styles.js';
  import PaymentBadge from '#lib/components/PaymentBadge.svelte';
  import SelectField from '#lib/components/SelectField.svelte';
  import SourceIcon from '#lib/components/SourceIcon.svelte';
  import Toast from '#lib/components/Toast.svelte';
  import { PERIODS } from '#lib/dates.js';
  import { formatCents, formatDate } from '#lib/money.js';
  import { currentAsFrom } from '#lib/return-to.js';
  import { PAYMENT_STATUS_LABELS, type PaymentStatus } from '#lib/types.js';
  import type { ResolvedPathname } from '$app/types';
  import type { PageProps } from './$types';

  let { data }: PageProps = $props();

  let filterForm = $state<HTMLFormElement>();
  const deleted = $derived(page.url.searchParams.get('deleted') === '1');
  const marked = $derived(page.url.searchParams.get('marked') === '1');
  const saved = $derived(page.url.searchParams.get('saved') === '1');
  const highlightId = $derived(Number(page.url.searchParams.get('highlight')) || null);
  const highlightVisible = $derived(data.list.items.some((e) => e.id === highlightId));
  /** This list (with its filters) as the "from" for the entry form, URL-encoded. */
  const fromParam = $derived(encodeURIComponent(currentAsFrom(page.url)));

  /** Link to an entry that remembers this list, so Save and Cancel come back here. */
  function entryHref(id: number): ResolvedPathname {
    return `${resolve('/entries/[id]', { id: String(id) })}?from=${fromParam}` as ResolvedPathname;
  }

  /** After the toast: drop saved/highlight/marked/deleted from the URL, keep the filters. */
  function clearTransient() {
    void replaceState(resolve(`/entries${query({})}`), page.state);
  }
  // Form actions keep the current filters: "?period=all&/markPaid".
  const markPaidAction = $derived.by(() => {
    const current = query({});
    return current ? `${current}&/markPaid` : '?/markPaid';
  });

  const filters = $derived(data.filters);
  const list = $derived(data.list);
  const result = $derived(list.summary.income_net_cents - list.summary.expense_net_cents);
  const firstRow = $derived(list.total === 0 ? 0 : (filters.page - 1) * data.pageSize + 1);
  const lastRow = $derived(Math.min(filters.page * data.pageSize, list.total));
  const hasFilters = $derived(
    Boolean(
      filters.direction ||
      filters.period !== 'this-month' ||
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
      period: filters.period === 'this-month' ? null : filters.period,
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

{#if deleted}<Toast message="Entry deleted" onclose={clearTransient} />{/if}
{#if marked}<Toast message="Marked as paid" onclose={clearTransient} />{/if}
{#if saved}
  <Toast
    message="Entry saved"
    link={highlightId && !highlightVisible
      ? { href: entryHref(highlightId), label: 'View entry' }
      : null}
    onclose={clearTransient}
  />
{/if}

<Page>
  <PageHeader title="Entries">
    {#snippet actions()}
      <a href={resolve(`/entries/new?from=${fromParam}`)} class={buttonClass('primary')}>
        New entry
      </a>
    {/snippet}
  </PageHeader>

  <div class="flex flex-col gap-3">
    <!-- Filters: a GET form, so every filter lives in the URL. -->
    <Card label="Filters">
      <form
        bind:this={filterForm}
        method="GET"
        data-sveltekit-keepfocus
        class="flex flex-col gap-2"
      >
        <div class="flex flex-col gap-2 2xl:flex-row 2xl:items-end">
          <nav aria-label="Direction" class="flex shrink-0 flex-wrap gap-0.5">
            {#each tabs as tab (tab.label)}
              {@const active = filters.direction === tab.value}
              <a
                href={resolve(
                  `/entries${query({ direction: tab.value, page: null, category_id: null })}`
                )}
                aria-current={active ? 'page' : undefined}
                class={[
                  'inline-flex h-[44px] items-center rounded-md px-2 text-sm transition-colors duration-150 ease-out focus-visible:outline-2 focus-visible:outline-accent',
                  active ? 'bg-nav font-medium text-ink' : 'text-muted hover:text-ink'
                ]}
              >
                {tab.label}
              </a>
            {/each}
          </nav>
          {#if filters.direction}
            <input type="hidden" name="direction" value={filters.direction} />
          {/if}
          {#if filters.counterpartyId}
            <input type="hidden" name="counterparty_id" value={filters.counterpartyId} />
          {/if}

          <!-- Period, Payment, Category and Search: one row from 1280px (2 x 2 below). -->
          <div
            class="grid min-w-0 flex-1 grid-cols-1 items-start gap-2 sm:grid-cols-2 xl:grid-cols-4"
          >
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
            <Field label="Search" for="entries-q">
              <div class="flex gap-0.5">
                <input
                  id="entries-q"
                  name="q"
                  type="search"
                  value={filters.q}
                  placeholder="Description, invoice no., counterparty"
                  class={controlClass}
                />
                <button type="submit" class={buttonClass('secondary')}>Search</button>
              </div>
            </Field>
          </div>
        </div>

        {#if period === 'custom'}
          <FormGrid columns={4}>
            <Field label="From" for="entries-from">
              <input
                id="entries-from"
                name="from"
                type="date"
                value={filters.from ?? ''}
                class={controlClass}
              />
            </Field>
            <Field label="To" for="entries-to">
              <input
                id="entries-to"
                name="to"
                type="date"
                value={filters.to ?? ''}
                class={controlClass}
              />
            </Field>
            <div class="pt-[22px]">
              <button type="submit" class={buttonClass('secondary')}>Apply</button>
            </div>
          </FormGrid>
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
    </Card>

    <!-- Summary for everything matching the filters (not just this page). -->
    <section aria-label="Summary" class="grid grid-cols-1 gap-2 sm:grid-cols-3">
      <Card>
        <p class="text-sm text-muted">Income</p>
        <p class="mt-0.5 text-xl font-semibold">
          <Amount cents={list.summary.income_net_cents} direction="income" />
        </p>
        <p class="text-xs text-muted">
          <Amount cents={list.summary.income_gross_cents} /> incl. VAT
        </p>
      </Card>
      <Card>
        <p class="text-sm text-muted">Expenses</p>
        <p class="mt-0.5 text-xl font-semibold">
          <Amount cents={list.summary.expense_net_cents} direction="expense" />
        </p>
        <p class="text-xs text-muted">
          <Amount cents={list.summary.expense_gross_cents} /> incl. VAT
        </p>
      </Card>
      <Card>
        <p class="text-sm text-muted">Result</p>
        <p class={['mt-0.5 text-xl font-semibold', result < 0 && 'text-expense']}>
          <Amount cents={result} />
        </p>
        <p class="text-xs text-muted">excl. VAT</p>
      </Card>
    </section>

    {#if list.items.length === 0}
      <Card>
        <div class="py-3 text-center">
          {#if hasFilters}
            <p class="text-muted">No entries match these filters.</p>
            <a href={resolve('/entries')} class={[buttonClass('secondary'), 'mt-2']}>
              Clear filters
            </a>
          {:else}
            <p class="text-muted">No entries yet. Record your first income or expense.</p>
            <a
              href={resolve(`/entries/new?from=${fromParam}`)}
              class={[buttonClass('primary'), 'mt-2']}
            >
              New entry
            </a>
          {/if}
        </div>
      </Card>
    {:else}
      <div class="overflow-x-auto rounded-xl border border-border bg-surface">
        <table class="w-full min-w-[760px] text-left text-sm">
          <thead class="border-b border-border text-xs text-muted">
            <tr>
              <th scope="col" class="px-3 py-1.5 font-medium">Date</th>
              <th scope="col" class="px-2 py-1.5 font-medium">Counterparty</th>
              <th scope="col" class="px-2 py-1.5 font-medium">Description</th>
              <th scope="col" class="px-2 py-1.5 font-medium">Category</th>
              <th scope="col" class="px-2 py-1.5 font-medium">Payment</th>
              <th scope="col" class="px-3 py-1.5 text-right font-medium">Amount</th>
            </tr>
          </thead>
          <tbody>
            {#each list.items as entry (entry.id)}
              <tr
                class={[
                  'relative h-[52px] border-b border-border transition-colors duration-150 last:border-b-0 hover:bg-bg',
                  entry.id === highlightId && saved && 'row-highlight'
                ]}
              >
                <td class="px-3 py-1 whitespace-nowrap">
                  <span class="flex items-center gap-1">
                    <SourceIcon source={entry.source} />
                    <a
                      href={entryHref(entry.id)}
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
                <td class="max-w-[200px] truncate px-2 py-1">{entry.counterparty?.name ?? '—'}</td>
                <td class="max-w-[260px] truncate px-2 py-1 text-muted">
                  {entry.description ?? entry.invoice_number ?? ''}
                </td>
                <td class="px-2 py-1 text-muted">{entry.category?.name ?? '—'}</td>
                <td class="px-2 py-1">
                  <span class="flex items-center gap-1">
                    <PaymentBadge status={entry.payment_status} />
                    {#if entry.payment_status !== 'paid'}
                      <!-- Above the row link (z-10), so clicking it doesn't open the entry. -->
                      <form method="POST" action={markPaidAction} use:enhance class="relative z-10">
                        <input type="hidden" name="id" value={entry.id} />
                        <!-- 32px to the eye, 44px to the finger (the ::before extends the hit area). -->
                        <button
                          type="submit"
                          class="relative inline-flex h-[32px] items-center rounded-md border border-border bg-surface px-1 text-xs font-medium text-ink before:absolute before:inset-x-0 before:-inset-y-[6px] before:content-[''] hover:bg-nav focus-visible:outline-2 focus-visible:outline-accent"
                          aria-label="Mark {entry.counterparty?.name ??
                            entry.description ??
                            'this entry'} of {formatCents(entry.total_gross_cents)} as paid"
                        >
                          Mark paid
                        </button>
                      </form>
                    {/if}
                  </span>
                </td>
                <td class="px-3 py-1 text-right font-medium">
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
              class={buttonClass('secondary')}
            >
              Previous
            </a>
          {/if}
          {#if lastRow < list.total}
            <a
              href={resolve(`/entries${query({ page: filters.page + 1 })}`)}
              class={buttonClass('secondary')}
            >
              Next
            </a>
          {/if}
        </div>
      </nav>
    {/if}
  </div>
</Page>
