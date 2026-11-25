<script lang="ts">
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import Toast from '#lib/components/Toast.svelte';
  import EntryForm from '#lib/components/entry/EntryForm.svelte';
  import Page from '#lib/components/layout/Page.svelte';
  import PageHeader from '#lib/components/layout/PageHeader.svelte';
  import type { ResolvedPathname } from '$app/types';
  import type { PageProps } from './$types';

  let { data, form }: PageProps = $props();

  const savedId = $derived(page.url.searchParams.get('saved'));
  // `from` is validated on the server (same-site relative path, /entries otherwise).
  const from = $derived(data.from as ResolvedPathname);
</script>

<svelte:head>
  <title>New entry · Ficka</title>
</svelte:head>

{#if savedId}
  {#key savedId}
    <Toast
      message="Entry saved. Ready for the next one."
      link={{ href: resolve('/entries/[id]', { id: savedId }), label: 'View entry' }}
    />
  {/key}
{/if}

<Page>
  <PageHeader title="New entry" back={{ href: from, label: 'Entries' }} />

  {#key data.formKey}
    <EntryForm
      categories={data.categories}
      rates={data.rates}
      initialDirection={data.initialDirection}
      initialDate={data.initialDate}
      serverErrors={form?.errors ?? {}}
      serverMessage={form?.message ?? null}
      cancelHref={from}
    />
  {/key}
</Page>
