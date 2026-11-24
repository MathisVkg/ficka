<script lang="ts">
  import { Combobox } from 'bits-ui';
  import type { CounterpartyChoice, CounterpartyRole } from '#lib/types.js';

  interface Props {
    value?: CounterpartyChoice | null;
    id: string;
    label?: string;
    error?: string | null;
    /** Role given to counterparties created from here. */
    createRole?: CounterpartyRole;
    onselect?: (choice: CounterpartyChoice | null) => void;
  }

  let {
    value = $bindable(null),
    id,
    label = 'Counterparty',
    error = null,
    createRole = 'supplier',
    onselect
  }: Props = $props();

  const CREATE = '__create__';
  let results = $state<CounterpartyChoice[]>([]);
  let term = $state('');
  let open = $state(false);
  let busy = $state(false);
  let createError = $state<string | null>(null);
  let timer: ReturnType<typeof setTimeout> | undefined;
  let requestId = 0;

  const exactMatch = $derived(
    results.some((r) => r.name.toLowerCase() === term.trim().toLowerCase())
  );
  const items = $derived([
    ...results.map((r) => ({ value: String(r.id), label: r.name })),
    ...(term.trim() && !exactMatch ? [{ value: CREATE, label: `Create “${term.trim()}”` }] : [])
  ]);

  async function search(q: string) {
    const current = ++requestId;
    try {
      const response = await fetch(`/counterparties/search?q=${encodeURIComponent(q)}`);
      if (!response.ok || current !== requestId) return;
      results = (await response.json()) as CounterpartyChoice[];
    } catch {
      // Keep the previous suggestions; the form still works without them.
    }
  }

  function onInput(event: Event) {
    term = (event.currentTarget as HTMLInputElement).value;
    createError = null;
    clearTimeout(timer);
    timer = setTimeout(() => void search(term), 200);
  }

  function choose(choice: CounterpartyChoice | null) {
    value = choice;
    onselect?.(choice);
  }

  async function create(name: string) {
    busy = true;
    createError = null;
    try {
      const response = await fetch('/counterparties/quick', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, role: createRole })
      });
      const body = (await response.json().catch(() => ({}))) as CounterpartyChoice & {
        message?: string;
      };
      if (!response.ok) {
        createError = body.message ?? 'The counterparty couldn’t be created.';
        return;
      }
      results = [body, ...results];
      choose(body);
    } finally {
      busy = false;
    }
  }

  function onValueChange(next: string) {
    if (next === CREATE) {
      void create(term.trim());
      return;
    }
    choose(results.find((r) => String(r.id) === next) ?? null);
  }

  function onOpenChange(next: boolean) {
    open = next;
    if (next && results.length === 0) void search(term);
  }
</script>

<div class="flex flex-col gap-0.5">
  <label for={id} class="text-sm font-medium text-ink">{label}</label>
  <Combobox.Root
    type="single"
    value={value ? String(value.id) : ''}
    {onValueChange}
    {open}
    {onOpenChange}
    {items}
    inputValue={value?.name ?? term}
  >
    <div class="relative">
      <Combobox.Input
        {id}
        oninput={onInput}
        placeholder="Search, or type a new name"
        aria-invalid={error || createError ? 'true' : undefined}
        aria-describedby={error || createError ? `${id}-error` : undefined}
        class="min-h-[44px] w-full rounded-md border border-border bg-surface pr-9 pl-1.5 text-base text-ink placeholder:text-muted focus:border-accent focus:outline-2 focus:outline-offset-1 focus:outline-accent aria-invalid:border-expense"
      />
      {#if value}
        <button
          type="button"
          class="absolute top-1/2 right-5 flex size-4 -translate-y-1/2 items-center justify-center rounded-md text-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-accent"
          aria-label="Clear counterparty"
          onclick={() => {
            term = '';
            choose(null);
          }}
        >
          ×
        </button>
      {/if}
      <Combobox.Trigger
        aria-label="Show counterparties"
        class="absolute top-1/2 right-0.5 flex size-[40px] -translate-y-1/2 items-center justify-center rounded-md text-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-accent"
      >
        <svg aria-hidden="true" viewBox="0 0 16 16" class="size-2">
          <path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.5" />
        </svg>
      </Combobox.Trigger>
    </div>
    <Combobox.Portal>
      <Combobox.Content
        sideOffset={4}
        class="z-50 max-h-[320px] min-w-(--bits-combobox-anchor-width) overflow-y-auto rounded-lg border border-border bg-surface p-0.5 shadow-[0_8px_24px_rgba(29,30,32,0.08)]"
      >
        {#each items as item (item.value)}
          <Combobox.Item
            value={item.value}
            label={item.label}
            class={[
              'flex min-h-[40px] cursor-pointer items-center rounded-md px-1.5 text-sm outline-none data-highlighted:bg-nav',
              item.value === CREATE ? 'font-medium text-accent' : 'text-ink'
            ]}
          >
            {item.label}
          </Combobox.Item>
        {:else}
          <p class="px-1.5 py-1 text-sm text-muted">Type a name to search or create.</p>
        {/each}
      </Combobox.Content>
    </Combobox.Portal>
  </Combobox.Root>
  {#if busy}<p class="text-xs text-muted">Creating…</p>{/if}
  {#if error || createError}
    <p id="{id}-error" class="text-sm text-expense">{createError ?? error}</p>
  {/if}
</div>
