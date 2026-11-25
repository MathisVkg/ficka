<script lang="ts">
  import { tick } from 'svelte';
  import { Dialog, DropdownMenu } from 'bits-ui';
  import { enhance } from '$app/forms';
  import Button from '#lib/components/Button.svelte';
  import ConfirmDialog from '#lib/components/ConfirmDialog.svelte';
  import Notice from '#lib/components/Notice.svelte';
  import SelectField from '#lib/components/SelectField.svelte';
  import TextField from '#lib/components/TextField.svelte';
  import Card from '#lib/components/layout/Card.svelte';
  import { buttonClass, controlClass } from '#lib/components/layout/styles.js';
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
  let addDirection = $state<Direction | null>(null);
  let addOpen = $state(false);
  let addRate = $state('none');

  // One hidden form performs the menu's Move up / Move down.
  let moveForm = $state<HTMLFormElement>();
  let move = $state<{ id: number; direction: Direction; step: string }>({
    id: 0,
    direction: 'expense',
    step: 'up'
  });

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

  function plural(n: number, one: string, many: string) {
    return `${n} ${n === 1 ? one : many}`;
  }

  function usageText(c: Category): string {
    const parts: string[] = [];
    if (c.usage.entries) parts.push(plural(c.usage.entries, 'entry', 'entries'));
    if (c.usage.templates) {
      parts.push(plural(c.usage.templates, 'recurring template', 'recurring templates'));
    }
    if (c.usage.counterparties) {
      parts.push(`${plural(c.usage.counterparties, 'counterparty', 'counterparties')} (default)`);
    }
    return parts.join(', ');
  }

  /** Short usage for the compact row: "3 entries" or "Unused". */
  function usageShort(c: Category): string {
    if (usageTotal(c) === 0) return 'Unused';
    if (c.usage.entries) return plural(c.usage.entries, 'entry', 'entries');
    return 'In use';
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

  async function moveCategory(category: Category, step: 'up' | 'down') {
    move = { id: category.id, direction: category.direction, step };
    await tick();
    moveForm?.requestSubmit();
  }

  function openAdd(direction: Direction) {
    addDirection = direction;
    addRate = direction === 'income' && rates.length ? String(rates[0].rate_bp) : 'none';
    addOpen = true;
  }

  // Edit mode ends when the server accepts the change.
  $effect(() => {
    if (result?.action === 'update' && Object.keys(result.errors).length === 0 && !result.message) {
      editingId = null;
    }
  });

  const createFailed = $derived(
    result?.action === 'create' && (Object.keys(result.errors).length > 0 || !!result.message)
  );
  const highlightId = $derived(
    result?.action === 'create' && !createFailed ? (result.id ?? null) : null
  );

  const rateValue = (bp: number | null) => (bp === null ? 'none' : String(bp));
  const menuItemClass =
    'flex h-[40px] cursor-pointer items-center rounded-md px-1.5 text-sm text-ink outline-none data-disabled:cursor-not-allowed data-disabled:opacity-40 data-highlighted:bg-nav';
</script>

{#if result?.message && (result.action === 'move' || result.action === 'delete')}
  <div class="mb-2"><Notice tone="error">{result.message}</Notice></div>
{/if}

<form
  bind:this={moveForm}
  method="POST"
  action="?/moveCategory"
  use:enhance
  class="hidden"
  aria-hidden="true"
>
  <input type="hidden" name="id" value={move.id} />
  <input type="hidden" name="direction" value={move.direction} />
  <input type="hidden" name="step" value={move.step} />
</form>

<!-- Income and Expenses side by side on wide screens. -->
<div class="grid grid-cols-1 items-start gap-3 xl:grid-cols-2">
  {#each groups as group (group.direction)}
    <Card
      title={group.title}
      titleId="categories-{group.direction}"
      description={group.direction === 'income'
        ? 'The default VAT rate is suggested on new income.'
        : 'The default VAT rate is suggested on new expenses.'}
    >
      {#snippet actions()}
        <Button type="button" variant="secondary" onclick={() => openAdd(group.direction)}>
          + Add category
        </Button>
      {/snippet}

      <ul class="divide-y divide-border rounded-lg border border-border">
        {#each group.items as category, index (category.id)}
          {@const rowErrors =
            result?.action === 'update' && result.id === category.id ? result.errors : {}}
          <li class={['px-1.5', category.id === highlightId && 'row-highlight']}>
            {#if editingId === category.id}
              <form
                method="POST"
                action="?/updateCategory"
                use:enhance={() =>
                  async ({ update }) =>
                    update({ reset: false })}
                class="flex min-h-[48px] flex-wrap items-center gap-1 py-0.5"
              >
                <input type="hidden" name="id" value={category.id} />
                <label for="cat-name-{category.id}" class="sr-only">Name</label>
                <input
                  id="cat-name-{category.id}"
                  name="name"
                  required
                  maxlength="120"
                  value={category.name}
                  aria-invalid={rowErrors.name ? 'true' : undefined}
                  class={[controlClass, 'min-w-[160px] flex-1']}
                />
                <SelectField
                  id="cat-rate-{category.id}"
                  label="Default VAT"
                  hideLabel
                  name="default_vat_rate_bp"
                  items={rateItems}
                  value={rateValue(category.default_vat_rate_bp)}
                  class="w-[140px]"
                />
                <Button>Save</Button>
                <Button type="button" variant="ghost" onclick={() => (editingId = null)}>
                  Cancel
                </Button>
                {#if rowErrors.name || (result?.action === 'update' && result.id === category.id && result.message)}
                  <p class="w-full text-sm text-expense">{rowErrors.name ?? result?.message}</p>
                {/if}
              </form>
            {:else}
              <div class="flex h-[48px] items-center gap-1.5">
                <span class="min-w-0 flex-1 truncate font-medium">{category.name}</span>
                <span class="shrink-0 rounded-full bg-nav px-1 py-0.5 text-xs text-muted amount">
                  {formatRate(category.default_vat_rate_bp)}
                </span>
                <span class="hidden w-[96px] shrink-0 text-right text-xs text-muted sm:inline">
                  {usageShort(category)}
                </span>
                <DropdownMenu.Root>
                  <DropdownMenu.Trigger
                    aria-label="Actions for {category.name}"
                    class="inline-flex h-[44px] w-[44px] shrink-0 items-center justify-center rounded-md text-muted hover:bg-nav hover:text-ink focus-visible:outline-2 focus-visible:outline-accent"
                  >
                    <span aria-hidden="true" class="text-lg leading-none">⋯</span>
                  </DropdownMenu.Trigger>
                  <DropdownMenu.Portal>
                    <DropdownMenu.Content
                      align="end"
                      sideOffset={4}
                      class="z-50 min-w-[180px] rounded-lg border border-border bg-surface p-0.5 shadow-[0_8px_24px_rgba(29,30,32,0.08)]"
                    >
                      <DropdownMenu.Item
                        class={menuItemClass}
                        onSelect={() => (editingId = category.id)}
                      >
                        Edit
                      </DropdownMenu.Item>
                      <DropdownMenu.Item
                        class={menuItemClass}
                        disabled={index === 0}
                        onSelect={() => void moveCategory(category, 'up')}
                      >
                        Move up
                      </DropdownMenu.Item>
                      <DropdownMenu.Item
                        class={menuItemClass}
                        disabled={index === group.items.length - 1}
                        onSelect={() => void moveCategory(category, 'down')}
                      >
                        Move down
                      </DropdownMenu.Item>
                      <DropdownMenu.Separator class="my-0.5 h-px bg-border" />
                      <DropdownMenu.Item
                        class={[menuItemClass, 'text-expense data-highlighted:bg-expense/10']}
                        onSelect={() => askDelete(category)}
                      >
                        Delete
                      </DropdownMenu.Item>
                    </DropdownMenu.Content>
                  </DropdownMenu.Portal>
                </DropdownMenu.Root>
              </div>
            {/if}
          </li>
        {:else}
          <li class="px-1.5 py-1.5 text-sm text-muted">No categories yet.</li>
        {/each}
      </ul>
    </Card>
  {/each}
</div>

<!-- Add category -->
<Dialog.Root bind:open={addOpen}>
  <Dialog.Portal>
    <Dialog.Overlay class="fixed inset-0 z-40 bg-ink/30" />
    <Dialog.Content
      class="fixed top-1/2 left-1/2 z-50 w-[calc(100%-32px)] max-w-[440px] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-border bg-surface p-3 shadow-[0_16px_48px_rgba(29,30,32,0.12)]"
    >
      <Dialog.Title class="text-lg font-semibold">
        New {addDirection === 'income' ? 'income' : 'expense'} category
      </Dialog.Title>
      <form
        method="POST"
        action="?/createCategory"
        class="mt-2 flex flex-col gap-2"
        use:enhance={() =>
          async ({ result: actionResult, update }) => {
            await update({ reset: false });
            if (actionResult.type === 'success') addOpen = false;
          }}
      >
        <input type="hidden" name="direction" value={addDirection ?? 'expense'} />
        <TextField
          id="new-category-name"
          label="Name"
          name="name"
          required
          maxlength={120}
          value={createFailed ? (result?.values?.name ?? '') : ''}
          error={createFailed && result?.direction === addDirection
            ? (result?.errors.name ?? result?.message)
            : null}
        />
        <SelectField
          id="new-category-rate"
          label="Default VAT"
          name="default_vat_rate_bp"
          items={rateItems}
          bind:value={addRate}
        />
        <div class="mt-1 flex justify-end gap-1">
          <Dialog.Close class={buttonClass('ghost')}>Cancel</Dialog.Close>
          <Button>Add</Button>
        </div>
      </form>
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>

<!-- Delete (and move entries elsewhere when the category is in use) -->
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
        <Button variant="danger-solid" disabled={usageTotal(target) > 0 && !reassignTo}>
          {usageTotal(target) > 0 ? 'Move and delete' : 'Delete'}
        </Button>
      </form>
    {/snippet}
  </ConfirmDialog>
{/if}
