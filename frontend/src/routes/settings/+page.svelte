<script lang="ts">
  import { enhance } from '$app/forms';
  import Button from '#lib/components/Button.svelte';
  import CategoriesSection from '#lib/components/CategoriesSection.svelte';
  import TextField from '#lib/components/TextField.svelte';
  import { formString } from '#lib/forms.js';
  import type { PageProps } from './$types';
  import type { CategoryResult, PasswordErrors } from './+page.server';

  const MIN_PASSWORD_LENGTH = 8;

  let { data, form }: PageProps = $props();

  type FormResult = {
    password?: { errors: PasswordErrors; success: boolean };
    category?: CategoryResult;
  };
  const result = $derived((form ?? null) as FormResult | null);

  let clientErrors = $state<PasswordErrors>({});
  let submitting = $state(false);

  const errors = $derived<PasswordErrors>({ ...result?.password?.errors, ...clientErrors });
  const success = $derived(result?.password?.success === true);
</script>

<svelte:head>
  <title>Settings · Ficka</title>
</svelte:head>

<div class="flex max-w-[760px] flex-col gap-4">
  <h1 class="text-3xl font-semibold tracking-tight">Settings</h1>

  <!-- Sections: Account, Categories. Later settings sections go below as further <section> blocks. -->
  <section
    aria-labelledby="settings-account"
    class="rounded-xl border border-border bg-surface p-3 md:p-4"
  >
    <h2 id="settings-account" class="text-lg font-semibold">Account</h2>
    <p class="mt-0.5 text-sm text-muted">Change the password you use to sign in.</p>

    <form
      method="POST"
      action="?/password"
      class="mt-3 flex flex-col gap-2"
      use:enhance={({ formData, cancel }) => {
        const next = formString(formData, 'new_password');
        const confirm = formString(formData, 'confirm_password');
        const found: PasswordErrors = {};
        if (next.length < MIN_PASSWORD_LENGTH) {
          found.new = `Use at least ${MIN_PASSWORD_LENGTH} characters.`;
        }
        if (confirm !== next) found.confirm = 'The passwords don’t match.';
        clientErrors = found;
        if (Object.keys(found).length > 0) {
          cancel();
          return;
        }
        submitting = true;
        return async ({ update }) => {
          await update();
          submitting = false;
        };
      }}
    >
      <TextField
        label="Current password"
        name="current_password"
        type="password"
        autocomplete="current-password"
        required
        error={errors.current}
      />
      <TextField
        label="New password"
        name="new_password"
        type="password"
        autocomplete="new-password"
        minlength={MIN_PASSWORD_LENGTH}
        required
        hint="At least {MIN_PASSWORD_LENGTH} characters."
        error={errors.new}
      />
      <TextField
        label="Confirm new password"
        name="confirm_password"
        type="password"
        autocomplete="new-password"
        required
        error={errors.confirm}
      />

      <div aria-live="polite" class="min-h-[20px]">
        {#if errors.form}
          <p class="text-sm text-expense">{errors.form}</p>
        {:else if success}
          <p class="text-sm text-income">Password changed. Other sessions were signed out.</p>
        {/if}
      </div>

      <div>
        <Button disabled={submitting}>{submitting ? 'Saving…' : 'Change password'}</Button>
      </div>
    </form>
  </section>

  <CategoriesSection
    categories={data.categories}
    rates={data.rates}
    result={result?.category ?? null}
  />
</div>
