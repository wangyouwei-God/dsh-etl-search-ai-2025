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
	}
	
	.container {
		max-width: 700px;
		margin: 0 auto;
	}
	
	.back-nav {
		max-width: 700px;
		margin: 20px auto 0;
	}
	
	.back-nav a {
		font-family: -apple-system, BlinkMacSystemFont, sans-serif;
		font-size: 13px;
		color: #666;
		text-decoration: none;
	}
	
	.back-nav a:hover {
		color: #000;
		text-decoration: underline;
	}
</style>
