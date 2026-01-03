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

<div class="page">
	<header class="page-header">
		<div class="brand">
			<div class="brand-mark"></div>
			<div class="brand-text">
				<h1>Environmental Dataset Search</h1>
				<span>UK Centre for Ecology and Hydrology</span>
			</div>
		</div>
	</header>

	<main class="main-content">
		<SearchBar {isLoading} on:search={handleSearch} />

		<nav class="secondary-nav">
			<a href="/chat">Advanced Query Interface</a>
		</nav>

		{#if error}
			<div class="error-card">
				<strong>Error:</strong> {error}
			</div>
		{/if}

		{#if results}
			<section class="results-section">
				<header class="results-header">
					<h2>{results.total_results} result{results.total_results !== 1 ? 's' : ''}</h2>
					<span class="meta">{results.processing_time_ms.toFixed(0)}ms</span>
				</header>

				{#if results.total_results === 0}
					<p class="empty-state">No datasets found for "{query}". Try different search terms.</p>
				{:else}
					<div class="results-list">
						{#each results.results as dataset (dataset.id)}
							<DatasetCard {dataset} />
						{/each}
					</div>
				{/if}
			</section>
		{:else if !isLoading}
			<section class="welcome-card">
				<h2>Search the Catalogue</h2>
				<p>Enter keywords to search across curated environmental research datasets.</p>
				<div class="topics">
					<span class="topics-label">Example topics</span>
					<div class="topic-buttons">
						{#each ['Land cover mapping', 'Climate data', 'Biodiversity monitoring'] as topic}
							<button on:click={() => handleSearch(new CustomEvent('search', { detail: topic }))}>
								{topic}
							</button>
						{/each}
					</div>
				</div>
			</section>
		{/if}
	</main>

	<footer class="page-footer">
		<span>Research Software Engineering Assessment</span>
	</footer>
</div>

<style>
	.page {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
		background: #f8f8f8;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
	}

	/* Header */
	.page-header {
		padding: 28px 32px;
		background: #fff;
		border-bottom: 1px solid #eaeaea;
	}

	.brand {
		display: flex;
		align-items: center;
		gap: 16px;
		max-width: 800px;
		margin: 0 auto;
	}

	.brand-mark {
		width: 8px;
		height: 36px;
		background: #1a1a1a;
		border-radius: 2px;
	}

	.brand-text h1 {
		margin: 0;
		font-size: 20px;
		font-weight: 600;
		color: #1a1a1a;
		letter-spacing: -0.02em;
	}

	.brand-text span {
		font-size: 13px;
		color: #888;
	}

	/* Main */
	.main-content {
		flex: 1;
		max-width: 800px;
		width: 100%;
		margin: 0 auto;
		padding: 32px 24px 60px;
	}

	/* Nav */
	.secondary-nav {
		text-align: center;
		margin-top: 16px;
	}

	.secondary-nav a {
		font-size: 13px;
		color: #666;
		text-decoration: none;
		transition: color 0.15s ease;
	}

	.secondary-nav a:hover {
		color: #1a1a1a;
	}

	/* Error */
	.error-card {
		margin-top: 24px;
		padding: 16px 20px;
		background: #fff;
		border: 1px solid #f0d0d0;
		border-radius: 8px;
		font-size: 14px;
		color: #a00;
	}

	.error-card strong {
		font-weight: 600;
	}

	/* Results */
	.results-section {
		margin-top: 36px;
	}

	.results-header {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		padding-bottom: 16px;
		margin-bottom: 20px;
		border-bottom: 1px solid #e0e0e0;
	}

	.results-header h2 {
		margin: 0;
		font-size: 18px;
		font-weight: 600;
		color: #1a1a1a;
	}

	.results-header .meta {
		font-size: 12px;
		color: #999;
	}

	.results-list {
		display: flex;
		flex-direction: column;
		gap: 16px;
	}

	.empty-state {
		padding: 48px 0;
		text-align: center;
		font-size: 15px;
		color: #666;
	}

	/* Welcome */
	.welcome-card {
		margin-top: 40px;
		padding: 32px;
		background: #fff;
		border-radius: 8px;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
	}

	.welcome-card h2 {
		margin: 0 0 10px 0;
		font-size: 18px;
		font-weight: 600;
		color: #1a1a1a;
	}

	.welcome-card p {
		margin: 0 0 24px 0;
		font-size: 15px;
		line-height: 1.6;
		color: #555;
	}

	.topics {
		padding-top: 20px;
		border-top: 1px solid #f0f0f0;
	}

	.topics-label {
		display: block;
		margin-bottom: 12px;
		font-size: 11px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: #999;
	}

	.topic-buttons {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}

	.topic-buttons button {
		padding: 9px 16px;
		background: #fafafa;
		border: 1px solid #e0e0e0;
		border-radius: 6px;
		font-size: 13px;
		color: #444;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.topic-buttons button:hover {
		background: #fff;
		border-color: #1a1a1a;
		color: #1a1a1a;
	}

	/* Footer */
	.page-footer {
		padding: 20px 32px;
		background: #fff;
		border-top: 1px solid #eaeaea;
		text-align: center;
	}

	.page-footer span {
		font-size: 12px;
		color: #999;
	}
</style>
