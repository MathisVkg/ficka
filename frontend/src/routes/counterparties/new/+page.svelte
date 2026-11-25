<script lang="ts">
  import { resolve } from '$app/paths';
  import CounterpartyForm from '#lib/components/CounterpartyForm.svelte';
  import Page from '#lib/components/layout/Page.svelte';
  import PageHeader from '#lib/components/layout/PageHeader.svelte';
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

<Page>
  <PageHeader
    title="New counterparty"
    back={{ href: resolve('/counterparties'), label: 'Counterparties' }}
  />
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
</Page>
