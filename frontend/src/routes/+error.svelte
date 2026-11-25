<script lang="ts">
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import Card from '#lib/components/layout/Card.svelte';
  import Page from '#lib/components/layout/Page.svelte';
  import PageHeader from '#lib/components/layout/PageHeader.svelte';
</script>

<svelte:head>
  <title>Error {page.status} · Ficka</title>
</svelte:head>

<Page>
  <PageHeader title={page.status === 404 ? 'Not found' : `Something went wrong (${page.status})`} />
  <Card>
    <p class="max-w-[70ch] text-muted">
      {page.status === 404 ? 'This page or item doesn’t exist.' : page.error?.message}
    </p>
    <a href={resolve('/')} class="mt-2 inline-block font-medium text-accent">
      Back to the dashboard
    </a>
  </Card>
</Page>
