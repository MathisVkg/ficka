<script lang="ts">
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import { SETTINGS_SECTIONS } from '#lib/settings-sections.js';
  import type { LayoutProps } from './$types';

  let { children }: LayoutProps = $props();
</script>

<div class="flex flex-col gap-3">
  <h1 class="text-3xl font-semibold tracking-tight">Settings</h1>

  <div class="flex flex-col gap-3 lg:grid lg:grid-cols-[220px_minmax(0,1fr)] lg:items-start">
    <!-- Section menu: tabs on narrow screens, a side menu from 1024px. -->
    <nav aria-label="Settings sections" class="lg:sticky lg:top-4">
      <ul class="flex gap-0.5 overflow-x-auto border-b border-border lg:flex-col lg:border-b-0">
        {#each SETTINGS_SECTIONS as section (section.href)}
          {@const active = page.url.pathname === section.href}
          <li class="shrink-0">
            <a
              href={resolve(section.href)}
              aria-current={active ? 'page' : undefined}
              class={[
                'flex min-h-[44px] items-center px-1.5 text-sm transition-colors duration-150 ease-out focus-visible:outline-2 focus-visible:outline-accent',
                'border-b-2 lg:rounded-md lg:border-b-0',
                active
                  ? 'border-accent font-medium text-ink lg:bg-surface lg:shadow-[0_0_0_1px_var(--color-border)]'
                  : 'border-transparent text-muted hover:text-ink lg:hover:bg-surface/60'
              ]}
            >
              {section.label}
            </a>
          </li>
        {/each}
      </ul>
    </nav>

    <div class="min-w-0">
      {@render children()}
    </div>
  </div>
</div>
