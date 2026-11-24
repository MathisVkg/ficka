<script lang="ts" module>
  /** Field key from the API (`lines.0.net_cents`) → id of the input to focus. */
  export function fieldId(key: string): string {
    const line = /^lines\.(\d+)\.(\w+)$/.exec(key);
    if (line) {
      const part = line[2] === 'vat_rate_bp' ? 'rate' : line[2] === 'vat_cents' ? 'vat' : 'amount';
      return `line-${line[1]}-${part}`;
    }
    if (key === 'lines') return 'lines-editor';
    return `entry-${key.replaceAll('_', '-')}`;
  }
</script>

<script lang="ts">
  import { untrack } from 'svelte';
  import { enhance } from '$app/forms';
  import { resolve } from '$app/paths';
  import Button from '#lib/components/Button.svelte';
  import SelectField from '#lib/components/SelectField.svelte';
  import Notice from '#lib/components/Notice.svelte';
  import CounterpartyCombobox from '#lib/components/entry/CounterpartyCombobox.svelte';
  import { todayIso } from '#lib/dates.js';
  import {
    centsToInput,
    computeLine,
    formatCents,
    formatRate,
    parseAmount,
    VatError,
    type LineAmounts
  } from '#lib/money.js';
  import type {
    Category,
    CounterpartyChoice,
    Direction,
    Entry,
    EntryPayload,
    VatRate
  } from '#lib/types.js';

  interface Props {
    entry?: Entry | null;
    categories: Category[];
    rates: VatRate[];
    amountsIncludeVatDefault: boolean;
    /** Field errors and message returned by the action, keyed like the API. */
    serverErrors?: Record<string, string>;
    serverMessage?: string | null;
    action?: string;
  }

  let {
    entry = null,
    categories,
    rates: initialRates,
    amountsIncludeVatDefault,
    serverErrors = {},
    serverMessage = null,
    action
  }: Props = $props();

  // --- State ----------------------------------------------------------------------------

  interface LineState {
    key: number;
    description: string;
    amountText: string;
    rate: string; // 'none' or basis points
    vatText: string;
    vatManual: boolean;
    rateTouched: boolean;
  }

  let nextKey = 0;
  const topRate = (list: VatRate[]) => (list.length ? String(list[0].rate_bp) : 'none');

  // The form owns its state: props are read once (the page re-mounts it after a save).
  const initial = untrack(() => ({
    entry,
    rates: initialRates,
    includeVat: amountsIncludeVatDefault
  }));
  const start = initial.entry;
  let rates = $state<VatRate[]>(initial.rates);
  let direction = $state<Direction>(start?.direction ?? 'expense');
  let invoiceDate = $state(start?.invoice_date ?? todayIso());
  let dueDate = $state(start?.due_date ?? '');
  let counterparty = $state<CounterpartyChoice | null>(
    start?.counterparty
      ? { ...start.counterparty, default_category_id: null, default_vat_rate_bp: null }
      : null
  );
  let categoryId = $state(start?.category ? String(start.category.id) : '');
  let categoryTouched = $state(Boolean(start));
  let description = $state(start?.description ?? '');
  let invoiceNumber = $state(start?.invoice_number ?? '');
  let structuredReference = $state(start?.structured_reference ?? '');
  let documentLocation = $state(start?.document_location ?? '');
  let amountsIncludeVat = $state(start ? start.amounts_include_vat : initial.includeVat);
  let alreadyPaid = $state(false);
  let paidOn = $state(todayIso());
  let lines = $state<LineState[]>(
    start
      ? start.lines.map((line) => ({
          key: nextKey++,
          description: line.description ?? '',
          amountText: centsToInput(start.amounts_include_vat ? line.gross_cents : line.net_cents),
          rate: line.vat_rate_bp === null ? 'none' : String(line.vat_rate_bp),
          vatText: centsToInput(line.vat_cents),
          vatManual: line.vat_manual,
          rateTouched: true
        }))
      : [newLine()]
  );
  let clientErrors = $state<Record<string, string>>({});
  let submitted = $state(false);
  let submitting = $state(false);
  let ratesLoading = $state(false);

  function newLine(): LineState {
    const category = categories.find((c) => String(c.id) === categoryId);
    const rate =
      category && categoryTouched
        ? category.default_vat_rate_bp === null
          ? 'none'
          : String(category.default_vat_rate_bp)
        : topRate(rates);
    return {
      key: nextKey++,
      description: '',
      amountText: '',
      rate,
      vatText: '',
      vatManual: false,
      rateTouched: false
    };
  }

  // --- Derived --------------------------------------------------------------------------

  const validRates = $derived(new Set(rates.map((r) => r.rate_bp)));
  const rateItems = $derived([
    ...rates.map((r) => ({ value: String(r.rate_bp), label: formatRate(r.rate_bp) })),
    { value: 'none', label: 'No VAT' }
  ]);
  const categoryItems = $derived([
    { value: '', label: 'No category' },
    ...categories
      .filter((c) => c.direction === direction)
      .map((c) => ({ value: String(c.id), label: c.name }))
  ]);

  interface Evaluated {
    amounts: LineAmounts | null;
    errors: Partial<Record<'amount' | 'vat' | 'rate', string>>;
  }

  function evaluate(line: LineState): Evaluated {
    const errors: Evaluated['errors'] = {};
    const parsed = parseAmount(line.amountText);
    const rateBp = line.rate === 'none' ? null : Number(line.rate);
    if (rateBp !== null && !validRates.has(rateBp)) {
      errors.rate = `${formatRate(rateBp)} isn’t valid on this invoice date.`;
    }
    if (!parsed.ok) {
      errors.amount = parsed.error;
      return { amounts: null, errors };
    }
    let vatCents: number | null = null;
    if (line.vatManual && rateBp !== null) {
      const vat = parseAmount(line.vatText);
      if (!vat.ok) {
        errors.vat = vat.error;
        return { amounts: null, errors };
      }
      vatCents = vat.cents;
    }
    try {
      const amounts = computeLine(parsed.cents, rateBp, {
        amountsIncludeVat,
        vatManual: line.vatManual && rateBp !== null,
        vatCents
      });
      return { amounts, errors };
    } catch (error) {
      if (error instanceof VatError) {
        const part =
          error.field === 'vat_cents' ? 'vat' : error.field === 'vat_rate_bp' ? 'rate' : 'amount';
        errors[part] = error.message;
        return { amounts: null, errors };
      }
      throw error;
    }
  }

  const evaluated = $derived(lines.map(evaluate));
  const totals = $derived(
    evaluated.reduce(
      (sum, e) =>
        e.amounts
          ? {
              net: sum.net + e.amounts.netCents,
              vat: sum.vat + e.amounts.vatCents,
              gross: sum.gross + e.amounts.grossCents
            }
          : sum,
      { net: 0, vat: 0, gross: 0 }
    )
  );

  const payload = $derived<EntryPayload>({
    direction,
    invoice_date: invoiceDate,
    due_date: dueDate || null,
    counterparty_id: counterparty?.id ?? null,
    category_id: categoryId ? Number(categoryId) : null,
    description: description.trim() || null,
    invoice_number: invoiceNumber.trim() || null,
    structured_reference: structuredReference.trim() || null,
    amounts_include_vat: amountsIncludeVat,
    document_location: documentLocation.trim() || null,
    paid_on: !entry && alreadyPaid ? paidOn : null,
    lines: lines.map((line) => {
      const parsed = parseAmount(line.amountText);
      const rateBp = line.rate === 'none' ? null : Number(line.rate);
      const vat = parseAmount(line.vatText);
      const manual = line.vatManual && rateBp !== null;
      return {
        description: line.description.trim() || null,
        ...(parsed.ok
          ? amountsIncludeVat
            ? { gross_cents: parsed.cents }
            : { net_cents: parsed.cents }
          : {}),
        vat_rate_bp: rateBp,
        vat_manual: manual,
        ...(manual && vat.ok ? { vat_cents: vat.cents } : {})
      };
    })
  });

  // Errors shown: client ones after a submit attempt, otherwise the server's.
  const errors = $derived<Record<string, string>>(submitted ? clientErrors : serverErrors);

  function lineError(index: number, part: 'amount' | 'vat' | 'rate'): string | undefined {
    const key =
      part === 'rate'
        ? `lines.${index}.vat_rate_bp`
        : part === 'vat'
          ? `lines.${index}.vat_cents`
          : `lines.${index}.${amountsIncludeVat ? 'gross_cents' : 'net_cents'}`;
    return (
      errors[key] ??
      (part === 'amount'
        ? (errors[`lines.${index}.net_cents`] ?? errors[`lines.${index}.gross_cents`])
        : undefined)
    );
  }

  const LABELS: Record<string, string> = {
    direction: 'Type',
    invoice_date: 'Invoice date',
    due_date: 'Due date',
    counterparty_id: 'Counterparty',
    category_id: 'Category',
    description: 'Description',
    invoice_number: 'Invoice number',
    structured_reference: 'Structured reference',
    document_location: 'Document location',
    paid_on: 'Paid on',
    lines: 'Lines'
  };

  function labelFor(key: string): string {
    const line = /^lines\.(\d+)\.(\w+)$/.exec(key);
    if (line) {
      const part =
        line[2] === 'vat_rate_bp' ? 'VAT rate' : line[2] === 'vat_cents' ? 'VAT amount' : 'amount';
      return `Line ${Number(line[1]) + 1}, ${part}`;
    }
    return LABELS[key] ?? key;
  }

  const errorList = $derived(Object.entries(errors));

  // --- Actions --------------------------------------------------------------------------

  function setDirection(next: Direction) {
    if (next === direction) return;
    direction = next;
    const category = categories.find((c) => String(c.id) === categoryId);
    if (category && category.direction !== next) {
      categoryId = '';
      categoryTouched = false;
    }
  }

  function applyRateDefault(rateBp: number | null) {
    const value = rateBp === null ? 'none' : String(rateBp);
    lines = lines.map((line) =>
      line.rateTouched ? line : { ...line, rate: value, vatManual: false }
    );
  }

  function onCounterparty(choice: CounterpartyChoice | null) {
    if (!choice) return;
    if (!categoryTouched && choice.default_category_id !== null) {
      const category = categories.find(
        (c) => c.id === choice.default_category_id && c.direction === direction
      );
      if (category) {
        categoryId = String(category.id);
        if (choice.default_vat_rate_bp === null) applyRateDefault(category.default_vat_rate_bp);
      }
    }
    if (choice.default_vat_rate_bp !== null) applyRateDefault(choice.default_vat_rate_bp);
  }

  function onCategory(value: string) {
    categoryTouched = true;
    const category = categories.find((c) => String(c.id) === value);
    if (category) applyRateDefault(category.default_vat_rate_bp);
  }

  function setMode(includeVat: boolean) {
    if (includeVat === amountsIncludeVat) return;
    // Keep the amounts: what was the net becomes the gross (or back), so nothing changes.
    lines = lines.map((line, index) => {
      const amounts = evaluated[index].amounts;
      if (!amounts) return line;
      return {
        ...line,
        amountText: centsToInput(includeVat ? amounts.grossCents : amounts.netCents)
      };
    });
    amountsIncludeVat = includeVat;
  }

  async function onInvoiceDate() {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(invoiceDate)) return;
    ratesLoading = true;
    try {
      const response = await fetch(`/entries/vat-rates?on=${invoiceDate}`);
      if (response.ok) rates = (await response.json()) as VatRate[];
    } finally {
      ratesLoading = false;
    }
  }

  function addLine() {
    lines = [...lines, newLine()];
  }

  function removeLine(index: number) {
    lines = lines.filter((_, i) => i !== index);
  }

  function editVat(index: number, value: string) {
    lines[index] = { ...lines[index], vatText: value, vatManual: true };
  }

  function recalculate(index: number) {
    lines[index] = { ...lines[index], vatManual: false };
  }

  function validate(): Record<string, string> {
    const found: Record<string, string> = {};
    if (!invoiceDate) found.invoice_date = 'Enter the invoice date.';
    if (dueDate && invoiceDate && dueDate < invoiceDate) {
      found.due_date = 'The due date can’t be before the invoice date.';
    }
    if (lines.length === 0) found.lines = 'Add at least one line.';
    evaluated.forEach((e, index) => {
      const amountKey = `lines.${index}.${amountsIncludeVat ? 'gross_cents' : 'net_cents'}`;
      if (e.errors.amount) found[amountKey] = e.errors.amount;
      if (e.errors.rate) found[`lines.${index}.vat_rate_bp`] = e.errors.rate;
      if (e.errors.vat) found[`lines.${index}.vat_cents`] = e.errors.vat;
    });
    return found;
  }

  function focusSummary() {
    requestAnimationFrame(() => document.getElementById('entry-errors')?.focus());
  }

  const inputClass =
    'min-h-[44px] w-full rounded-md border border-border bg-surface px-1.5 text-base text-ink placeholder:text-muted focus:border-accent focus:outline-2 focus:outline-offset-1 focus:outline-accent aria-invalid:border-expense';
</script>

<form
  method="POST"
  {action}
  class="flex flex-col gap-3"
  novalidate
  use:enhance={({ cancel }) => {
    clientErrors = validate();
    submitted = true;
    if (Object.keys(clientErrors).length > 0) {
      cancel();
      focusSummary();
      return;
    }
    submitted = false;
    submitting = true;
    return async ({ result, update }) => {
      await update({ reset: false });
      submitting = false;
      if (result.type === 'failure') focusSummary();
    };
  }}
>
  <input type="hidden" name="payload" value={JSON.stringify(payload)} />

  {#if errorList.length > 0 || serverMessage}
    <Notice
      tone="error"
      id="entry-errors"
      title={serverMessage ?? 'Some fields need your attention.'}
    >
      {#if errorList.length > 0}
        <ul class="mt-0.5 list-disc pl-2">
          {#each errorList as [key, message] (key)}
            <li>
              <a class="underline underline-offset-2 hover:text-ink" href="#{fieldId(key)}">
                {labelFor(key)}: {message}
              </a>
            </li>
          {/each}
        </ul>
      {/if}
    </Notice>
  {/if}

  <!-- Type -->
  <fieldset class="flex flex-col gap-0.5">
    <legend class="sr-only">Type</legend>
    <div
      id="entry-direction"
      class="inline-flex w-fit rounded-lg border border-border bg-surface p-0.5"
      role="radiogroup"
      aria-label="Type"
    >
      {#each [{ value: 'income', label: 'Income' }, { value: 'expense', label: 'Expense' }] as option (option.value)}
        <label
          class={[
            'inline-flex min-h-[40px] cursor-pointer items-center rounded-md px-2.5 text-sm font-medium transition-colors duration-150 ease-out has-focus-visible:outline-2 has-focus-visible:outline-accent',
            direction === option.value
              ? option.value === 'income'
                ? 'bg-income/10 text-income'
                : 'bg-nav text-ink'
              : 'text-muted hover:text-ink'
          ]}
        >
          <input
            type="radio"
            name="direction-choice"
            value={option.value}
            checked={direction === option.value}
            onchange={() => setDirection(option.value as Direction)}
            class="sr-only"
          />
          {option.label}
        </label>
      {/each}
    </div>
  </fieldset>

  <!-- Details -->
  <section class="rounded-xl border border-border bg-surface p-2 md:p-3">
    <h2 class="text-base font-semibold">Details</h2>
    <div class="mt-2 grid grid-cols-1 gap-2 md:grid-cols-2">
      <div class="flex flex-col gap-0.5">
        <label for="entry-invoice-date" class="text-sm font-medium">Invoice date</label>
        <input
          id="entry-invoice-date"
          type="date"
          required
          bind:value={invoiceDate}
          onchange={onInvoiceDate}
          aria-invalid={errors.invoice_date ? 'true' : undefined}
          class={inputClass}
        />
        {#if errors.invoice_date}<p class="text-sm text-expense">{errors.invoice_date}</p>{/if}
      </div>
      <div class="flex flex-col gap-0.5">
        <label for="entry-due-date" class="text-sm font-medium">Due date</label>
        <input
          id="entry-due-date"
          type="date"
          bind:value={dueDate}
          min={invoiceDate}
          aria-invalid={errors.due_date ? 'true' : undefined}
          class={inputClass}
        />
        {#if errors.due_date}<p class="text-sm text-expense">{errors.due_date}</p>{/if}
      </div>
      <CounterpartyCombobox
        id="entry-counterparty-id"
        bind:value={counterparty}
        createRole={direction === 'income' ? 'customer' : 'supplier'}
        error={errors.counterparty_id}
        onselect={onCounterparty}
      />
      <SelectField
        id="entry-category-id"
        label="Category"
        items={categoryItems}
        bind:value={categoryId}
        placeholder="No category"
        error={errors.category_id}
        onchange={onCategory}
      />
      <div class="flex flex-col gap-0.5 md:col-span-2">
        <label for="entry-description" class="text-sm font-medium">Description</label>
        <input id="entry-description" maxlength="500" bind:value={description} class={inputClass} />
      </div>
      <div class="flex flex-col gap-0.5">
        <label for="entry-invoice-number" class="text-sm font-medium">Invoice number</label>
        <input
          id="entry-invoice-number"
          maxlength="100"
          bind:value={invoiceNumber}
          class={inputClass}
        />
      </div>
      <div class="flex flex-col gap-0.5">
        <label for="entry-structured-reference" class="text-sm font-medium">
          Structured reference
        </label>
        <input
          id="entry-structured-reference"
          maxlength="40"
          inputmode="numeric"
          placeholder="+++090/9337/55493+++"
          bind:value={structuredReference}
          aria-invalid={errors.structured_reference ? 'true' : undefined}
          class={inputClass}
        />
        {#if errors.structured_reference}
          <p class="text-sm text-expense">{errors.structured_reference}</p>
        {/if}
      </div>
      <div class="flex flex-col gap-0.5 md:col-span-2">
        <label for="entry-document-location" class="text-sm font-medium">Document location</label>
        <input
          id="entry-document-location"
          maxlength="2000"
          placeholder="Where the original is kept, e.g. a link or a folder"
          bind:value={documentLocation}
          class={inputClass}
        />
      </div>
    </div>
  </section>

  <!-- Lines -->
  <section
    id="lines-editor"
    tabindex="-1"
    aria-labelledby="lines-heading"
    class="rounded-xl border border-border bg-surface p-2 outline-none md:p-3"
  >
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h2 id="lines-heading" class="text-base font-semibold">Lines</h2>
      <label class="flex min-h-[44px] cursor-pointer items-center gap-1 text-sm">
        <input
          type="checkbox"
          checked={amountsIncludeVat}
          onchange={(e) => setMode(e.currentTarget.checked)}
          class="size-2.5 accent-(--color-accent)"
        />
        Amounts include VAT
      </label>
    </div>
    {#if errors.lines}<p class="mt-1 text-sm text-expense">{errors.lines}</p>{/if}
    {#if ratesLoading}<p class="mt-1 text-xs text-muted">Loading the VAT rates…</p>{/if}

    <div class="mt-2 flex flex-col gap-2">
      {#each lines as line, index (line.key)}
        {@const result = evaluated[index]}
        {@const amountError =
          lineError(index, 'amount') ?? (line.amountText ? result.errors.amount : undefined)}
        {@const rateError = lineError(index, 'rate') ?? result.errors.rate}
        {@const vatError = lineError(index, 'vat') ?? result.errors.vat}
        <div
          class="grid grid-cols-1 gap-1.5 rounded-lg border border-border p-1.5 sm:grid-cols-2 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_auto] lg:items-start"
        >
          <div class="flex flex-col gap-0.5">
            <label for="line-{index}-description" class="text-xs font-medium text-muted">
              Description
            </label>
            <input
              id="line-{index}-description"
              bind:value={line.description}
              maxlength="500"
              class={inputClass}
            />
          </div>
          <div class="flex flex-col gap-0.5">
            <label for="line-{index}-amount" class="text-xs font-medium text-muted">
              {amountsIncludeVat ? 'Amount incl. VAT' : 'Amount excl. VAT'}
            </label>
            <input
              id="line-{index}-amount"
              inputmode="decimal"
              autocomplete="off"
              placeholder="0,00"
              bind:value={line.amountText}
              aria-invalid={amountError ? 'true' : undefined}
              class={[inputClass, 'text-right amount']}
            />
            {#if amountError}<p class="text-xs text-expense">{amountError}</p>{/if}
          </div>
          <SelectField
            id="line-{index}-rate"
            label="VAT rate"
            items={rateItems.some((i) => i.value === line.rate)
              ? rateItems
              : [
                  ...rateItems,
                  { value: line.rate, label: `${formatRate(Number(line.rate))} (not valid)` }
                ]}
            bind:value={line.rate}
            error={rateError}
            onchange={() => {
              lines[index] = { ...lines[index], rateTouched: true, vatManual: false };
            }}
          />
          <div class="flex flex-col gap-0.5">
            <span class="flex items-center justify-between gap-1">
              <label for="line-{index}-vat" class="text-xs font-medium text-muted">VAT</label>
              {#if line.vatManual && line.rate !== 'none'}
                <span class="flex items-center gap-0.5">
                  <span class="rounded-full bg-warning/10 px-0.5 text-xs text-warning">manual</span>
                  <button
                    type="button"
                    class="rounded-md px-0.5 text-xs font-medium text-accent hover:underline focus-visible:outline-2 focus-visible:outline-accent"
                    onclick={() => recalculate(index)}
                  >
                    ↺ Recalculate
                  </button>
                </span>
              {/if}
            </span>
            <input
              id="line-{index}-vat"
              inputmode="decimal"
              autocomplete="off"
              disabled={line.rate === 'none'}
              value={line.vatManual
                ? line.vatText
                : result.amounts
                  ? centsToInput(result.amounts.vatCents)
                  : ''}
              oninput={(e) => editVat(index, e.currentTarget.value)}
              aria-invalid={vatError ? 'true' : undefined}
              class={[inputClass, 'text-right amount disabled:bg-bg disabled:text-muted']}
            />
            {#if vatError}<p class="text-xs text-expense">{vatError}</p>{/if}
          </div>
          <div class="flex items-end lg:pt-[22px]">
            <button
              type="button"
              aria-label="Remove line {index + 1}"
              disabled={lines.length === 1}
              onclick={() => removeLine(index)}
              class="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md text-muted hover:bg-nav hover:text-expense focus-visible:outline-2 focus-visible:outline-accent disabled:opacity-40"
            >
              <svg
                aria-hidden="true"
                viewBox="0 0 16 16"
                class="size-2"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
              >
                <path d="M4 4l8 8M12 4l-8 8" />
              </svg>
            </button>
          </div>
        </div>
      {/each}
    </div>
    <div class="mt-2">
      <Button type="button" variant="ghost" class="border border-border" onclick={addLine}>
        Add line
      </Button>
    </div>
  </section>

  <!-- Totals and payment -->
  <div class="grid grid-cols-1 gap-2 md:grid-cols-2">
    <section aria-label="Totals" class="rounded-xl border border-border bg-surface p-2 md:p-3">
      <h2 class="text-base font-semibold">Totals</h2>
      <dl class="mt-1.5 flex flex-col gap-0.5 text-sm">
        <div class="flex justify-between">
          <dt class="text-muted">Net</dt>
          <dd class="amount">{formatCents(totals.net)}</dd>
        </div>
        <div class="flex justify-between">
          <dt class="text-muted">VAT</dt>
          <dd class="amount">{formatCents(totals.vat)}</dd>
        </div>
        <div
          class="mt-0.5 flex justify-between border-t border-border pt-1 text-base font-semibold"
        >
          <dt>Total</dt>
          <dd class="amount">{formatCents(totals.gross)}</dd>
        </div>
      </dl>
    </section>

    {#if !entry}
      <section aria-label="Payment" class="rounded-xl border border-border bg-surface p-2 md:p-3">
        <h2 class="text-base font-semibold">Payment</h2>
        <label class="mt-1.5 flex min-h-[44px] cursor-pointer items-center gap-1 text-sm">
          <input
            type="checkbox"
            bind:checked={alreadyPaid}
            class="size-2.5 accent-(--color-accent)"
          />
          Already paid
        </label>
        {#if alreadyPaid}
          <div class="flex flex-col gap-0.5">
            <label for="entry-paid-on" class="text-sm font-medium">Paid on</label>
            <input id="entry-paid-on" type="date" bind:value={paidOn} class={inputClass} />
          </div>
        {/if}
      </section>
    {/if}
  </div>

  <div class="flex flex-wrap items-center gap-1">
    <Button disabled={submitting}>{submitting ? 'Saving…' : 'Save'}</Button>
    <a
      href={resolve('/entries')}
      class="inline-flex min-h-[44px] items-center rounded-md px-2.5 text-sm font-medium text-muted hover:bg-nav hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
    >
      Cancel
    </a>
  </div>
</form>
