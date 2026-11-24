<script lang="ts">
  import { enhance } from '$app/forms';
  import Button from '#lib/components/Button.svelte';
  import TextField from '#lib/components/TextField.svelte';
  import type { PageProps } from './$types';

  let { data, form }: PageProps = $props();
  let submitting = $state(false);
</script>

<svelte:head>
  <title>Sign in · Ficka</title>
</svelte:head>

<main class="flex min-h-screen items-center justify-center p-2">
  <div class="w-full max-w-[400px] rounded-xl border border-border bg-surface p-4 md:p-5">
    <p class="text-2xl font-semibold tracking-tight text-ink">Ficka</p>
    <h1 class="mt-1 text-sm text-muted">Sign in to your workspace</h1>

    <form
      method="POST"
      class="mt-4 flex flex-col gap-2"
      use:enhance={() => {
        submitting = true;
        return async ({ update }) => {
          await update();
          submitting = false;
        };
      }}
    >
      <input type="hidden" name="next" value={data.next} />
      <TextField
        label="Email"
        name="email"
        type="email"
        autocomplete="username"
        inputmode="email"
        required
        value={form?.email ?? ''}
      />
      <TextField
        label="Password"
        name="password"
        type="password"
        autocomplete="current-password"
        required
      />

      <div aria-live="polite" class="min-h-[20px]">
        {#if form?.message}
          <p class="text-sm text-expense">{form.message}</p>
        {/if}
      </div>

      <Button disabled={submitting}>{submitting ? 'Signing in…' : 'Sign in'}</Button>
    </form>
  </div>
</main>
