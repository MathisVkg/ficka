<script lang="ts">
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
</script>

<svelte:head>
  <title>Error {page.status} · Ficka</title>
</svelte:head>

<div class="max-w-[520px] rounded-xl border border-border bg-surface p-4">
  <h1 class="text-xl font-semibold">
    {page.status === 404 ? 'Not found' : `Something went wrong (${page.status})`}
  </h1>
  <p class="mt-1 text-muted">
    {page.status === 404 ? 'This page or item doesn’t exist.' : page.error?.message}
  </p>
  <a href={resolve('/')} class="mt-3 inline-block font-medium text-accent">Back to the dashboard</a>
</div>
