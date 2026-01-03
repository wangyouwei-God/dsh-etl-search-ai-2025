<script lang="ts">
	import SearchBar from '$lib/components/SearchBar.svelte';
	import DatasetCard from '$lib/components/DatasetCard.svelte';
	import { searchDatasets, APIError } from '$lib/api';
	import type { SearchResponse } from '$lib/types';
	import { AlertCircle, Sparkles, MessageCircle } from 'lucide-svelte';

	let query = '';
	let results: SearchResponse | null = null;
	let isLoading = false;
	let error: string | null = null;

	async function handleSearch(event: CustomEvent<string>) {
		query = event.detail;
		isLoading = true;
		error = null;
		results = null;

		try {
			results = await searchDatasets(query, 20);
		} catch (e) {
			if (e instanceof APIError) {
				error = e.message;
			} else {
				error = 'An unexpected error occurred';
			}
		} finally {
			isLoading = false;
		}
	}
</script>

<svelte:head>
	<title>Dataset Search & Discovery | University of Manchester</title>
	<meta name="description" content="Semantic search for environmental datasets" />
</svelte:head>

<div class="space-y-8">
	<!-- Hero Section -->
	<div class="text-center space-y-4 py-8">
		<div class="flex items-center justify-center gap-2">
			<Sparkles class="w-8 h-8 text-primary" />
			<h2 class="text-4xl font-bold text-foreground">Discover Environmental Datasets</h2>
		</div>
		<p class="text-lg text-muted-foreground max-w-2xl mx-auto">
			Search through curated datasets using advanced semantic search powered by AI
		</p>
		<a 
			href="/chat" 
			class="inline-flex items-center gap-2 px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors mt-4"
		>
			<MessageCircle class="w-5 h-5" />
			Chat with Dataset Assistant
		</a>
	</div>

	<!-- Search Bar -->
	<SearchBar {isLoading} on:search={handleSearch} />

	<!-- Error Display -->
	{#if error}
		<div class="max-w-3xl mx-auto">
			<div class="flex items-start gap-3 p-4 bg-destructive/10 border border-destructive/30 rounded-lg">
				<AlertCircle class="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
				<div>
					<h3 class="font-semibold text-destructive">Search Error</h3>
					<p class="text-sm text-destructive/90">{error}</p>
				</div>
			</div>
		</div>
	{/if}

	<!-- Results -->
	{#if results}
		<div class="max-w-5xl mx-auto space-y-6">
			<div class="flex items-center justify-between">
				<h3 class="text-2xl font-semibold text-foreground">
					{results.total_results} result{results.total_results !== 1 ? 's' : ''} found
				</h3>
				<div class="text-sm text-muted-foreground">
					Search completed in {results.processing_time_ms.toFixed(0)}ms
				</div>
			</div>

			{#if results.total_results === 0}
				<div class="text-center py-12">
					<p class="text-muted-foreground text-lg">
						No datasets found for "{query}". Try a different search term.
					</p>
				</div>
			{:else}
				<div class="grid gap-6">
					{#each results.results as dataset (dataset.id)}
						<DatasetCard {dataset} />
					{/each}
				</div>
			{/if}
		</div>
	{:else if !isLoading}
		<!-- Welcome State -->
		<div class="text-center py-16 max-w-2xl mx-auto">
			<div class="space-y-4">
				<h3 class="text-2xl font-semibold text-foreground">Ready to explore?</h3>
				<p class="text-muted-foreground">
					Try searching for topics like "land cover", "climate data", or "biodiversity"
				</p>
				<div class="flex flex-wrap justify-center gap-2 pt-4">
					{#each ['land cover mapping', 'environmental data', 'geographic information'] as suggestion}
						<button
							on:click={() => handleSearch(new CustomEvent('search', { detail: suggestion }))}
							class="px-4 py-2 text-sm border border-border rounded-full hover:bg-secondary transition-colors"
						>
							{suggestion}
						</button>
					{/each}
				</div>
			</div>
		</div>
	{/if}
</div>
