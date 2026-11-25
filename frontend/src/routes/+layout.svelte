<script lang="ts">
  import './layout.css';
  import favicon from '#lib/assets/favicon.svg';
  import { resolve } from '$app/paths';
  import { afterNavigate } from '$app/navigation';
  import { page } from '$app/state';
  import Button from '#lib/components/Button.svelte';
  import { isActive, navItems } from '#lib/navigation.js';
  import type { LayoutProps } from './$types';

  let { children, data }: LayoutProps = $props();

  // Below 768px the menu folds away behind a "Menu" button, so pages start at the top.
  let menuOpen = $state(false);
  afterNavigate(() => {
    menuOpen = false;
  });
  const current = $derived(navItems.find((item) => isActive(page.url.pathname, item.href)));
</script>

<svelte:head>
  <link rel="icon" href={favicon} />
</svelte:head>

{#if data.user}
  <div class="flex min-h-screen flex-col md:flex-row">
    <nav
      aria-label="Main"
      class="flex w-full shrink-0 flex-col border-b border-border bg-nav p-2 md:sticky md:top-0 md:h-screen md:w-[240px] md:border-r md:border-b-0"
    >
      <div class="flex items-center justify-between gap-2">
        <a href={resolve('/')} class="px-1.5 py-1 text-xl font-semibold tracking-tight text-ink">
          Ficka
        </a>
        <button
          type="button"
          class="inline-flex h-[44px] items-center gap-1 rounded-md px-1.5 text-sm font-medium text-ink hover:bg-surface/60 focus-visible:outline-2 focus-visible:outline-accent md:hidden"
          aria-expanded={menuOpen}
          aria-controls="main-menu"
          onclick={() => (menuOpen = !menuOpen)}
          onkeydown={(event) => event.key === 'Escape' && (menuOpen = false)}
        >
          {#if !menuOpen && current}<span class="text-muted">{current.label}</span>{/if}
          <svg
            aria-hidden="true"
            viewBox="0 0 16 16"
            class="size-2"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
          >
            {#if menuOpen}<path d="M4 4l8 8M12 4l-8 8" />{:else}<path
                d="M2.5 4.5h11M2.5 8h11M2.5 11.5h11"
              />{/if}
          </svg>
          {menuOpen ? 'Close' : 'Menu'}
        </button>
      </div>

      <div id="main-menu" class={['flex-1 flex-col', menuOpen ? 'flex' : 'hidden', 'md:flex']}>
        <ul class="mt-2 flex flex-col gap-0.5">
          {#each navItems as item (item.href)}
            {@const active = isActive(page.url.pathname, item.href)}
            <li>
              <a
                href={resolve(item.href)}
                aria-current={active ? 'page' : undefined}
                class={[
                  'block rounded-md px-1.5 py-1 text-sm transition-colors duration-150 ease-out',
                  active
                    ? 'bg-surface font-medium text-ink shadow-[0_0_0_1px_var(--color-border)]'
                    : 'text-muted hover:bg-surface/60 hover:text-ink'
                ]}
              >
                {item.label}
              </a>
            </li>
          {/each}
        </ul>

        <div class="mt-2 flex flex-col gap-1 border-t border-border pt-2 md:mt-auto">
          <div class="px-1.5">
            <p class="truncate text-sm font-medium text-ink">{data.user.display_name}</p>
            {#if data.company}
              <p class="truncate text-xs text-muted">{data.company.name}</p>
            {/if}
          </div>
          <form method="POST" action="/logout">
            <Button variant="ghost" class="w-full justify-start px-1.5">Log out</Button>
          </form>
          <p class="flex items-center gap-1 px-1.5 text-xs text-muted">
            <span
              aria-hidden="true"
              class={['size-1 rounded-full', data.api.connected ? 'bg-income' : 'bg-expense']}
            ></span>
            {data.api.connected ? 'API connected' : 'API unavailable'}
          </p>
        </div>
      </div>
    </nav>

    <!-- Each page wraps itself in <Page> (full width, 32px / 16px padding). -->
    <main class="flex min-w-0 flex-1">
      {@render children()}
    </main>
  </div>
{:else}
  <!-- Not logged in: only /login renders (hooks.server.ts redirects everything else). -->
  {@render children()}
{/if}
