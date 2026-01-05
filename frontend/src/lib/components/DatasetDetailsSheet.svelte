<script lang="ts">
    import { fly, fade } from 'svelte/transition';
    import { cubicOut } from 'svelte/easing';
    import type { Dataset } from '$lib/types';
    import { X, Copy, FileText, Code, Download, ExternalLink, Calendar, MapPin, Loader2 } from 'lucide-svelte';
    import { formatDate } from '$lib/utils';
    import { createEventDispatcher } from 'svelte';

    export let dataset: Dataset | null = null;
    export let isOpen = false;
    export let isLoading = false;

    const dispatch = createEventDispatcher<{ close: void }>();

    const tabs = ['overview', 'metadata', 'files'] as const;
    let activeTab: typeof tabs[number] = 'overview';

    function close() {
        dispatch('close');
        activeTab = 'overview';
    }

    function copyDOI() {
        if (!dataset) return;
        const cehId = getOriginalCehId();
        navigator.clipboard.writeText(`10.5285/${cehId}`);
    }

    // Extract original CEH UUID from metadata_url
    // metadata_url format: /var/.../metadata_be0bdc0e-bc2e-4f1d-b524-2c02798dd893.xml
    function getOriginalCehId(): string {
        if (!dataset?.metadata_url) return dataset?.id || '';
        const match = dataset.metadata_url.match(/metadata_([a-f0-9-]{36})/);
        return match ? match[1] : dataset.id;
    }

    $: cehId = dataset ? getOriginalCehId() : '';
</script>

{#if isOpen}
    <!-- Backdrop -->
    <button
        type="button"
        transition:fade={{ duration: 150 }}
        class="fixed inset-0 bg-foreground/10 backdrop-blur-sm z-50"
        on:click={close}
        aria-label="Close dataset details"
    ></button>

    <!-- Panel -->
    <div
        transition:fly={{ y: 50, duration: 250, easing: cubicOut }}
        class="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[90%] max-w-3xl max-h-[85vh] bg-white shadow-2xl z-50 border border-border rounded-lg flex flex-col"
    >
        {#if !dataset && isLoading}
            <!-- Loading State -->
            <div class="h-full flex flex-col items-center justify-center">
                <Loader2 class="w-6 h-6 text-primary animate-spin mb-3" />
                <p class="text-sm text-muted-foreground">Loading dataset details...</p>
            </div>
        {:else if dataset}
            <!-- Header -->
            <header class="px-6 py-5 border-b border-border flex items-start justify-between shrink-0">
                <div class="pr-8">
                    <div class="flex items-center gap-2 mb-2">
                        <span class="px-2 py-0.5 text-xs font-medium bg-muted text-muted-foreground rounded">
                            Dataset
                        </span>
                        <span class="text-xs text-muted-foreground font-mono">
                            ID: {dataset.id.slice(0, 8)}...
                        </span>
                    </div>
                    <h2 class="text-lg font-semibold text-foreground leading-snug">
                        {dataset.title}
                    </h2>
                </div>
                <button 
                    on:click={close}
                    class="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors"
                >
                    <X class="w-5 h-5" />
                </button>
            </header>

            <!-- Tabs -->
            <div class="px-6 border-b border-border shrink-0 bg-muted/30">
                <div class="flex gap-6">
                    {#each tabs as tab}
                        <button 
                            class={`
                                py-3 text-sm font-medium border-b-2 transition-colors capitalize
                                ${activeTab === tab 
                                    ? 'border-primary text-primary' 
                                    : 'border-transparent text-muted-foreground hover:text-foreground'}
                            `}
                            on:click={() => activeTab = tab}
                        >
                            {tab}
                        </button>
                    {/each}
                </div>
            </div>

            <!-- Content -->
            <div class="flex-1 overflow-y-auto p-6">
                
                <!-- Tab: Overview -->
                {#if activeTab === 'overview'}
                    <div class="space-y-6 animate-in">
                        <!-- Actions -->
                        <div class="flex gap-2">
                            <button 
                                on:click={copyDOI} 
                                class="btn-secondary text-xs"
                            >
                                <Copy class="w-3.5 h-3.5 mr-1.5" />
                                Copy DOI
                            </button>
                            {#if dataset.metadata_url}
                                <a 
                                    href={dataset.metadata_url} 
                                    target="_blank" 
                                    class="btn-secondary text-xs"
                                >
                                    <ExternalLink class="w-3.5 h-3.5 mr-1.5" />
                                    Original Source
                                </a>
                            {/if}
                        </div>

                        <!-- Abstract -->
                        <div>
                            <h3 class="section-header mb-3 flex items-center gap-2">
                                <FileText class="w-4 h-4" />
                                Abstract
                            </h3>
                            <p class="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
                                {dataset.abstract}
                            </p>
                        </div>

                        <!-- Metadata Cards -->
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            {#if dataset.metadata?.temporal_extent_start}
                                <div class="p-4 bg-muted/30 border border-border rounded">
                                    <span class="section-header block mb-1">Temporal Coverage</span>
                                    <div class="flex items-center gap-2 text-sm text-foreground font-mono">
                                        <Calendar class="w-4 h-4 text-muted-foreground" />
                                        <span>{formatDate(dataset.metadata.temporal_extent_start).split(',')[0]}</span>
                                        <span class="text-muted-foreground">to</span>
                                        <span>
                                            {dataset.metadata.temporal_extent_end
                                                ? formatDate(dataset.metadata.temporal_extent_end).split(',')[0]
                                                : 'Present'}
                                        </span>
                                    </div>
                                </div>
                            {/if}
                            
                            {#if dataset.metadata?.bounding_box}
                                <div class="p-4 bg-muted/30 border border-border rounded">
                                    <span class="section-header block mb-1">Spatial Coverage</span>
                                    <div class="flex items-center gap-2 text-sm text-foreground">
                                        <MapPin class="w-4 h-4 text-muted-foreground" />
                                        <span>Geographic extent defined</span>
                                    </div>
                                    <div class="text-xs text-muted-foreground mt-1 font-mono">
                                        N: {dataset.metadata.bounding_box.north_latitude.toFixed(2)} | 
                                        E: {dataset.metadata.bounding_box.east_longitude.toFixed(2)}
                                    </div>
                                </div>
                            {/if}
                        </div>
                    </div>
                {/if}

                <!-- Tab: Metadata -->
                {#if activeTab === 'metadata'}
                    <div class="animate-in">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th class="w-1/3">Field (ISO 19115)</th>
                                    <th>Value</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td class="font-mono text-xs text-muted-foreground">gmd:title</td>
                                    <td>{dataset.title}</td>
                                </tr>
                                <tr>
                                    <td class="font-mono text-xs text-muted-foreground">gmd:topicCategory</td>
                                    <td>{dataset.metadata?.topic_category || 'geoscientificInformation'}</td>
                                </tr>
                                <tr>
                                    <td class="font-mono text-xs text-muted-foreground">gmd:language</td>
                                    <td class="font-mono">{dataset.metadata?.dataset_language || 'eng'}</td>
                                </tr>
                                <tr>
                                    <td class="font-mono text-xs text-muted-foreground">gmd:contact</td>
                                    <td>
                                        <div class="font-medium">{dataset.metadata?.contact_organization || 'Not specified'}</div>
                                        {#if dataset.metadata?.contact_email}
                                            <div class="text-xs text-muted-foreground mt-0.5">{dataset.metadata.contact_email}</div>
                                        {/if}
                                    </td>
                                </tr>
                                <tr>
                                    <td class="font-mono text-xs text-muted-foreground">gmd:dateStamp</td>
                                    <td class="font-mono">
                                        {dataset.metadata?.metadata_date
                                            ? formatDate(dataset.metadata.metadata_date)
                                            : 'Unknown'}
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                {/if}

                <!-- Tab: Files -->
                {#if activeTab === 'files'}
                    <div class="space-y-4 animate-in">
                        <h3 class="section-header flex items-center gap-2">
                            <Download class="w-4 h-4" />
                            Available Downloads
                        </h3>
                        
                        <div class="space-y-3">
                            <!-- Dataset Landing Page -->
                            <a 
                                href={`https://catalogue.ceh.ac.uk/documents/${cehId}`} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                class="flex items-center justify-between p-4 bg-white border border-border rounded hover:border-primary/30 transition-colors group"
                            >
                                <div class="flex items-center gap-3">
                                    <div class="p-2 bg-muted rounded">
                                        <ExternalLink class="w-5 h-5 text-muted-foreground" />
                                    </div>
                                    <div>
                                        <p class="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                                            View on CEH Catalogue
                                        </p>
                                        <p class="text-xs text-muted-foreground">
                                            Full dataset record and download options
                                        </p>
                                    </div>
                                </div>
                                <span class="text-xs font-mono text-muted-foreground bg-muted px-2 py-1 rounded">catalogue.ceh.ac.uk</span>
                            </a>

                            <!-- Metadata XML -->
                            <a 
                                href={`https://catalogue.ceh.ac.uk/documents/${cehId}.xml`} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                class="flex items-center justify-between p-4 bg-white border border-border rounded hover:border-primary/30 transition-colors group"
                            >
                                <div class="flex items-center gap-3">
                                    <div class="p-2 bg-muted rounded">
                                        <Code class="w-5 h-5 text-muted-foreground" />
                                    </div>
                                    <div>
                                        <p class="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                                            ISO 19139 Metadata
                                        </p>
                                        <p class="text-xs text-muted-foreground">
                                            Download as XML record
                                        </p>
                                    </div>
                                </div>
                                <span class="text-xs font-mono text-muted-foreground bg-muted px-2 py-1 rounded">.XML</span>
                            </a>

                            <!-- Dataset Files (ZIP/Download) -->
                            <a 
                                href={`https://catalogue.ceh.ac.uk/datastore/eidchub/${cehId}`} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                class="flex items-center justify-between p-4 bg-white border border-border rounded hover:border-primary/30 transition-colors group"
                            >
                                <div class="flex items-center gap-3">
                                    <div class="p-2 bg-primary/10 rounded">
                                        <Download class="w-5 h-5 text-primary" />
                                    </div>
                                    <div>
                                        <p class="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                                            Download Data Files
                                        </p>
                                        <p class="text-xs text-muted-foreground">
                                            Access raw data files
                                        </p>
                                    </div>
                                </div>
                                <span class="text-xs font-mono text-muted-foreground bg-muted px-2 py-1 rounded">DATA</span>
                            </a>
                        </div>

                        <p class="text-xs text-muted-foreground mt-4">
                            Data access may require registration with the EIDC portal.
                        </p>
                    </div>
                {/if}
            </div>
        {/if}
    </div>
{/if}
