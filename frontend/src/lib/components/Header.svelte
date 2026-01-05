<script lang="ts">
    import { page } from '$app/stores';
    import { Database, Search, MessageSquare, BarChart3 } from 'lucide-svelte';

    const navigation = [
        { href: '/', label: 'Search', icon: Search },
        { href: '/chat', label: 'AI Assistant', icon: MessageSquare },
    ];

    $: currentPath = $page.url.pathname;
</script>

<header class="sticky top-0 z-50 w-full bg-white border-b border-border">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-14">
            <!-- Logo and Title -->
            <a href="/" class="flex items-center gap-3 hover:opacity-80 transition-opacity">
                <div class="flex items-center justify-center w-8 h-8 bg-primary rounded">
                    <Database class="w-4 h-4 text-primary-foreground" />
                </div>
                <div class="hidden sm:block">
                    <div class="text-sm font-semibold text-foreground leading-tight">
                        Dataset Search
                    </div>
                    <div class="text-xs text-muted-foreground leading-tight">
                        Environmental Data Discovery
                    </div>
                </div>
            </a>

            <!-- Navigation -->
            <nav class="flex items-center gap-1">
                {#each navigation as item}
                    <a
                        href={item.href}
                        class={`
                            flex items-center gap-2 px-3 py-2 text-sm font-medium rounded transition-colors
                            ${currentPath === item.href 
                                ? 'bg-muted text-foreground' 
                                : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'}
                        `}
                    >
                        <svelte:component this={item.icon} class="w-4 h-4" />
                        <span class="hidden sm:inline">{item.label}</span>
                    </a>
                {/each}
            </nav>

            <!-- Stats Badge -->
            <div class="hidden md:flex items-center gap-2 text-xs text-muted-foreground">
                <BarChart3 class="w-3.5 h-3.5" />
                <span>200 Datasets</span>
            </div>
        </div>
    </div>
</header>
