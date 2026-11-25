<script lang="ts">
  import { tick } from 'svelte';
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import Amount from '#lib/components/Amount.svelte';
  import SelectField from '#lib/components/SelectField.svelte';
  import Card from '#lib/components/layout/Card.svelte';
  import Field from '#lib/components/layout/Field.svelte';
  import FormGrid from '#lib/components/layout/FormGrid.svelte';
  import Page from '#lib/components/layout/Page.svelte';
  import PageHeader from '#lib/components/layout/PageHeader.svelte';
  import { buttonClass, controlClass } from '#lib/components/layout/styles.js';
  import Toast from '#lib/components/Toast.svelte';
  import { formatVatNumber } from '#lib/identifiers.js';
  import { ROLE_LABELS, type CounterpartyRole } from '#lib/types.js';
  import type { PageProps } from './$types';

  let { data }: PageProps = $props();

  let filterForm = $state<HTMLFormElement>();
  const list = $derived(data.list);
  const filters = $derived(data.filters);
  const firstRow = $derived(list.total === 0 ? 0 : (filters.page - 1) * data.pageSize + 1);
  const lastRow = $derived(Math.min(filters.page * data.pageSize, list.total));
  const deleted = $derived(page.url.searchParams.get('deleted'));

  const roleItems = [
    { value: 'any', label: 'All roles' },
    ...(Object.keys(ROLE_LABELS) as CounterpartyRole[]).map((r) => ({
      value: r,
      label: ROLE_LABELS[r]
    }))
  ];

  function query(nextPage: number): '' | `?${string}` {
    const parts: string[] = [];
    if (filters.q) parts.push(`q=${encodeURIComponent(filters.q)}`);
    if (filters.role) parts.push(`role=${filters.role}`);
    if (nextPage > 1) parts.push(`page=${nextPage}`);
    return parts.length ? `?${parts.join('&')}` : '';
  }

  async function submit() {
    await tick();
    filterForm?.requestSubmit();
  }
</script>

<svelte:head>
  <title>Counterparties · Ficka</title>
</svelte:head>

{#if deleted !== null}
  <Toast
    message={deleted === '0'
      ? 'Counterparty deleted'
      : `Counterparty deleted; ${deleted} entries kept without it`}
  />
{/if}

<Page>
  <PageHeader title="Counterparties">
    {#snippet actions()}
      <a href={resolve('/counterparties/new')} class={buttonClass('primary')}>New counterparty</a>
    {/snippet}
  </PageHeader>

  <div class="flex flex-col gap-3">
    <Card label="Filters">
      <form bind:this={filterForm} method="GET" data-sveltekit-keepfocus>
        <FormGrid columns={4}>
          <Field label="Search" for="cp-q" class="sm:col-span-2">
            <div class="flex gap-0.5">
              <input
                id="cp-q"
                type="search"
                name="q"
                value={filters.q}
                placeholder="Name, VAT number or IBAN"
                class={controlClass}
              />
              <button type="submit" class={buttonClass('secondary')}>Search</button>
            </div>
          </Field>
          <SelectField
            label="Role"
            name="role"
            items={roleItems}
            value={filters.role ?? 'any'}
            onchange={submit}
          />
        </FormGrid>
      </form>
    </Card>

    {#if list.items.length === 0}
      <Card>
        <div class="py-3 text-center">
          {#if filters.q || filters.role}
            <p class="text-muted">No counterparties match.</p>
            <a href={resolve('/counterparties')} class={[buttonClass('secondary'), 'mt-2']}>
              Clear filters
            </a>
          {:else}
            <p class="text-muted">No customers or suppliers yet.</p>
            <a href={resolve('/counterparties/new')} class={[buttonClass('primary'), 'mt-2']}>
              New counterparty
            </a>
          {/if}
        </div>
      </Card>
    {:else}
      <div class="overflow-x-auto rounded-xl border border-border bg-surface">
        <table class="w-full min-w-[640px] text-left text-sm">
          <thead class="border-b border-border text-xs text-muted">
            <tr>
              <th scope="col" class="px-2 py-1.5 font-medium">Name</th>
              <th scope="col" class="px-2 py-1.5 font-medium">VAT number</th>
              <th scope="col" class="px-2 py-1.5 font-medium">Role</th>
              <th scope="col" class="px-2 py-1.5 text-right font-medium">Entries</th>
              <th scope="col" class="px-2 py-1.5 text-right font-medium">Open balance</th>
            </tr>
          </thead>
          <tbody>
            {#each list.items as cp (cp.id)}
              <tr class="relative border-b border-border last:border-b-0 hover:bg-bg">
                <td class="px-2 py-1.5 font-medium">
                  <a
                    href={resolve('/counterparties/[id]', { id: String(cp.id) })}
                    class="after:absolute after:inset-0 after:content-[''] focus-visible:outline-2 focus-visible:outline-accent"
                  >
                    {cp.name}
                  </a>
                </td>
                <td class="px-2 py-1.5 text-muted amount">
                  {formatVatNumber(cp.vat_number) || '—'}
                </td>
                <td class="px-2 py-1.5 text-muted">{ROLE_LABELS[cp.role]}</td>
                <td class="px-2 py-1.5 text-right amount">{cp.entries_count}</td>
                <td class="px-2 py-1.5 text-right">
                  {#if cp.open_balance_cents === 0}
                    <span class="text-muted">—</span>
                  {:else}
                    <Amount
                      cents={Math.abs(cp.open_balance_cents)}
                      direction={cp.open_balance_cents > 0 ? 'income' : 'expense'}
                    />
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <p class="text-xs text-muted">
        Open balance: what this counterparty still owes you (+) or what you still owe them (−), on
        confirmed entries.
      </p>
      <nav aria-label="Pagination" class="flex flex-wrap items-center justify-between gap-2">
        <p class="text-sm text-muted amount">{firstRow}–{lastRow} of {list.total}</p>
        <div class="flex gap-1">
          {#if filters.page > 1}
            <a
              href={resolve(`/counterparties${query(filters.page - 1)}`)}
              class={buttonClass('secondary')}
            >
              Previous
            </a>
          {/if}
          {#if lastRow < list.total}
            <a
              href={resolve(`/counterparties${query(filters.page + 1)}`)}
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
