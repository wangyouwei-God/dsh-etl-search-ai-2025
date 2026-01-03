<script lang="ts">
	import SearchBar from '$lib/components/SearchBar.svelte';
	import DatasetCard from '$lib/components/DatasetCard.svelte';
	import { searchDatasets, APIError } from '$lib/api';
	import type { SearchResponse } from '$lib/types';

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
	<title>Dataset Search | UK Centre for Ecology and Hydrology</title>
	<meta name="description" content="Search environmental research datasets" />
</svelte:head>

<div class="page-content">
	<!-- Header -->
	<header class="page-header">
		<h1>Environmental Dataset Search</h1>
		<p>UK Centre for Ecology and Hydrology Data Catalogue</p>
	</header>

	<!-- Search -->
	<SearchBar {isLoading} on:search={handleSearch} />

	<!-- Navigation -->
	<nav class="secondary-nav">
		<a href="/chat">Advanced Query Interface</a>
	</nav>

	<!-- Error -->
	{#if error}
		<div class="error-message">
			<strong>Error:</strong> {error}
		</div>
	{/if}

	<!-- Results -->
	{#if results}
		<section class="results-section">
			<div class="results-meta">
				<span class="results-count">{results.total_results} result{results.total_results !== 1 ? 's' : ''}</span>
				<span class="results-time">{results.processing_time_ms.toFixed(0)}ms</span>
			</div>

			{#if results.total_results === 0}
				<p class="no-results">No datasets found for "{query}". Please try different search terms.</p>
			{:else}
				<div class="results-list">
					{#each results.results as dataset (dataset.id)}
						<DatasetCard {dataset} />
					{/each}
				</div>
			{/if}
		</section>
	{:else if !isLoading}
		<!-- Welcome -->
		<section class="welcome-section">
			<h2>Search the Catalogue</h2>
			<p>Enter keywords to search across environmental research datasets. Example topics:</p>
			<ul class="topic-list">
				{#each ['Land cover mapping', 'Climate and weather data', 'Biodiversity monitoring'] as topic}
					<li>
						<button on:click={() => handleSearch(new CustomEvent('search', { detail: topic }))}>
							{topic}
						</button>
					</li>
				{/each}
			</ul>
		</section>
	{/if}
</div>

<style>
	.page-content {
		max-width: 800px;
		margin: 0 auto;
		padding: 40px 24px 80px;
		font-family: 'Georgia', 'Times New Roman', serif;
	}

	/* Header */
	.page-header {
		text-align: center;
		margin-bottom: 32px;
	}

	.page-header h1 {
		margin: 0 0 8px 0;
		font-size: 26px;
		font-weight: 600;
		color: #000;
		letter-spacing: -0.01em;
	}

	.page-header p {
		margin: 0;
		font-family: -apple-system, BlinkMacSystemFont, sans-serif;
		font-size: 13px;
		color: #666;
		letter-spacing: 0.02em;
	}

	/* Nav */
	.secondary-nav {
		text-align: center;
		margin-top: 16px;
	}

	.secondary-nav a {
		font-family: -apple-system, BlinkMacSystemFont, sans-serif;
		font-size: 13px;
		color: #666;
		text-decoration: none;
	}

	.secondary-nav a:hover {
		color: #000;
		text-decoration: underline;
	}

	/* Error */
	.error-message {
		margin-top: 24px;
		padding: 14px 18px;
		background: #fff8f8;
		border: 1px solid #f0cccc;
		font-family: -apple-system, BlinkMacSystemFont, sans-serif;
		font-size: 14px;
		color: #900;
	}

	.error-message strong {
		font-weight: 600;
	}

	/* Results */
	.results-section {
		margin-top: 32px;
	}

	.results-meta {
		display: flex;
		justify-content: space-between;
		padding-bottom: 12px;
		margin-bottom: 20px;
		border-bottom: 1px solid #ddd;
		font-family: -apple-system, BlinkMacSystemFont, sans-serif;
	}

	.results-count {
		font-size: 14px;
		font-weight: 600;
		color: #000;
	}

	.results-time {
		font-size: 12px;
		color: #888;
	}

	.results-list {
		display: flex;
		flex-direction: column;
		gap: 16px;
	}

	.no-results {
		padding: 40px 0;
		text-align: center;
		font-size: 15px;
		color: #666;
	}

	/* Welcome */
	.welcome-section {
		margin-top: 48px;
		padding: 32px;
		background: #fafafa;
		border: 1px solid #e0e0e0;
	}

	.welcome-section h2 {
		margin: 0 0 12px 0;
		font-size: 18px;
		font-weight: 600;
		color: #000;
	}

	.welcome-section p {
		margin: 0 0 20px 0;
		font-size: 14px;
		line-height: 1.6;
		color: #444;
	}

	.topic-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-wrap: wrap;
		gap: 10px;
	}

	.topic-list button {
		padding: 8px 16px;
		background: #fff;
		border: 1px solid #ccc;
		font-family: -apple-system, BlinkMacSystemFont, sans-serif;
		font-size: 13px;
		color: #333;
		cursor: pointer;
	}

	.topic-list button:hover {
		background: #f0f0f0;
		border-color: #000;
	}
</style>
