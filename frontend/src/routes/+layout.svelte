<script lang="ts">
  import './layout.css';
  import favicon from '#lib/assets/favicon.svg';
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import { isActive, navItems } from '#lib/navigation.js';
  import type { LayoutProps } from './$types';

  let { children, data }: LayoutProps = $props();
</script>

<svelte:head>
  <link rel="icon" href={favicon} />
</svelte:head>

<div class="flex min-h-screen flex-col md:flex-row">
  <nav
    aria-label="Main"
    class="flex w-full shrink-0 flex-col border-b border-border bg-nav p-2 md:sticky md:top-0 md:h-screen md:w-[240px] md:border-r md:border-b-0"
  >
    <a href={resolve('/')} class="px-1.5 py-1 text-xl font-semibold tracking-tight text-ink">
      Ficka
    </a>

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

    <p class="mt-2 flex items-center gap-1 px-1.5 pt-1 text-xs text-muted md:mt-auto">
      <span
        aria-hidden="true"
        class={['size-1 rounded-full', data.api.connected ? 'bg-income' : 'bg-expense']}
      ></span>
      {data.api.connected ? 'API connected' : 'API unavailable'}
    </p>
  </nav>

  <main class="min-w-0 flex-1 p-3 md:p-5">
    {@render children()}
  </main>
</div>
