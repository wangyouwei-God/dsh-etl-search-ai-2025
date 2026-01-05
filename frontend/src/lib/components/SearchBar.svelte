<script lang="ts">
    import { Search, Loader2, X } from 'lucide-svelte';
    import { createEventDispatcher } from 'svelte';

    export let value = '';
    export let placeholder = 'Search datasets by keyword or natural language...';
    export let isLoading = false;
    export let variant: 'hero' | 'compact' = 'hero';

    const dispatch = createEventDispatcher<{ search: string }>();

    function handleSubmit(e: Event) {
        e.preventDefault();
        if (value.trim()) {
            dispatch('search', value.trim());
        }
    }

    function clear() {
        value = '';
    }
</script>

<form 
    on:submit={handleSubmit} 
    class="w-full {variant === 'hero' ? 'max-w-xl mx-auto' : ''}"
>
    <div class={`
        relative flex items-center bg-white border transition-all
        ${variant === 'hero' 
            ? 'border-border rounded shadow-sm focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/10' 
            : 'border-border rounded focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/10'}
    `}>
        <!-- Search Icon -->
        <div class={`
            flex items-center justify-center text-muted-foreground
            ${variant === 'hero' ? 'pl-4 w-12' : 'pl-3 w-10'}
        `}>
            <Search class={`${variant === 'hero' ? 'w-5 h-5' : 'w-4 h-4'}`} />
        </div>
        
        <!-- Input -->
        <input
            type="text"
            bind:value
            {placeholder}
            disabled={isLoading}
            class={`
                w-full bg-transparent border-none focus:ring-0 focus:outline-none 
                text-foreground placeholder:text-muted-foreground
                disabled:opacity-50 disabled:cursor-not-allowed
                ${variant === 'hero' ? 'py-3 text-base' : 'py-2 text-sm'}
            `}
        />
        
        <!-- Actions -->
        <div class="pr-2 flex items-center gap-1">
            {#if value && !isLoading}
                <button 
                    type="button"
                    on:click={clear}
                    class="p-1.5 text-muted-foreground hover:text-foreground rounded transition-colors"
                    aria-label="Clear search"
                >
                    <X class="w-4 h-4" />
                </button>
            {/if}

            {#if isLoading}
                <div class="p-2">
                    <Loader2 class={`${variant === 'hero' ? 'w-5 h-5' : 'w-4 h-4'} text-primary animate-spin`} />
                </div>
            {:else}
                <button 
                    type="submit"
                    class={`
                        px-3 py-1.5 text-sm font-medium bg-primary text-primary-foreground rounded
                        hover:opacity-90 transition-opacity disabled:opacity-50
                        ${variant === 'hero' ? '' : 'text-xs'}
                    `}
                    disabled={!value.trim()}
                >
                    Search
                </button>
            {/if}
        </div>
    </div>
</form>
