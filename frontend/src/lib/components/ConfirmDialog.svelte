<script lang="ts">
  import { AlertDialog } from 'bits-ui';
  import type { Snippet } from 'svelte';

  interface Props {
    open?: boolean;
    title: string;
    /** The explanation; the action button submits the `form` snippet's form. */
    description: Snippet;
    /** A <form> with the destructive action's submit button, rendered in the footer. */
    action: Snippet;
    /** Optional extra content between the description and the buttons. */
    children?: Snippet;
    cancelLabel?: string;
  }

  let {
    open = $bindable(false),
    title,
    description,
    action,
    children,
    cancelLabel = 'Cancel'
  }: Props = $props();
</script>

<AlertDialog.Root bind:open>
  <AlertDialog.Portal>
    <AlertDialog.Overlay class="fixed inset-0 z-40 bg-ink/30" />
    <AlertDialog.Content
      class="fixed top-1/2 left-1/2 z-50 w-[calc(100%-32px)] max-w-[460px] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-border bg-surface p-3 shadow-[0_16px_48px_rgba(29,30,32,0.12)] md:p-4"
    >
      <AlertDialog.Title class="text-lg font-semibold text-ink">{title}</AlertDialog.Title>
      <AlertDialog.Description class="mt-1 text-sm text-muted">
        {@render description()}
      </AlertDialog.Description>
      {#if children}
        <div class="mt-2">{@render children()}</div>
      {/if}
      <div class="mt-3 flex flex-wrap justify-end gap-1">
        <AlertDialog.Cancel
          class="inline-flex min-h-[44px] items-center rounded-md px-2.5 text-sm font-medium text-muted hover:bg-nav hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          {cancelLabel}
        </AlertDialog.Cancel>
        {@render action()}
      </div>
    </AlertDialog.Content>
  </AlertDialog.Portal>
</AlertDialog.Root>
