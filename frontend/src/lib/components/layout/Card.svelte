<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    /** Optional title row: title on the left, actions on the right. */
    title?: string;
    titleId?: string;
    /** Sub-heading under the title. */
    description?: string;
    actions?: Snippet;
    children: Snippet;
    /** The element's accessible name when there's no visible title. */
    label?: string;
    id?: string;
    class?: string;
  }

  let { title, titleId, description, actions, children, label, id, class: extra }: Props = $props();

  const headingId = $derived(
    titleId ?? (title ? `card-${title.toLowerCase().replace(/\W+/g, '-')}` : undefined)
  );
</script>

<!-- White surface, 1px border, 16px radius, 24px padding (16px on mobile). -->
<section
  {id}
  aria-labelledby={title ? headingId : undefined}
  aria-label={title ? undefined : label}
  class={['min-w-0 rounded-xl border border-border bg-surface p-2 md:p-3', extra]}
>
  {#if title || actions}
    <div class="mb-2 flex min-h-[44px] flex-wrap items-center justify-between gap-x-2 gap-y-1">
      <div class="min-w-0">
        {#if title}<h2 id={headingId} class="truncate text-lg font-semibold">{title}</h2>{/if}
        {#if description}<p class="max-w-[70ch] text-sm text-muted">{description}</p>{/if}
      </div>
      {#if actions}<div class="flex flex-wrap items-center gap-1">{@render actions()}</div>{/if}
    </div>
  {/if}
  {@render children()}
</section>
