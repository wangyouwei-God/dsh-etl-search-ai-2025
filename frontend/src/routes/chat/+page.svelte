<script lang="ts">
	import ChatInterface from '$lib/components/ChatInterface.svelte';
</script>

<svelte:head>
	<title>Dataset Query | UK Centre for Ecology and Hydrology</title>
</svelte:head>

<div class="page">
	<div class="container">
		<ChatInterface />
	</div>
	
	<nav class="back-nav">
		<a href="/">Back to Search</a>
	</nav>
</div>

<style>
	.page {
		min-height: 100vh;
		background: #f5f5f5;
		padding: 48px 24px;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
	}
	
	.container {
		max-width: 720px;
		margin: 0 auto;
	}
	
	.back-nav {
		max-width: 720px;
		margin: 24px auto 0;
	}
	
	.back-nav a {
		font-size: 13px;
		color: #888;
		text-decoration: none;
		transition: color 0.15s ease;
	}
	
	.back-nav a:hover {
		color: #1a1a1a;
	}
</style>
