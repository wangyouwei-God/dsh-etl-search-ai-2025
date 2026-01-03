<script lang="ts">
	import ChatInterface from '$lib/components/ChatInterface.svelte';
</script>

<svelte:head>
	<title>Dataset Query | UK Centre for Ecology and Hydrology</title>
</svelte:head>

<div class="page-container">
	<div class="content-wrapper">
		<ChatInterface />
	</div>
	
	<nav class="nav-back">
		<a href="/">
			<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<path d="M19 12H5M12 19l-7-7 7-7"/>
			</svg>
			Back to Search
		</a>
	</nav>
</div>

<style>
	.page-container {
		min-height: 100vh;
		background: linear-gradient(180deg, #f5f5f7 0%, #e8e8ed 100%);
		padding: 48px 24px;
	}
	
	.content-wrapper {
		max-width: 680px;
		margin: 0 auto;
	}
	
	.nav-back {
		max-width: 680px;
		margin: 24px auto 0;
	}
	
	.nav-back a {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		color: #86868b;
		text-decoration: none;
		font-size: 14px;
		font-weight: 500;
		font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif;
		transition: color 0.2s ease;
	}
	
	.nav-back a:hover {
		color: #007AFF;
	}
	
	.nav-back svg {
		transition: transform 0.2s ease;
	}
	
	.nav-back a:hover svg {
		transform: translateX(-3px);
	}
</style>
