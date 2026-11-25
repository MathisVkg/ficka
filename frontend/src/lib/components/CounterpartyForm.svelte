<script lang="ts">
  import { untrack } from 'svelte';
  import { enhance } from '$app/forms';
  import { resolve } from '$app/paths';
  import Button from '#lib/components/Button.svelte';
  import Card from '#lib/components/layout/Card.svelte';
  import Field from '#lib/components/layout/Field.svelte';
  import FormGrid from '#lib/components/layout/FormGrid.svelte';
  import { buttonClass, controlClass, labelClass } from '#lib/components/layout/styles.js';
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
  use:enhance={() => {
    submitting = true;
    return async ({ update }) => {
      await update({ reset: false });
      submitting = false;
    };
  }}
>
  <Card label="Counterparty">
    <div class="flex flex-col gap-3">
      {#if errorList.length > 0 || message}
        <Notice tone="error" title={message ?? 'Some fields need your attention.'}>
          {#if errorList.length > 0}
            <ul class="list-disc pl-2">
              {#each errorList as [key, text] (key)}
                <li>
                  <a class="underline underline-offset-2" href="#cp-{key.replace('.', '-')}">
                    {text}
                  </a>
                </li>
              {/each}
            </ul>
          {/if}
        </Notice>
      {/if}

      <FormGrid columns={3}>
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
      </FormGrid>

      <div class="flex flex-col gap-0.5">
        <span class={labelClass}>IBANs</span>
        <FormGrid columns={3}>
          {#each ibans as iban, index (iban.key)}
            <Field
              label="IBAN {index + 1}"
              for="cp-ibans-{index}"
              hideLabel
              error={errors[`ibans.${index}`]}
            >
              <div class="flex gap-0.5">
                <input
                  id="cp-ibans-{index}"
                  name="ibans"
                  bind:value={iban.value}
                  placeholder="BE71 0961 2345 6769"
                  autocomplete="off"
                  aria-invalid={errors[`ibans.${index}`] ? 'true' : undefined}
                  class={[controlClass, 'uppercase placeholder:normal-case']}
                />
                <button
                  type="button"
                  aria-label="Remove IBAN {index + 1}"
                  onclick={() => (ibans = ibans.filter((_, i) => i !== index))}
                  class="inline-flex h-[44px] w-[44px] shrink-0 items-center justify-center rounded-md text-muted hover:bg-nav hover:text-expense focus-visible:outline-2 focus-visible:outline-accent"
                >
                  ×
                </button>
              </div>
            </Field>
          {/each}
          <div>
            <Button
              type="button"
              variant="secondary"
              onclick={() => (ibans = [...ibans, { key: ibanKey++, value: '' }])}
            >
              Add IBAN
            </Button>
          </div>
        </FormGrid>
      </div>

      <Field label="Notes" for="cp-notes">
        <textarea
          id="cp-notes"
          name="notes"
          rows="3"
          maxlength="2000"
          class="w-full rounded-md border border-border bg-surface px-1.5 py-1 text-base focus:border-accent focus:outline-2 focus:outline-offset-1 focus:outline-accent"
          >{initial.notes}</textarea
        >
      </Field>

      <div class="flex flex-wrap items-center gap-1 border-t border-border pt-2">
        <Button disabled={submitting}>{submitting ? 'Saving…' : submitLabel}</Button>
        <a href={resolve('/counterparties')} class={buttonClass('ghost')}>Cancel</a>
      </div>
    </div>
  </Card>
</form>
