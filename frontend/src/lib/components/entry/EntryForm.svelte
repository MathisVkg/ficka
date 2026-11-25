<script lang="ts" module>
  /** Field key from the API (`lines.0.gross_cents`) → id of the input to focus. */
  export function fieldId(key: string, linesMode: boolean): string {
    const line = /^lines\.(\d+)\.(\w+)$/.exec(key);
    if (line) {
      if (!linesMode) return line[2] === 'vat_rate_bp' ? 'entry-vat-rate' : 'entry-amount';
      const part = line[2] === 'vat_rate_bp' ? 'rate' : line[2] === 'vat_cents' ? 'vat' : 'amount';
      return `line-${line[1]}-${part}`;
    }
    if (key === 'lines') return linesMode ? 'lines-editor' : 'entry-amount';
    if (key === 'payment.paid_on') return 'entry-paid-on';
    return `entry-${key.replaceAll('_', '-')}`;
  }
</script>

<script lang="ts">
  import { onMount, untrack, type Snippet } from 'svelte';
  import { enhance } from '$app/forms';
  import Button from '#lib/components/Button.svelte';
  import Card from '#lib/components/layout/Card.svelte';
  import Field from '#lib/components/layout/Field.svelte';
  import FormGrid from '#lib/components/layout/FormGrid.svelte';
  import { buttonClass, checkboxClass, controlClass } from '#lib/components/layout/styles.js';
  import ConfirmDialog from '#lib/components/ConfirmDialog.svelte';
  import Notice from '#lib/components/Notice.svelte';
  import PaymentBadge from '#lib/components/PaymentBadge.svelte';
  import SelectField from '#lib/components/SelectField.svelte';
  import SourceIcon from '#lib/components/SourceIcon.svelte';
  import CounterpartyCombobox from '#lib/components/entry/CounterpartyCombobox.svelte';
  import { todayIso } from '#lib/dates.js';
  import {
    categoryRateSource,
    categoryWins,
    rateWins,
    type CategorySource,
    type RateSource
  } from '#lib/entry-defaults.js';
  import { canShowSimply, needsLinesEditor } from '#lib/entry-mode.js';
  import {
    centsToInput,
    computeLine,
    formatCents,
    formatDate,
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
    PaymentInstruction,
    PaymentStatus,
    Suggestion,
    VatRate
  } from '#lib/types.js';

  interface Props {
    entry?: Entry | null;
    categories: Category[];
    rates: VatRate[];
    /** Field errors and message returned by the action, keyed like the API. */
    serverErrors?: Record<string, string>;
    serverMessage?: string | null;
    action?: string;
    /** For "Save and add another": the direction and date to start from. */
    initialDirection?: Direction | null;
    initialDate?: string | null;
    /** Rendered under More details, outside the form (e.g. the payments block). */
    details?: Snippet;
    /** Where Cancel goes, and where the action returns after saving (validated). */
    cancelHref: string;
    /** Existing entries: opens the delete dialog (the button sits in the summary card). */
    ondelete?: () => void;
  }

  let {
    entry = null,
    categories,
    rates: initialRates,
    serverErrors = {},
    serverMessage = null,
    action,
    initialDirection = null,
    initialDate = null,
    details,
    cancelHref,
    ondelete
  }: Props = $props();

  const DIRECTION_KEY = 'ficka.entry.direction';
  const RATE_KEY = 'ficka.entry.vatRate';

  function stored(key: string): string | null {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  }

  function store(key: string, value: string) {
    try {
      localStorage.setItem(key, value);
    } catch {
      // Private mode or storage disabled: nothing to remember, the form still works.
    }
  }

  // --- State: props are read once (the page re-mounts the form after a save) -----------

  interface LineState {
    key: number;
    description: string;
    amountText: string;
    rate: string; // 'none' or basis points
    vatText: string;
    vatManual: boolean;
    rateTouched: boolean;
  }

  const initial = untrack(() => ({
    entry,
    rates: initialRates,
    direction: initialDirection,
    date: initialDate
  }));
  const start = initial.entry;
  const isNew = !start;
  const startedSimple = start ? canShowSimply(start) : true;
  const startPaid = start
    ? start.payments.length > 0 && start.paid_cents >= start.total_gross_cents
    : true;

  let nextKey = 0;
  let rates = $state<VatRate[]>(initial.rates);
  let direction = $state<Direction>(start?.direction ?? initial.direction ?? 'expense');
  const startDate = start?.invoice_date ?? initial.date ?? todayIso();
  let invoiceDate = $state(startDate);

  // Simple mode: one amount incl. VAT and one rate.
  const firstLine = start?.lines[0];
  let amountText = $state(firstLine ? centsToInput(firstLine.gross_cents) : '');
  let rate = $state(
    firstLine
      ? firstLine.vat_rate_bp === null
        ? 'none'
        : String(firstLine.vat_rate_bp)
      : initial.rates.length
        ? String(initial.rates[0].rate_bp)
        : 'none'
  );
  let rateSource = $state<RateSource>(start ? 'user' : 'default');

  // Lines mode: the TASK-003 lines editor.
  let linesMode = $state(start ? needsLinesEditor(start) : false);
  let amountsIncludeVat = $state(start ? start.amounts_include_vat : true);
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
      : []
  );

  let counterparty = $state<CounterpartyChoice | null>(
    start?.counterparty
      ? { ...start.counterparty, default_category_id: null, default_vat_rate_bp: null }
      : null
  );
  let categoryId = $state(start?.category ? String(start.category.id) : '');
  let categorySource = $state<CategorySource | null>(start?.category ? 'user' : null);
  let description = $state(start?.description ?? '');

  let paid = $state(startPaid);
  let paidTouched = $state(false);
  let paidOn = $state(start?.payments.length === 1 ? start.payments[0].paid_on : startDate);
  let paidOnTouched = $state(Boolean(start && start.payments.length === 1));
  let dueDate = $state(start?.due_date ?? '');

  let detailsOpen = $state(!startedSimple);
  let invoiceNumber = $state(start?.invoice_number ?? '');
  let structuredReference = $state(start?.structured_reference ?? '');
  let documentLocation = $state(start?.document_location ?? '');

  let clientErrors = $state<Record<string, string>>({});
  let submitted = $state(false);
  let submitting = $state(false);
  let ratesLoading = $state(false);
  let confirmUnpaidOpen = $state(false);
  let unpaidConfirmed = $state(false);
  let formElement = $state<HTMLFormElement>();
  let lastSubmitter: HTMLElement | null = null;

  onMount(() => {
    if (isNew && !initial.direction) {
      const last = stored(DIRECTION_KEY);
      if (last === 'income' || last === 'expense') direction = last;
    }
    if (isNew) {
      const last = stored(RATE_KEY);
      const valid = last === 'none' || rates.some((r) => String(r.rate_bp) === last);
      if (last && valid && rateSource === 'default') {
        rate = last;
        rateSource = 'last';
      }
    }
  });

  // --- Derived --------------------------------------------------------------------------

  const validRates = $derived(new Set(rates.map((r) => r.rate_bp)));
  const rateItems = $derived([
    ...rates.map((r) => ({ value: String(r.rate_bp), label: formatRate(r.rate_bp) })),
    { value: 'none', label: 'No VAT' }
  ]);
  function rateItemsWith(value: string) {
    return rateItems.some((i) => i.value === value)
      ? rateItems
      : [...rateItems, { value, label: `${formatRate(Number(value))} (not valid on this date)` }];
  }
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

  function rateError(value: string): string | undefined {
    if (value === 'none') return undefined;
    const bp = Number(value);
    return validRates.has(bp) ? undefined : `${formatRate(bp)} isn’t valid on this date.`;
  }

  function evaluate(
    text: string,
    rateValue: string,
    includeVat: boolean,
    manual: boolean,
    vatText: string
  ): Evaluated {
    const errors: Evaluated['errors'] = {};
    const parsed = parseAmount(text);
    const rateBp = rateValue === 'none' ? null : Number(rateValue);
    const invalidRate = rateError(rateValue);
    if (invalidRate) errors.rate = invalidRate;
    if (!parsed.ok) {
      errors.amount = parsed.error;
      return { amounts: null, errors };
    }
    let vatCents: number | null = null;
    if (manual && rateBp !== null) {
      const vat = parseAmount(vatText);
      if (!vat.ok) {
        errors.vat = vat.error;
        return { amounts: null, errors };
      }
      vatCents = vat.cents;
    }
    try {
      return {
        amounts: computeLine(parsed.cents, rateBp, {
          amountsIncludeVat: includeVat,
          vatManual: manual && rateBp !== null,
          vatCents
        }),
        errors
      };
    } catch (error) {
      if (!(error instanceof VatError)) throw error;
      const part =
        error.field === 'vat_cents' ? 'vat' : error.field === 'vat_rate_bp' ? 'rate' : 'amount';
      errors[part] = error.message;
      return { amounts: null, errors };
    }
  }

  const simple = $derived(evaluate(amountText, rate, true, false, ''));
  const evaluatedLines = $derived(
    lines.map((l) => evaluate(l.amountText, l.rate, amountsIncludeVat, l.vatManual, l.vatText))
  );
  const totals = $derived(
    linesMode
      ? evaluatedLines.reduce(
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
      : simple.amounts
        ? {
            net: simple.amounts.netCents,
            vat: simple.amounts.vatCents,
            gross: simple.amounts.grossCents
          }
        : { net: 0, vat: 0, gross: 0 }
  );

  // Partial or several payments: unless the user touches "Paid", leave them as they are.
  const hasComplexPayments = Boolean(
    start && (start.payments.length > 1 || (start.paid_cents > 0 && !startPaid))
  );

  const paymentInstruction = $derived<PaymentInstruction>(
    hasComplexPayments && !paidTouched
      ? { mode: 'keep' }
      : paid
        ? { mode: 'paid', paid_on: paidOn }
        : { mode: 'unpaid' }
  );

  const previewStatus = $derived<PaymentStatus>(
    paymentInstruction.mode === 'keep' && start
      ? start.payment_status
      : paid
        ? 'paid'
        : dueDate && dueDate < todayIso()
          ? 'overdue'
          : 'unpaid'
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
    amounts_include_vat: linesMode ? amountsIncludeVat : true,
    document_location: documentLocation.trim() || null,
    payment: paymentInstruction,
    lines: linesMode
      ? lines.map((line) => {
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
      : [
          {
            description: start && start.lines.length === 1 ? start.lines[0].description : null,
            ...(simple.amounts ? { gross_cents: simple.amounts.grossCents } : {}),
            vat_rate_bp: rate === 'none' ? null : Number(rate),
            vat_manual: false
          }
        ]
  });

  const errors = $derived<Record<string, string>>(submitted ? clientErrors : serverErrors);
  const errorList = $derived(Object.entries(errors));

  function lineError(index: number, part: 'amount' | 'vat' | 'rate'): string | undefined {
    if (part === 'rate') return errors[`lines.${index}.vat_rate_bp`];
    if (part === 'vat') return errors[`lines.${index}.vat_cents`];
    return errors[`lines.${index}.gross_cents`] ?? errors[`lines.${index}.net_cents`];
  }

  const LABELS: Record<string, string> = {
    invoice_date: 'Date',
    due_date: 'Expected on',
    counterparty_id: 'Counterparty',
    category_id: 'Category',
    description: 'Description',
    invoice_number: 'Invoice number',
    structured_reference: 'Structured reference',
    document_location: 'Document location',
    'payment.paid_on': 'Paid on',
    'payment.mode': 'Paid',
    lines: 'Amount'
  };

  function labelFor(key: string): string {
    const line = /^lines\.(\d+)\.(\w+)$/.exec(key);
    if (line) {
      const part =
        line[2] === 'vat_rate_bp' ? 'VAT rate' : line[2] === 'vat_cents' ? 'VAT amount' : 'Amount';
      return linesMode ? `Line ${Number(line[1]) + 1}, ${part.toLowerCase()}` : part;
    }
    return LABELS[key] ?? key;
  }

  // --- Defaults and suggestions (priority rules: #lib/entry-defaults.ts) -------------------

  function setRate(value: string, source: RateSource) {
    if (linesMode) {
      lines = lines.map((line) =>
        line.rateTouched ? line : { ...line, rate: value, vatManual: false }
      );
      return;
    }
    if (rateWins(rateSource, source)) {
      rate = value;
      rateSource = source;
    }
  }

  function rateOfCategory(category: Category): string {
    return category.default_vat_rate_bp === null ? 'none' : String(category.default_vat_rate_bp);
  }

  function setCategory(id: number | null, source: CategorySource) {
    if (id === null) return;
    const category = categories.find((c) => c.id === id && c.direction === direction);
    if (!category || !categoryWins(categorySource, source)) return;
    categoryId = String(category.id);
    categorySource = source;
    setRate(rateOfCategory(category), categoryRateSource(source));
  }

  async function fetchSuggestion(params: { counterpartyId?: number; description?: string }) {
    const parts = [`direction=${direction}`];
    if (params.counterpartyId) parts.push(`counterparty_id=${params.counterpartyId}`);
    if (params.description) parts.push(`description=${encodeURIComponent(params.description)}`);
    try {
      const response = await fetch(`/entries/suggestion?${parts.join('&')}`);
      if (!response.ok) return;
      const suggestion = (await response.json()) as Suggestion;
      if (suggestion.category_id !== null) setCategory(suggestion.category_id, 'suggestion');
      if (suggestion.matched_on) {
        setRate(
          suggestion.vat_rate_bp === null ? 'none' : String(suggestion.vat_rate_bp),
          'suggestion'
        );
      }
    } catch {
      // Suggestions are a convenience; the form works without them.
    }
  }

  function onCounterparty(choice: CounterpartyChoice | null) {
    if (!choice) return;
    // Counterparty defaults first (lowest priority); the suggestion can override them.
    if (choice.default_category_id !== null) {
      setCategory(choice.default_category_id, 'counterparty');
    }
    if (choice.default_vat_rate_bp !== null) {
      setRate(String(choice.default_vat_rate_bp), 'counterparty');
    }
    void fetchSuggestion({ counterpartyId: choice.id });
  }

  function onDescriptionBlur() {
    if (description.trim() && !counterparty) {
      void fetchSuggestion({ description: description.trim() });
    }
  }

  function onCategory(value: string) {
    categorySource = value ? 'user' : null;
    const category = categories.find((c) => String(c.id) === value);
    // A category picked by hand beats a suggested rate (but not a rate typed by hand).
    if (category) setRate(rateOfCategory(category), 'userCategory');
  }

  // --- Actions --------------------------------------------------------------------------

  function setDirection(next: Direction) {
    if (next === direction) return;
    direction = next;
    if (isNew) store(DIRECTION_KEY, next);
    const category = categories.find((c) => String(c.id) === categoryId);
    if (category && category.direction !== next) {
      categoryId = '';
      categorySource = null;
    }
  }

  async function onInvoiceDate() {
    if (!paidOnTouched) paidOn = invoiceDate;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(invoiceDate)) return;
    ratesLoading = true;
    try {
      const response = await fetch(`/entries/vat-rates?on=${invoiceDate}`);
      if (response.ok) rates = (await response.json()) as VatRate[];
    } finally {
      ratesLoading = false;
    }
  }

  function switchToLines() {
    lines = [
      {
        key: nextKey++,
        description: '',
        amountText,
        rate,
        vatText: '',
        vatManual: false,
        rateTouched: rateSource === 'user'
      }
    ];
    amountsIncludeVat = true;
    linesMode = true;
    detailsOpen = true;
  }

  const canGoBackToSimple = $derived(
    linesMode && lines.length === 1 && amountsIncludeVat && !lines[0].vatManual
  );

  function backToSimple() {
    amountText = lines[0].amountText;
    rate = lines[0].rate;
    rateSource = 'user';
    linesMode = false;
  }

  function newLine(): LineState {
    const category = categories.find((c) => String(c.id) === categoryId);
    const lineRate = category
      ? rateOfCategory(category)
      : rates.length
        ? String(rates[0].rate_bp)
        : 'none';
    return {
      key: nextKey++,
      description: '',
      amountText: '',
      rate: lineRate,
      vatText: '',
      vatManual: false,
      rateTouched: false
    };
  }

  function setLinesVatMode(includeVat: boolean) {
    if (includeVat === amountsIncludeVat) return;
    lines = lines.map((line, index) => {
      const amounts = evaluatedLines[index].amounts;
      return amounts
        ? {
            ...line,
            amountText: centsToInput(includeVat ? amounts.grossCents : amounts.netCents)
          }
        : line;
    });
    amountsIncludeVat = includeVat;
  }

  function validate(): Record<string, string> {
    const found: Record<string, string> = {};
    if (!invoiceDate) found.invoice_date = 'Enter the date.';
    if (!paid && dueDate && invoiceDate && dueDate < invoiceDate) {
      found.due_date = 'The expected date can’t be before the date.';
    }
    if (paymentInstruction.mode === 'paid' && !paidOn) {
      found['payment.paid_on'] = 'Enter the payment date.';
    }
    if (linesMode) {
      if (lines.length === 0) found.lines = 'Add at least one line.';
      evaluatedLines.forEach((e, index) => {
        const key = `lines.${index}.${amountsIncludeVat ? 'gross_cents' : 'net_cents'}`;
        if (e.errors.amount) found[key] = e.errors.amount;
        if (e.errors.rate) found[`lines.${index}.vat_rate_bp`] = e.errors.rate;
        if (e.errors.vat) found[`lines.${index}.vat_cents`] = e.errors.vat;
      });
    } else {
      if (simple.errors.amount) found['lines.0.gross_cents'] = simple.errors.amount;
      if (simple.errors.rate) found['lines.0.vat_rate_bp'] = simple.errors.rate;
    }
    return found;
  }

  function focusSummary() {
    requestAnimationFrame(() => document.getElementById('entry-errors')?.focus());
  }

  /** Enter saves from any field: native for text inputs, added here for the checkbox. */
  function submitOnEnter(event: KeyboardEvent) {
    if (event.key !== 'Enter') return;
    event.preventDefault();
    formElement?.requestSubmit();
  }

  function confirmUnpaid() {
    unpaidConfirmed = true;
    confirmUnpaidOpen = false;
    formElement?.requestSubmit(
      lastSubmitter instanceof HTMLButtonElement ? lastSubmitter : undefined
    );
  }

  const removedPaymentsText = $derived(
    start && start.paid_cents > 0
      ? start.payments.length === 1
        ? `This will remove the recorded payment of ${formatCents(start.paid_cents)}.`
        : `This will remove the ${start.payments.length} recorded payments (${formatCents(start.paid_cents)}).`
      : ''
  );
</script>

<!-- Form column and summary column start on the same top line. -->
<div
  class="grid grid-cols-1 items-start gap-3 min-[1200px]:grid-cols-[minmax(0,1fr)_360px] min-[1600px]:grid-cols-[minmax(0,1fr)_400px]"
>
  <Card label="Entry">
    <form
      id="entry-form"
      bind:this={formElement}
      method="POST"
      {action}
      class="flex flex-col gap-3"
      novalidate
      use:enhance={({ cancel, submitter }) => {
        lastSubmitter = submitter;
        clientErrors = validate();
        submitted = true;
        if (Object.keys(clientErrors).length > 0) {
          cancel();
          focusSummary();
          return;
        }
        submitted = false;
        if (
          paymentInstruction.mode === 'unpaid' &&
          start &&
          start.paid_cents > 0 &&
          !unpaidConfirmed
        ) {
          cancel();
          confirmUnpaidOpen = true;
          return;
        }
        submitting = true;
        store(RATE_KEY, linesMode ? (lines[0]?.rate ?? rate) : rate);
        return async ({ result, update }) => {
          await update({ reset: false });
          submitting = false;
          unpaidConfirmed = false;
          if (result.type === 'failure') focusSummary();
        };
      }}
    >
      <input type="hidden" name="payload" value={JSON.stringify(payload)} />
      <input type="hidden" name="from" value={cancelHref} />

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
                  <a
                    class="underline underline-offset-2 hover:text-ink"
                    href="#{fieldId(key, linesMode)}"
                  >
                    {labelFor(key)}: {message}
                  </a>
                </li>
              {/each}
            </ul>
          {/if}
        </Notice>
      {/if}

      <!-- First row: Expense / Income -->
      <div
        id="entry-direction"
        class="inline-flex w-fit rounded-lg border border-border bg-bg p-0.5"
        role="radiogroup"
        aria-label="Type"
      >
        {#each [{ value: 'expense', label: 'Expense' }, { value: 'income', label: 'Income' }] as option (option.value)}
          <label
            class={[
              'inline-flex h-[40px] cursor-pointer items-center rounded-md px-2.5 text-sm font-medium transition-colors duration-150 ease-out has-focus-visible:outline-2 has-focus-visible:outline-accent',
              direction === option.value
                ? option.value === 'income'
                  ? 'bg-surface text-income shadow-[0_0_0_1px_var(--color-border)]'
                  : 'bg-surface text-ink shadow-[0_0_0_1px_var(--color-border)]'
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

      <!-- Date, amount (with live VAT as its hint), VAT rate -->
      <FormGrid columns={3}>
        <Field label="Date" for="entry-invoice-date" error={errors.invoice_date}>
          <input
            id="entry-invoice-date"
            type="date"
            required
            bind:value={invoiceDate}
            onchange={onInvoiceDate}
            aria-invalid={errors.invoice_date ? 'true' : undefined}
            class={controlClass}
          />
        </Field>

        {#if !linesMode}
          {@const amountError =
            errors['lines.0.gross_cents'] ??
            errors.lines ??
            (amountText ? simple.errors.amount : undefined)}
          <Field label="Amount (incl. VAT)" for="entry-amount" error={amountError}>
            <input
              id="entry-amount"
              inputmode="decimal"
              autocomplete="off"
              placeholder="0,00"
              bind:value={amountText}
              aria-invalid={amountError ? 'true' : undefined}
              aria-describedby="entry-amount-hint"
              class={[controlClass, 'text-right amount']}
            />
            {#snippet hintContent()}
              <span class="amount" aria-live="polite">
                VAT {formatCents(totals.vat)} · excl. {formatCents(totals.net)}
              </span>
            {/snippet}
          </Field>
          <SelectField
            id="entry-vat-rate"
            label="VAT rate"
            items={rateItemsWith(rate)}
            bind:value={rate}
            error={errors['lines.0.vat_rate_bp'] ?? simple.errors.rate}
            hint={rateSource === 'suggestion' ? 'Suggested from a similar entry' : null}
            onchange={() => (rateSource = 'user')}
          />
        {:else}
          <p class="text-sm text-muted sm:col-span-1 xl:col-span-2 xl:pt-[22px]">
            Several lines: the amounts are in the lines below.
          </p>
        {/if}
      </FormGrid>
      {#if ratesLoading}<p class="text-xs text-muted">Loading the VAT rates…</p>{/if}

      <!-- Category, counterparty, description -->
      <FormGrid columns={3}>
        <SelectField
          id="entry-category-id"
          label="Category"
          items={categoryItems}
          bind:value={categoryId}
          placeholder="No category"
          error={errors.category_id}
          hint={categorySource === 'suggestion' ? 'Suggested from a similar entry' : null}
          onchange={onCategory}
        />
        <CounterpartyCombobox
          id="entry-counterparty-id"
          label="Counterparty (optional)"
          bind:value={counterparty}
          createRole={direction === 'income' ? 'customer' : 'supplier'}
          error={errors.counterparty_id}
          onselect={onCounterparty}
        />
        <Field label="Description (optional)" for="entry-description">
          <input
            id="entry-description"
            maxlength="500"
            bind:value={description}
            onblur={onDescriptionBlur}
            class={controlClass}
          />
        </Field>
      </FormGrid>

      <!-- Paid: the checkbox sits on a 44px row aligned with the controls next to it. -->
      <FormGrid columns={3}>
        <div class="flex flex-col gap-0.5">
          <div class="min-h-[20px]" aria-hidden="true"></div>
          <label class="flex h-[44px] w-fit cursor-pointer items-center gap-1 text-sm font-medium">
            <input
              id="entry-paid"
              type="checkbox"
              bind:checked={paid}
              onchange={() => (paidTouched = true)}
              onkeydown={submitOnEnter}
              class={checkboxClass}
            />
            Paid
          </label>
        </div>
        {#if !paid}
          <Field label="Expected on" for="entry-due-date" error={errors.due_date}>
            <input
              id="entry-due-date"
              type="date"
              bind:value={dueDate}
              min={invoiceDate}
              aria-invalid={errors.due_date ? 'true' : undefined}
              class={controlClass}
            />
          </Field>
        {:else if hasComplexPayments && !paidTouched}
          <p class="text-sm text-muted sm:pt-[34px]">The payments are listed under More details.</p>
        {/if}
      </FormGrid>

      <!-- More details: a disclosure at the bottom of the same card. -->
      <div class="border-t border-border pt-2">
        <button
          type="button"
          aria-expanded={detailsOpen}
          aria-controls="entry-details"
          onclick={() => (detailsOpen = !detailsOpen)}
          class="-ml-1 inline-flex h-[44px] items-center gap-1 rounded-md px-1 text-sm font-medium text-ink hover:bg-nav focus-visible:outline-2 focus-visible:outline-accent"
        >
          <span
            aria-hidden="true"
            class={['inline-block transition-transform duration-150', detailsOpen && 'rotate-90']}
          >
            ▸
          </span>
          More details
        </button>

        <div id="entry-details" hidden={!detailsOpen} class="mt-2 flex flex-col gap-3">
          <FormGrid columns={3}>
            {#if paymentInstruction.mode === 'paid'}
              <Field label="Paid on" for="entry-paid-on" error={errors['payment.paid_on']}>
                <input
                  id="entry-paid-on"
                  type="date"
                  bind:value={paidOn}
                  oninput={() => (paidOnTouched = true)}
                  aria-invalid={errors['payment.paid_on'] ? 'true' : undefined}
                  class={controlClass}
                />
              </Field>
            {/if}
            {#if paid && dueDate}
              <Field label="Due date" for="entry-due-date-details">
                <input
                  id="entry-due-date-details"
                  type="date"
                  bind:value={dueDate}
                  min={invoiceDate}
                  class={controlClass}
                />
              </Field>
            {/if}
            <Field label="Invoice number" for="entry-invoice-number">
              <input
                id="entry-invoice-number"
                maxlength="100"
                bind:value={invoiceNumber}
                class={controlClass}
              />
            </Field>
            <Field
              label="Structured reference"
              for="entry-structured-reference"
              error={errors.structured_reference}
            >
              <input
                id="entry-structured-reference"
                maxlength="40"
                inputmode="numeric"
                placeholder="+++090/9337/55493+++"
                bind:value={structuredReference}
                aria-invalid={errors.structured_reference ? 'true' : undefined}
                class={controlClass}
              />
            </Field>
            <Field label="Document location" for="entry-document-location">
              <input
                id="entry-document-location"
                maxlength="2000"
                placeholder="A link or a folder"
                bind:value={documentLocation}
                class={controlClass}
              />
            </Field>
          </FormGrid>

          {#if !linesMode}
            <div>
              <button
                type="button"
                onclick={switchToLines}
                class="-ml-0.5 h-[44px] rounded-md px-0.5 text-sm font-medium text-accent hover:underline focus-visible:outline-2 focus-visible:outline-accent"
              >
                Split into several lines
              </button>
            </div>
          {:else}
            <!-- Lines editor (TASK-003) -->
            <div
              id="lines-editor"
              tabindex="-1"
              class="outline-none"
              role="group"
              aria-labelledby="lines-heading"
            >
              <div class="flex flex-wrap items-center justify-between gap-2">
                <h2 id="lines-heading" class="text-base font-semibold">Lines</h2>
                <div class="flex flex-wrap items-center gap-2">
                  <label class="flex h-[44px] cursor-pointer items-center gap-1 text-sm">
                    <input
                      type="checkbox"
                      checked={amountsIncludeVat}
                      onchange={(e) => setLinesVatMode(e.currentTarget.checked)}
                      class={checkboxClass}
                    />
                    Amounts include VAT
                  </label>
                  {#if canGoBackToSimple}
                    <button
                      type="button"
                      onclick={backToSimple}
                      class="h-[44px] text-sm font-medium text-accent hover:underline focus-visible:outline-2 focus-visible:outline-accent"
                    >
                      Back to a single amount
                    </button>
                  {/if}
                </div>
              </div>
              {#if errors.lines}<p class="mt-1 text-sm text-expense">{errors.lines}</p>{/if}

              <div class="mt-2 flex flex-col gap-2">
                {#each lines as line, index (line.key)}
                  {@const result = evaluatedLines[index]}
                  {@const amountError =
                    lineError(index, 'amount') ??
                    (line.amountText ? result.errors.amount : undefined)}
                  {@const vatError = lineError(index, 'vat') ?? result.errors.vat}
                  <div
                    class="grid grid-cols-1 items-start gap-2 rounded-lg border border-border p-2 sm:grid-cols-2 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_44px]"
                  >
                    <Field label="Description" for="line-{index}-description">
                      <input
                        id="line-{index}-description"
                        bind:value={line.description}
                        maxlength="500"
                        class={controlClass}
                      />
                    </Field>
                    <Field
                      label={amountsIncludeVat ? 'Amount incl. VAT' : 'Amount excl. VAT'}
                      for="line-{index}-amount"
                      error={amountError}
                    >
                      <input
                        id="line-{index}-amount"
                        inputmode="decimal"
                        autocomplete="off"
                        placeholder="0,00"
                        bind:value={line.amountText}
                        aria-invalid={amountError ? 'true' : undefined}
                        class={[controlClass, 'text-right amount']}
                      />
                    </Field>
                    <SelectField
                      id="line-{index}-rate"
                      label="VAT rate"
                      items={rateItemsWith(line.rate)}
                      bind:value={line.rate}
                      error={lineError(index, 'rate') ?? result.errors.rate}
                      onchange={() => {
                        lines[index] = { ...lines[index], rateTouched: true, vatManual: false };
                      }}
                    />
                    <Field label="VAT" for="line-{index}-vat" error={vatError}>
                      {#snippet labelExtra()}
                        {#if line.vatManual && line.rate !== 'none'}
                          <span class="rounded-full bg-warning/10 px-0.5 text-xs text-warning">
                            manual
                          </span>
                          <button
                            type="button"
                            class="rounded-md px-0.5 text-xs font-medium text-accent hover:underline focus-visible:outline-2 focus-visible:outline-accent"
                            onclick={() => (lines[index] = { ...lines[index], vatManual: false })}
                          >
                            ↺ Recalculate
                          </button>
                        {/if}
                      {/snippet}
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
                        oninput={(e) =>
                          (lines[index] = {
                            ...lines[index],
                            vatText: e.currentTarget.value,
                            vatManual: true
                          })}
                        aria-invalid={vatError ? 'true' : undefined}
                        class={[controlClass, 'text-right amount']}
                      />
                    </Field>
                    <div class="xl:pt-[22px]">
                      <button
                        type="button"
                        aria-label="Remove line {index + 1}"
                        disabled={lines.length === 1}
                        onclick={() => (lines = lines.filter((_, i) => i !== index))}
                        class="inline-flex h-[44px] w-[44px] items-center justify-center rounded-md text-muted hover:bg-nav hover:text-expense focus-visible:outline-2 focus-visible:outline-accent disabled:opacity-40"
                      >
                        ×
                      </button>
                    </div>
                  </div>
                {/each}
              </div>
              <div class="mt-2">
                <Button
                  type="button"
                  variant="secondary"
                  onclick={() => (lines = [...lines, newLine()])}
                >
                  Add line
                </Button>
              </div>
            </div>
          {/if}
        </div>
      </div>
    </form>

    {#if detailsOpen && details}
      <div class="mt-3">{@render details()}</div>
    {/if}
  </Card>

  <!-- Summary and actions: sticky on wide screens, at the bottom otherwise. -->
  <aside
    aria-label="Summary"
    class="flex flex-col gap-2 rounded-xl border border-border bg-surface p-2 min-[1200px]:sticky min-[1200px]:top-4 md:p-3"
  >
    <div>
      <p class="text-sm text-muted">{direction === 'income' ? 'Income' : 'Expense'}</p>
      <p
        class={[
          'mt-0.5 text-3xl font-semibold tracking-tight amount',
          direction === 'income' && 'text-income'
        ]}
      >
        {formatCents(totals.gross)}
      </p>
    </div>
    <dl class="flex flex-col gap-0.5 text-sm">
      <div class="flex justify-between">
        <dt class="text-muted">Excl. VAT</dt>
        <dd class="amount">{formatCents(totals.net)}</dd>
      </div>
      <div class="flex justify-between">
        <dt class="text-muted">VAT</dt>
        <dd class="amount">{formatCents(totals.vat)}</dd>
      </div>
      <div class="flex items-center justify-between">
        <dt class="text-muted">Payment</dt>
        <dd><PaymentBadge status={previewStatus} /></dd>
      </div>
    </dl>
    <div class="flex flex-col gap-1">
      <Button form="entry-form" disabled={submitting}>{submitting ? 'Saving…' : 'Save'}</Button>
      {#if isNew}
        <Button
          form="entry-form"
          name="then"
          value="another"
          variant="secondary"
          disabled={submitting}
        >
          Save and add another
        </Button>
      {/if}
      <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- cancelHref is a validated, resolve()d path -->
      <a href={cancelHref} class={buttonClass('ghost')}>Cancel</a>
    </div>
    {#if start && ondelete}
      <div class="border-t border-border pt-2">
        <Button type="button" variant="danger" class="w-full" onclick={ondelete}>
          <svg
            aria-hidden="true"
            viewBox="0 0 16 16"
            class="size-2"
            fill="none"
            stroke="currentColor"
            stroke-width="1.4"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M2.5 4h11M6 4V2.5h4V4M4 4l.7 9.5h6.6L12 4M6.5 6.5v5M9.5 6.5v5" />
          </svg>
          Delete entry
        </Button>
      </div>
    {/if}
    {#if start}
      <dl class="flex flex-col gap-0.5 border-t border-border pt-1.5 text-xs text-muted">
        <div class="flex items-center justify-between gap-1">
          <dt>Source</dt>
          <dd class="flex items-center gap-0.5">
            <SourceIcon source={start.source} />
            {start.source}
          </dd>
        </div>
        <div class="flex justify-between gap-1">
          <dt>Created</dt>
          <dd class="amount">{formatDate(start.created_at)}</dd>
        </div>
        <div class="flex justify-between gap-1">
          <dt>Updated</dt>
          <dd class="amount">{formatDate(start.updated_at)}</dd>
        </div>
      </dl>
    {/if}
  </aside>
</div>

<ConfirmDialog bind:open={confirmUnpaidOpen} title="Mark as not paid?">
  {#snippet description()}
    {removedPaymentsText} The entry will show as expected until a payment is recorded.
  {/snippet}
  {#snippet action()}
    <Button type="button" variant="danger-solid" onclick={confirmUnpaid}>Remove and save</Button>
  {/snippet}
</ConfirmDialog>
