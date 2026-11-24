<script lang="ts">
  import { enhance } from '$app/forms';
  import Button from '#lib/components/Button.svelte';
  import ConfirmDialog from '#lib/components/ConfirmDialog.svelte';
  import Notice from '#lib/components/Notice.svelte';
  import SelectField from '#lib/components/SelectField.svelte';
  import { formatRate } from '#lib/money.js';
  import type { Category, Direction, VatRate } from '#lib/types.js';

  interface Result {
    action: 'create' | 'update' | 'move' | 'delete';
    id?: number;
    direction?: Direction;
    errors: Record<string, string>;
    message?: string | null;
    values?: { name: string; default_vat_rate_bp: string };
  }

  interface Props {
    categories: Category[];
    rates: VatRate[];
    result: Result | null;
  }

  let { categories, rates, result }: Props = $props();

  let editingId = $state<number | null>(null);
  let deleteTarget = $state<Category | null>(null);
  let deleteOpen = $state(false);
  let reassignTo = $state('');

  const rateItems = $derived([
    { value: 'none', label: 'No VAT' },
    ...rates.map((r) => ({ value: String(r.rate_bp), label: formatRate(r.rate_bp) }))
  ]);

  const groups = $derived([
    {
      direction: 'income' as const,
      title: 'Income',
      items: categories.filter((c) => c.direction === 'income')
    },
    {
      direction: 'expense' as const,
      title: 'Expenses',
      items: categories.filter((c) => c.direction === 'expense')
    }
  ]);

  const usageTotal = (c: Category) => c.usage.entries + c.usage.templates + c.usage.counterparties;

  function usageText(c: Category): string {
    const parts: string[] = [];
    if (c.usage.entries)
      parts.push(`${c.usage.entries} ${c.usage.entries === 1 ? 'entry' : 'entries'}`);
    if (c.usage.templates)
      parts.push(
        `${c.usage.templates} recurring ${c.usage.templates === 1 ? 'template' : 'templates'}`
      );
    if (c.usage.counterparties)
      parts.push(
        `${c.usage.counterparties} ${c.usage.counterparties === 1 ? 'counterparty' : 'counterparties'} (default)`
      );
    return parts.join(', ');
  }

  const reassignItems = $derived(
    deleteTarget
      ? categories
          .filter((c) => c.direction === deleteTarget?.direction && c.id !== deleteTarget.id)
          .map((c) => ({ value: String(c.id), label: c.name }))
      : []
  );

  function askDelete(category: Category) {
    deleteTarget = category;
    reassignTo = '';
    deleteOpen = true;
  }

  // Stay in edit mode only while the server reports an error for that row.
  $effect(() => {
    if (result?.action === 'update' && Object.keys(result.errors).length === 0 && !result.message) {
      editingId = null;
    }
  });

  const rateValue = (bp: number | null) => (bp === null ? 'none' : String(bp));
  const inputClass =
    'min-h-[44px] w-full rounded-md border border-border bg-surface px-1.5 text-base focus:border-accent focus:outline-2 focus:outline-offset-1 focus:outline-accent aria-invalid:border-expense';
  const iconButton =
    'inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md text-sm text-muted hover:bg-nav hover:text-ink focus-visible:outline-2 focus-visible:outline-accent disabled:opacity-30';
</script>

<section
  aria-labelledby="settings-categories"
  class="rounded-xl border border-border bg-surface p-3 md:p-4"
>
  <h2 id="settings-categories" class="text-lg font-semibold">Categories</h2>
  <p class="mt-0.5 text-sm text-muted">
    Group your income and expenses. The default VAT rate is suggested on new lines.
  </p>

  {#if result?.message && (result.action === 'move' || result.action === 'delete')}
    <div class="mt-2"><Notice tone="error">{result.message}</Notice></div>
  {/if}

  <div class="mt-3 flex flex-col gap-4">
    {#each groups as group (group.direction)}
      <div>
        <h3 class="text-base font-semibold">{group.title}</h3>
        <ul class="mt-1 divide-y divide-border rounded-lg border border-border">
          {#each group.items as category, index (category.id)}
            {@const rowErrors =
              result?.action === 'update' && result.id === category.id ? result.errors : {}}
            <li class="px-1.5 py-1">
              {#if editingId === category.id}
                <form
                  method="POST"
                  action="?/updateCategory"
                  use:enhance={() =>
                    async ({ update }) =>
                      update({ reset: false })}
                  class="grid grid-cols-1 items-start gap-1 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_auto]"
                >
                  <input type="hidden" name="id" value={category.id} />
                  <div class="flex flex-col gap-0.5">
                    <label for="cat-name-{category.id}" class="text-xs font-medium text-muted">
                      Name
                    </label>
                    <input
                      id="cat-name-{category.id}"
                      name="name"
                      required
                      maxlength="120"
                      value={category.name}
                      aria-invalid={rowErrors.name ? 'true' : undefined}
                      class={inputClass}
                    />
                    {#if rowErrors.name}<p class="text-sm text-expense">{rowErrors.name}</p>{/if}
                  </div>
                  <SelectField
                    id="cat-rate-{category.id}"
                    label="Default VAT"
                    name="default_vat_rate_bp"
                    items={rateItems}
                    value={rateValue(category.default_vat_rate_bp)}
                    error={rowErrors.default_vat_rate_bp}
                  />
                  <div class="flex gap-0.5 sm:pt-[22px]">
                    <Button>Save</Button>
                    <Button type="button" variant="ghost" onclick={() => (editingId = null)}>
                      Cancel
                    </Button>
                  </div>
                </form>
                {#if result?.action === 'update' && result.id === category.id && result.message}
                  <p class="mt-1 text-sm text-expense">{result.message}</p>
                {/if}
              {:else}
                <div class="flex flex-wrap items-center justify-between gap-1">
                  <div class="min-w-0">
                    <p class="truncate font-medium">{category.name}</p>
                    <p class="text-xs text-muted">
                      {formatRate(category.default_vat_rate_bp)} ·
                      {usageTotal(category) === 0 ? 'Not used' : usageText(category)}
                    </p>
                  </div>
                  <div class="flex items-center">
                    <form method="POST" action="?/moveCategory" use:enhance>
                      <input type="hidden" name="id" value={category.id} />
                      <input type="hidden" name="direction" value={group.direction} />
                      <input type="hidden" name="step" value="up" />
                      <button
                        type="submit"
                        class={iconButton}
                        disabled={index === 0}
                        aria-label="Move {category.name} up"
                      >
                        ↑
                      </button>
                    </form>
                    <form method="POST" action="?/moveCategory" use:enhance>
                      <input type="hidden" name="id" value={category.id} />
                      <input type="hidden" name="direction" value={group.direction} />
                      <input type="hidden" name="step" value="down" />
                      <button
                        type="submit"
                        class={iconButton}
                        disabled={index === group.items.length - 1}
                        aria-label="Move {category.name} down"
                      >
                        ↓
                      </button>
                    </form>
                    <button
                      type="button"
                      class={[iconButton, 'px-1']}
                      onclick={() => (editingId = category.id)}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      class={[iconButton, 'px-1 hover:text-expense']}
                      onclick={() => askDelete(category)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              {/if}
            </li>
          {:else}
            <li class="px-1.5 py-1.5 text-sm text-muted">No categories yet.</li>
          {/each}
        </ul>

        {#key result}
          {@const createResult =
            result?.action === 'create' && result.direction === group.direction ? result : null}
          {@const failed =
            createResult && (Object.keys(createResult.errors).length > 0 || createResult.message)}
          <form
            method="POST"
            action="?/createCategory"
            use:enhance={() =>
              async ({ update }) =>
                update({ reset: false })}
            class="mt-1.5 grid grid-cols-1 items-start gap-1 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_auto]"
          >
            <input type="hidden" name="direction" value={group.direction} />
            <div class="flex flex-col gap-0.5">
              <label for="new-cat-{group.direction}" class="text-xs font-medium text-muted">
                New {group.direction === 'income' ? 'income' : 'expense'} category
              </label>
              <input
                id="new-cat-{group.direction}"
                name="name"
                required
                maxlength="120"
                value={failed ? (createResult?.values?.name ?? '') : ''}
                aria-invalid={failed && createResult?.errors.name ? 'true' : undefined}
                class={inputClass}
              />
              {#if failed && (createResult?.errors.name || createResult?.message)}
                <p class="text-sm text-expense">
                  {createResult?.errors.name ?? createResult?.message}
                </p>
              {/if}
            </div>
            <SelectField
              id="new-cat-rate-{group.direction}"
              label="Default VAT"
              name="default_vat_rate_bp"
              items={rateItems}
              value={failed
                ? (createResult?.values?.default_vat_rate_bp ?? 'none')
                : group.direction === 'income'
                  ? String(rates[0]?.rate_bp ?? 'none')
                  : 'none'}
            />
            <div class="sm:pt-[22px]">
              <Button variant="ghost" class="border border-border">Add category</Button>
            </div>
          </form>
        {/key}
      </div>
    {/each}
  </div>
</section>

{#if deleteTarget}
  {@const target = deleteTarget}
  <ConfirmDialog bind:open={deleteOpen} title="Delete “{target.name}”?">
    {#snippet description()}
      {#if usageTotal(target) === 0}
        This category isn’t used. It will be deleted.
      {:else}
        This category is used by {usageText(target)}. Choose where to move them; then the category
        is deleted.
      {/if}
    {/snippet}
    {#if usageTotal(target) > 0}
      <SelectField
        id="reassign-to"
        label="Move them to"
        items={reassignItems}
        bind:value={reassignTo}
        placeholder="Choose a category"
      />
    {/if}
    {#snippet action()}
      <form
        method="POST"
        action="?/deleteCategory"
        use:enhance={() => {
          deleteOpen = false;
          return async ({ update }) => update();
        }}
      >
        <input type="hidden" name="id" value={target.id} />
        <input type="hidden" name="reassign_to" value={reassignTo} />
        <button
          type="submit"
          disabled={usageTotal(target) > 0 && !reassignTo}
          class="inline-flex min-h-[44px] items-center rounded-md bg-expense px-2.5 text-sm font-medium text-white hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-50"
        >
          {usageTotal(target) > 0 ? 'Move and delete' : 'Delete'}
        </button>
      </form>
    {/snippet}
  </ConfirmDialog>
{/if}
