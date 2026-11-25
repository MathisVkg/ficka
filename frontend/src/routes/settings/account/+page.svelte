<script lang="ts">
  import { enhance } from '$app/forms';
  import Button from '#lib/components/Button.svelte';
  import TextField from '#lib/components/TextField.svelte';
  import Card from '#lib/components/layout/Card.svelte';
  import { formString } from '#lib/forms.js';
  import type { PageProps } from './$types';
  import type { PasswordErrors } from './+page.server';

  const MIN_PASSWORD_LENGTH = 8;

  let { form }: PageProps = $props();

  type FormResult = {
    password?: { errors: PasswordErrors; success: boolean };
  };
  const result = $derived((form ?? null) as FormResult | null);

  let clientErrors = $state<PasswordErrors>({});
  let submitting = $state(false);

  const errors = $derived<PasswordErrors>({ ...result?.password?.errors, ...clientErrors });
  const success = $derived(result?.password?.success === true);
</script>

<svelte:head>
  <title>Account · Settings · Ficka</title>
</svelte:head>

<div class="flex flex-col gap-4">
  <Card
    title="Account"
    titleId="settings-account"
    description="Change the password you use to sign in."
  >
    <form
      method="POST"
      action="?/password"
      class="grid grid-cols-1 items-start gap-2 lg:grid-cols-3"
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

      <div aria-live="polite" class="min-h-[20px] lg:col-span-3">
        {#if errors.form}
          <p class="text-sm text-expense">{errors.form}</p>
        {:else if success}
          <p class="text-sm text-income">Password changed. Other sessions were signed out.</p>
        {/if}
      </div>

      <div class="lg:col-span-3">
        <Button disabled={submitting}>{submitting ? 'Saving…' : 'Change password'}</Button>
      </div>
    </form>
  </Card>
</div>
