<script lang="ts">
  import CategoriesSection from '#lib/components/CategoriesSection.svelte';
  import type { PageProps } from './$types';
  import type { CategoryResult } from './+page.server';

  let { data, form }: PageProps = $props();

  const result = $derived(
    ((form ?? null) as { category?: CategoryResult } | null)?.category ?? null
  );
</script>

<svelte:head>
  <title>Categories · Settings · Ficka</title>
</svelte:head>

<CategoriesSection categories={data.categories} rates={data.rates} {result} />
