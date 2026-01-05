<script lang="ts">
    import type { SearchResult, Dataset } from '$lib/types';
    import { MapPin, Calendar, ArrowRight } from 'lucide-svelte';
    import { truncate } from '$lib/utils';
    import { createEventDispatcher } from 'svelte';

    export let dataset: SearchResult;
    
    const dispatch = createEventDispatcher<{ open: Dataset }>();

    function formatScore(score: number): string {
        return `${(score * 100).toFixed(0)}%`;
    }

    function handleClick() {
        dispatch('open', dataset as unknown as Dataset);
    }
</script>

<button 
    type="button"
    class="card-elevated p-5 cursor-pointer group text-left w-full"
    on:click={handleClick}
    aria-label={`Open dataset ${dataset.title}`}
>
    <div class="flex items-start justify-between gap-4 mb-3">
        <!-- Title -->
        <h3 class="text-base font-semibold text-foreground leading-snug group-hover:text-primary transition-colors">
            {dataset.title}
        </h3>
        
        <!-- Score -->
        <div class="score-indicator shrink-0">
            {formatScore(dataset.score)} match
        </div>
    </div>

    <!-- Abstract -->
    <p class="text-sm text-muted-foreground leading-relaxed line-clamp-2 mb-4">
        {truncate(dataset.abstract, 200)}
    </p>

    <!-- Keywords -->
    {#if dataset.keywords && dataset.keywords.length > 0}
        <div class="flex flex-wrap gap-1.5 mb-4">
            {#each dataset.keywords.slice(0, 5) as keyword}
                <span class="badge">{keyword}</span>
            {/each}
            {#if dataset.keywords.length > 5}
                <span class="badge">+{dataset.keywords.length - 5}</span>
            {/if}
        </div>
    {/if}

    <!-- Metadata Row -->
    <div class="flex items-center justify-between pt-3 border-t border-border">
        <div class="flex items-center gap-4 text-xs text-muted-foreground">
            {#if dataset.has_geo_extent && dataset.center_lat && dataset.center_lon}
                <div class="flex items-center gap-1.5">
                    <MapPin class="w-3.5 h-3.5" />
                    <span>{dataset.center_lat.toFixed(1)}°N, {dataset.center_lon.toFixed(1)}°W</span>
                </div>
            {/if}
            
            {#if dataset.has_temporal_extent}
                <div class="flex items-center gap-1.5">
                    <Calendar class="w-3.5 h-3.5" />
                    <span>Temporal data</span>
                </div>
            {/if}
        </div>
        
        <div class="flex items-center gap-1 text-xs font-medium text-primary">
            View details
            <ArrowRight class="w-3.5 h-3.5" />
        </div>
    </div>
</button>
