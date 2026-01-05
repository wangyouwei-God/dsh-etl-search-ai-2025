<script lang="ts">
    import SearchBar from '$lib/components/SearchBar.svelte';
    import DatasetCard from '$lib/components/DatasetCard.svelte';
    import DatasetDetailsSheet from '$lib/components/DatasetDetailsSheet.svelte';
    import { searchDatasets, getDataset, APIError } from '$lib/api';
    import type { SearchResponse, Dataset } from '$lib/types';
    import { Database, Filter, ArrowRight, Clock, Globe, FileText, ChevronRight } from 'lucide-svelte';

    let query = '';
    let results: SearchResponse | null = null;
    let isLoading = false;
    let error: string | null = null;
    let hasSearched = false;

    // Sheet State
    let selectedDataset: Dataset | null = null;
    let isSheetOpen = false;
    let isSheetLoading = false;

    // Quick search suggestions
    const suggestions = [
        'Land cover mapping',
        'Hydrological data UK',
        'Biodiversity monitoring',
        'Climate change impacts'
    ];

    // Categories
    const categories = [
        { id: 'land', label: 'Land Cover', query: 'land cover' },
        { id: 'water', label: 'Hydrology', query: 'water hydrology' },
        { id: 'bio', label: 'Biodiversity', query: 'biodiversity species' },
        { id: 'climate', label: 'Climate', query: 'climate temperature' }
    ];

    async function handleSearch(event: CustomEvent<string>) {
        query = event.detail;
        if (!query.trim()) return;
        
        isLoading = true;
        error = null;
        hasSearched = true;
        results = null;

        try {
            results = await searchDatasets(query, 20);
        } catch (e) {
            if (e instanceof APIError) {
                error = e.message;
            } else {
                error = 'An unexpected error occurred. Please try again.';
            }
        } finally {
            isLoading = false;
        }
    }

    async function handleOpenDataset(event: CustomEvent<Dataset>) {
        const partialDataset = event.detail;
        
        selectedDataset = partialDataset;
        isSheetOpen = true;
        isSheetLoading = true;

        try {
            const fullDataset = await getDataset(partialDataset.id);
            selectedDataset = fullDataset;
        } catch (e) {
            console.error("Failed to fetch details:", e);
        } finally {
            isSheetLoading = false;
        }
    }

    function closeSheet() {
        isSheetOpen = false;
        setTimeout(() => {
            selectedDataset = null;
        }, 300);
    }
    
    function resetSearch() {
        hasSearched = false;
        results = null;
        query = '';
    }

    function quickSearch(term: string) {
        query = term;
        handleSearch(new CustomEvent('search', { detail: term }));
    }
</script>

<svelte:head>
    <title>{query ? `${query} - ` : ''}Dataset Search and Discovery</title>
</svelte:head>

<!-- Hero State: Initial Landing -->
{#if !hasSearched}
    <div class="min-h-[calc(100vh-3.5rem)] flex flex-col">
        <!-- Hero Section -->
        <section class="flex-1 flex items-center justify-center px-6 py-12">
            <div class="max-w-2xl w-full text-center space-y-8">
                <!-- Title -->
                <div class="space-y-3">
                    <h1 class="text-3xl sm:text-4xl font-bold text-foreground tracking-tight">
                        Dataset Search and Discovery
                    </h1>
                    <p class="text-lg text-muted-foreground max-w-lg mx-auto">
                        Search across 200+ environmental datasets using semantic search and natural language queries.
                    </p>
                </div>

                <!-- Search Bar -->
                <div class="pt-2">
                    <SearchBar {isLoading} on:search={handleSearch} variant="hero" />
                </div>

                <!-- Quick Suggestions -->
                <div class="pt-4">
                    <p class="text-xs text-muted-foreground mb-3">Try searching for:</p>
                    <div class="flex flex-wrap justify-center gap-2">
                        {#each suggestions as suggestion}
                            <button 
                                class="px-3 py-1 text-xs text-muted-foreground bg-muted/50 border border-border rounded-full hover:border-primary/40 hover:text-primary hover:bg-primary/5 transition-all"
                                on:click={() => quickSearch(suggestion)}
                            >
                                {suggestion}
                            </button>
                        {/each}
                    </div>
                </div>
            </div>
        </section>

        <!-- Footer Stats -->
        <footer class="border-t border-border py-4">
            <div class="max-w-5xl mx-auto px-6">
                <div class="flex flex-wrap justify-center gap-6 text-xs text-muted-foreground">
                    <div class="flex items-center gap-2">
                        <Database class="w-3.5 h-3.5" />
                        <span>200 Datasets indexed</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <Globe class="w-3.5 h-3.5" />
                        <span>ISO 19115 Metadata</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <FileText class="w-3.5 h-3.5" />
                        <span>Semantic Vector Search</span>
                    </div>
                </div>
            </div>
        </footer>
    </div>
{/if}

<!-- Results State: Active Search -->
{#if hasSearched}
    <div class="flex max-w-7xl mx-auto">
        <!-- Sidebar Filters -->
        <aside class="hidden lg:block w-64 shrink-0 border-r border-border bg-white min-h-[calc(100vh-3.5rem)] p-6">
            <div class="flex items-center gap-2 text-sm font-medium text-foreground mb-6">
                <Filter class="w-4 h-4" />
                Filters
            </div>
            
            <!-- Category Filter -->
            <div class="space-y-4">
                <div>
                    <div class="section-header mb-3">Category</div>
                    <div class="space-y-1">
                        {#each categories as category}
                            <button 
                                class="w-full text-left px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors"
                                on:click={() => quickSearch(category.query)}
                            >
                                {category.label}
                            </button>
                        {/each}
                    </div>
                </div>
            </div>
            
            <!-- Reset Button -->
            <div class="mt-8 pt-6 border-t border-border">
                <button 
                    class="w-full btn-secondary text-xs"
                    on:click={resetSearch}
                >
                    Clear Search
                </button>
            </div>
        </aside>

        <!-- Results Area -->
        <main class="flex-1 min-w-0 p-6 lg:p-8">
            <!-- Search Bar (Inline) -->
            <div class="mb-6">
                <SearchBar 
                    value={query} 
                    {isLoading} 
                    on:search={handleSearch} 
                    variant="compact" 
                />
            </div>

            {#if error}
                <div class="p-4 bg-destructive/5 border border-destructive/20 rounded text-sm text-destructive">
                    {error}
                </div>
            {:else if results}
                <!-- Results Header -->
                <div class="flex justify-between items-baseline mb-6">
                    <div>
                        <h2 class="text-lg font-semibold text-foreground">
                            {results.total_results} {results.total_results === 1 ? 'result' : 'results'}
                        </h2>
                        <p class="text-sm text-muted-foreground">
                            for "{query}"
                        </p>
                    </div>
                    <span class="text-xs text-muted-foreground font-mono">
                        {results.processing_time_ms.toFixed(0)}ms
                    </span>
                </div>

                {#if results.total_results === 0}
                    <div class="text-center py-16 bg-white rounded border border-dashed border-border">
                        <p class="text-muted-foreground mb-2">No datasets found matching your query.</p>
                        <p class="text-sm text-muted-foreground">Try adjusting your search terms.</p>
                    </div>
                {:else}
                    <div class="space-y-4">
                        {#each results.results as dataset (dataset.id)}
                            <DatasetCard 
                                {dataset} 
                                on:open={handleOpenDataset} 
                            />
                        {/each}
                    </div>
                {/if}
            {:else if isLoading}
                <!-- Loading Skeleton -->
                <div class="space-y-4">
                    {#each Array(4) as _}
                        <div class="card p-6 animate-pulse">
                            <div class="h-5 bg-muted rounded w-3/4 mb-3"></div>
                            <div class="h-4 bg-muted rounded w-full mb-2"></div>
                            <div class="h-4 bg-muted rounded w-2/3"></div>
                        </div>
                    {/each}
                </div>
            {/if}
        </main>
    </div>
{/if}

<!-- Details Sheet -->
<DatasetDetailsSheet 
    dataset={selectedDataset} 
    isOpen={isSheetOpen} 
    isLoading={isSheetLoading}
    on:close={closeSheet} 
/>
