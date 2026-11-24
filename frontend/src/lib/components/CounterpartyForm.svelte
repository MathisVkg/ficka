<script lang="ts">
  import { untrack } from 'svelte';
  import { enhance } from '$app/forms';
  import { resolve } from '$app/paths';
  import Button from '#lib/components/Button.svelte';
  import Notice from '#lib/components/Notice.svelte';
  import SelectField from '#lib/components/SelectField.svelte';
  import TextField from '#lib/components/TextField.svelte';
  import { formatIban, formatVatNumber } from '#lib/identifiers.js';
  import { formatRate } from '#lib/money.js';
  import {
    ROLE_LABELS,
    type Category,
    type CounterpartyFormValues,
    type CounterpartyRole,
    type VatRate
  } from '#lib/types.js';

  interface Props {
    values: CounterpartyFormValues;
    categories: Category[];
    rates: VatRate[];
    errors?: Record<string, string>;
    message?: string | null;
    action?: string;
    submitLabel?: string;
  }

  let {
    values,
    categories,
    rates,
    errors = {},
    message = null,
    action,
    submitLabel = 'Save'
  }: Props = $props();

  const initial = untrack(() => values);
  let role = $state<string>(initial.role);
  let defaultCategory = $state(initial.default_category_id);
  let defaultRate = $state(initial.default_vat_rate_bp);
  let ibanKey = 0;
  let ibans = $state(
    (initial.ibans.length ? initial.ibans : ['']).map((value) => ({
      key: ibanKey++,
      value: /^[A-Z]{2}\d{2}[A-Z0-9]+$/.test(value) ? formatIban(value) : value
    }))
  );
  let submitting = $state(false);

  const roleItems = (Object.keys(ROLE_LABELS) as CounterpartyRole[]).map((r) => ({
    value: r,
    label: ROLE_LABELS[r]
  }));
  const categoryItems = $derived([
    { value: '', label: 'No default category' },
    ...categories.map((c) => ({
      value: String(c.id),
      label: `${c.name} (${c.direction === 'income' ? 'income' : 'expense'})`
    }))
  ]);
  const rateItems = $derived([
    { value: '', label: 'No default rate' },
    ...rates.map((r) => ({ value: String(r.rate_bp), label: formatRate(r.rate_bp) }))
  ]);
  const errorList = $derived(Object.entries(errors));
  const vatDisplay = $derived(
    /^[A-Z]{2}[A-Z0-9]+$/.test(initial.vat_number)
      ? formatVatNumber(initial.vat_number)
      : initial.vat_number
  );
</script>

<form
  method="POST"
  {action}
  class="flex flex-col gap-3"
  use:enhance={() => {
    submitting = true;
    return async ({ update }) => {
      await update({ reset: false });
      submitting = false;
    };
  }}
>
  {#if errorList.length > 0 || message}
    <Notice tone="error" title={message ?? 'Some fields need your attention.'}>
      {#if errorList.length > 0}
        <ul class="list-disc pl-2">
          {#each errorList as [key, text] (key)}
            <li>
              <a class="underline underline-offset-2" href="#cp-{key.replace('.', '-')}">{text}</a>
            </li>
          {/each}
        </ul>
      {/if}
    </Notice>
  {/if}

  <section class="rounded-xl border border-border bg-surface p-2 md:p-3">
    <div class="grid grid-cols-1 gap-2 md:grid-cols-2">
      <TextField
        id="cp-name"
        label="Name"
        name="name"
        required
        maxlength={200}
        value={initial.name}
        error={errors.name}
      />
      <SelectField
        id="cp-role"
        label="Role"
        name="role"
        items={roleItems}
        bind:value={role}
        error={errors.role}
      />
      <TextField
        id="cp-vat_number"
        label="VAT number"
        name="vat_number"
        maxlength={40}
        placeholder="BE 0123.456.749"
        value={vatDisplay}
        error={errors.vat_number}
        hint="Belgian numbers are checked. Other countries are kept as typed."
      />
      <div class="flex flex-col gap-1">
        <span class="text-sm font-medium">IBANs</span>
        {#each ibans as iban, index (iban.key)}
          <div class="flex items-start gap-0.5">
            <div class="min-w-0 flex-1">
              <label for="cp-ibans-{index}" class="sr-only">IBAN {index + 1}</label>
              <input
                id="cp-ibans-{index}"
                name="ibans"
                bind:value={iban.value}
                placeholder="BE71 0961 2345 6769"
                autocomplete="off"
                aria-invalid={errors[`ibans.${index}`] ? 'true' : undefined}
                class="min-h-[44px] w-full rounded-md border border-border bg-surface px-1.5 text-base uppercase placeholder:text-muted placeholder:normal-case focus:border-accent focus:outline-2 focus:outline-offset-1 focus:outline-accent aria-invalid:border-expense"
              />
              {#if errors[`ibans.${index}`]}
                <p class="text-sm text-expense">{errors[`ibans.${index}`]}</p>
              {/if}
            </div>
            <button
              type="button"
              aria-label="Remove IBAN {index + 1}"
              onclick={() => (ibans = ibans.filter((_, i) => i !== index))}
              class="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md text-muted hover:bg-nav hover:text-expense focus-visible:outline-2 focus-visible:outline-accent"
            >
              ×
            </button>
          </div>
        {/each}
        <div>
          <Button
            type="button"
            variant="ghost"
            class="border border-border"
            onclick={() => (ibans = [...ibans, { key: ibanKey++, value: '' }])}
          >
            Add IBAN
          </Button>
        </div>
      </div>
      <SelectField
        id="cp-default_category_id"
        label="Default category"
        name="default_category_id"
        items={categoryItems}
        bind:value={defaultCategory}
        placeholder="No default category"
        error={errors.default_category_id}
      />
      <SelectField
        id="cp-default_vat_rate_bp"
        label="Default VAT rate"
        name="default_vat_rate_bp"
        items={rateItems}
        bind:value={defaultRate}
        placeholder="No default rate"
        error={errors.default_vat_rate_bp}
      />
      <div class="flex flex-col gap-0.5 md:col-span-2">
        <label for="cp-notes" class="text-sm font-medium">Notes</label>
        <textarea
          id="cp-notes"
          name="notes"
          rows="3"
          maxlength="2000"
          class="rounded-md border border-border bg-surface px-1.5 py-1 text-base focus:border-accent focus:outline-2 focus:outline-offset-1 focus:outline-accent"
          >{initial.notes}</textarea
        >
      </div>
    </div>
  </section>

  <div class="flex flex-wrap items-center gap-1">
    <Button disabled={submitting}>{submitting ? 'Saving…' : submitLabel}</Button>
    <a
      href={resolve('/counterparties')}
      class="inline-flex min-h-[44px] items-center rounded-md px-2.5 text-sm font-medium text-muted hover:bg-nav hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
    >
      Cancel
    </a>
  </div>
</form>
