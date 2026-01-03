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
	<meta name="description" content="Search and discover environmental research datasets" />
</svelte:head>

<div class="page-wrapper">
	<!-- Hero -->
	<header class="hero-section">
		<div class="hero-icon">
			<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
				<ellipse cx="12" cy="5" rx="9" ry="3"/>
				<path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
				<path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
			</svg>
		</div>
		<h1>Environmental Dataset Discovery</h1>
		<p>Search across curated research datasets from the UK Centre for Ecology and Hydrology</p>
		<a href="/chat" class="btn-query">
			<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<circle cx="11" cy="11" r="8"/>
				<path d="m21 21-4.35-4.35"/>
			</svg>
			Advanced Query
		</a>
	</header>

	<!-- Search -->
	<SearchBar {isLoading} on:search={handleSearch} />

	<!-- Error -->
	{#if error}
		<div class="error-card">
			<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<circle cx="12" cy="12" r="10"/>
				<line x1="12" y1="8" x2="12" y2="12"/>
				<line x1="12" y1="16" x2="12.01" y2="16"/>
			</svg>
			<div>
				<strong>Search Error</strong>
				<span>{error}</span>
			</div>
		</div>
	{/if}

	<!-- Results -->
	{#if results}
		<div class="results-section">
			<div class="results-header">
				<h2>{results.total_results} result{results.total_results !== 1 ? 's' : ''}</h2>
				<span class="results-time">{results.processing_time_ms.toFixed(0)}ms</span>
			</div>

			{#if results.total_results === 0}
				<div class="empty-results">
					<p>No datasets found for "{query}"</p>
					<span>Try different keywords or check spelling</span>
				</div>
			{:else}
				<div class="results-grid">
					{#each results.results as dataset (dataset.id)}
						<DatasetCard {dataset} />
					{/each}
				</div>
			{/if}
		</div>
	{:else if !isLoading}
		<!-- Welcome -->
		<div class="welcome-section">
			<h2>Ready to explore?</h2>
			<p>Search for topics like land cover, climate data, or biodiversity</p>
			<div class="topic-pills">
				{#each ['land cover mapping', 'climate monitoring', 'biodiversity survey'] as topic}
					<button class="topic-pill" on:click={() => handleSearch(new CustomEvent('search', { detail: topic }))}>
						{topic}
					</button>
				{/each}
			</div>
		</div>
	{/if}
</div>

<style>
	.page-wrapper {
		max-width: 960px;
		margin: 0 auto;
		padding: 40px 24px 80px;
		font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, sans-serif;
	}

	/* Hero */
	.hero-section {
		text-align: center;
		padding: 48px 0 40px;
	}

	.hero-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 56px;
		height: 56px;
		background: linear-gradient(135deg, #007AFF 0%, #5856D6 100%);
		border-radius: 16px;
		color: white;
		margin-bottom: 20px;
	}

	.hero-section h1 {
		margin: 0 0 10px 0;
		font-size: 32px;
		font-weight: 600;
		color: #1d1d1f;
		letter-spacing: -0.02em;
	}

	.hero-section p {
		margin: 0 0 24px 0;
		font-size: 16px;
		color: #86868b;
		max-width: 400px;
		margin-left: auto;
		margin-right: auto;
	}

	.btn-query {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		padding: 12px 24px;
		background: #1d1d1f;
		color: white;
		border-radius: 24px;
		font-size: 14px;
		font-weight: 500;
		text-decoration: none;
		transition: all 0.2s ease;
	}

	.btn-query:hover {
		background: #000;
		transform: scale(1.02);
	}

	/* Error */
	.error-card {
		display: flex;
		align-items: flex-start;
		gap: 12px;
		max-width: 600px;
		margin: 24px auto;
		padding: 16px 20px;
		background: #FFF2F2;
		border: 1px solid #FFE5E5;
		border-radius: 12px;
		color: #FF3B30;
	}

	.error-card strong {
		display: block;
		font-size: 14px;
		margin-bottom: 2px;
	}

	.error-card span {
		font-size: 13px;
		opacity: 0.9;
	}

	/* Results */
	.results-section {
		margin-top: 32px;
	}

	.results-header {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		margin-bottom: 20px;
		padding-bottom: 16px;
		border-bottom: 1px solid rgba(0, 0, 0, 0.06);
	}

	.results-header h2 {
		margin: 0;
		font-size: 22px;
		font-weight: 600;
		color: #1d1d1f;
	}

	.results-time {
		font-size: 13px;
		color: #86868b;
	}

	.results-grid {
		display: flex;
		flex-direction: column;
		gap: 16px;
	}

	.empty-results {
		text-align: center;
		padding: 60px 20px;
	}

	.empty-results p {
		margin: 0 0 8px 0;
		font-size: 17px;
		color: #1d1d1f;
	}

	.empty-results span {
		font-size: 14px;
		color: #86868b;
	}

	/* Welcome */
	.welcome-section {
		text-align: center;
		padding: 60px 20px;
	}

	.welcome-section h2 {
		margin: 0 0 8px 0;
		font-size: 22px;
		font-weight: 600;
		color: #1d1d1f;
	}

	.welcome-section p {
		margin: 0 0 24px 0;
		font-size: 15px;
		color: #86868b;
	}

	.topic-pills {
		display: flex;
		flex-wrap: wrap;
		gap: 10px;
		justify-content: center;
	}

	.topic-pill {
		padding: 10px 20px;
		background: rgba(0, 0, 0, 0.03);
		border: 1px solid rgba(0, 0, 0, 0.06);
		border-radius: 24px;
		font-size: 14px;
		font-weight: 500;
		color: #1d1d1f;
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.topic-pill:hover {
		background: rgba(0, 122, 255, 0.08);
		border-color: rgba(0, 122, 255, 0.2);
		color: #007AFF;
	}
</style>
