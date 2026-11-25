<script lang="ts">
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import Toast from '#lib/components/Toast.svelte';
  import EntryForm from '#lib/components/entry/EntryForm.svelte';
  import type { PageProps } from './$types';

  let { data, form }: PageProps = $props();

  const savedId = $derived(page.url.searchParams.get('saved'));
</script>

<svelte:head>
  <title>New entry · Ficka</title>
</svelte:head>

{#if savedId}
  {#key savedId}<Toast message="Saved. Ready for the next one." />{/key}
{/if}

<div class="flex flex-col gap-3">
  <header>
    <a href={resolve('/entries')} class="text-sm text-muted hover:text-ink">← Entries</a>
    <h1 class="mt-0.5 text-3xl font-semibold tracking-tight">New entry</h1>
  </header>

  {#key data.formKey}
    <EntryForm
      categories={data.categories}
      rates={data.rates}
      initialDirection={data.initialDirection}
      initialDate={data.initialDate}
      serverErrors={form?.errors ?? {}}
      serverMessage={form?.message ?? null}
    />
  {/key}
</div>
