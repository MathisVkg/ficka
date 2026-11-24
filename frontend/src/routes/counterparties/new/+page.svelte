<script lang="ts">
  import { resolve } from '$app/paths';
  import CounterpartyForm from '#lib/components/CounterpartyForm.svelte';
  import type { PageProps } from './$types';

  let { data, form }: PageProps = $props();

  const empty = {
    name: '',
    role: 'supplier' as const,
    vat_number: '',
    ibans: [],
    default_category_id: '',
    default_vat_rate_bp: '',
    notes: ''
  };
</script>

<svelte:head>
  <title>New counterparty · Ficka</title>
</svelte:head>

<div class="flex max-w-[960px] flex-col gap-3">
  <header>
    <a href={resolve('/counterparties')} class="text-sm text-muted hover:text-ink">
      ← Counterparties
    </a>
    <h1 class="mt-0.5 text-3xl font-semibold tracking-tight">New counterparty</h1>
  </header>
  {#key form}
    <CounterpartyForm
      values={form?.values ?? empty}
      categories={data.categories}
      rates={data.rates}
      errors={form?.errors ?? {}}
      message={form?.message ?? null}
      submitLabel="Create"
    />
  {/key}
</div>
