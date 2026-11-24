<script lang="ts">
  import { resolve } from '$app/paths';
  import EntryForm from '#lib/components/entry/EntryForm.svelte';
  import type { PageProps } from './$types';

  let { data, form }: PageProps = $props();
</script>

<svelte:head>
  <title>New entry · Ficka</title>
</svelte:head>

<div class="flex max-w-[960px] flex-col gap-3">
  <header>
    <a href={resolve('/entries')} class="text-sm text-muted hover:text-ink">← Entries</a>
    <h1 class="mt-0.5 text-3xl font-semibold tracking-tight">New entry</h1>
  </header>

  <EntryForm
    categories={data.categories}
    rates={data.rates}
    amountsIncludeVatDefault={data.amountsIncludeVatDefault}
    serverErrors={form?.errors ?? {}}
    serverMessage={form?.message ?? null}
  />
</div>
