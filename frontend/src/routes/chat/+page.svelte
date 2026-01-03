<script lang="ts">
	import ChatInterface from '$lib/components/ChatInterface.svelte';
</script>

<svelte:head>
	<title>Dataset Query | UK Centre for Ecology and Hydrology</title>
</svelte:head>

<div class="query-page">
	<div class="query-wrapper">
		<ChatInterface />
	</div>
	
	<nav class="back-navigation">
		<a href="/">Return to Search</a>
	</nav>
</div>

<style>
	.query-page {
		min-height: 100vh;
		background: #f8f9fa;
		padding: 48px 24px;
	}
	
	.query-wrapper {
		max-width: 720px;
		margin: 0 auto;
	}
	
	.back-navigation {
		max-width: 720px;
		margin: 20px auto 0;
	}
	
	.back-navigation a {
		color: #6b7280;
		text-decoration: none;
		font-size: 0.875rem;
		display: inline-flex;
		align-items: center;
		gap: 4px;
		transition: color 0.15s ease;
	}
	
	.back-navigation a::before {
		content: '←';
	}
	
	.back-navigation a:hover {
		color: #1a1a2e;
	}
</style>
