<script lang="ts">
	import ChatInterface from '$lib/components/ChatInterface.svelte';
</script>

<svelte:head>
	<title>Dataset Chat | Dataset Search</title>
</svelte:head>

<div class="chat-page">
	<div class="chat-wrapper">
		<ChatInterface />
	</div>
	
	<div class="back-link">
		<a href="/">← Back to Search</a>
	</div>
</div>

<style>
	.chat-page {
		min-height: 100vh;
		background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
		padding: 40px 20px;
	}
	
	.chat-wrapper {
		max-width: 800px;
		margin: 0 auto;
	}
	
	.back-link {
		max-width: 800px;
		margin: 16px auto 0;
	}
	
	.back-link a {
		color: #2563eb;
		text-decoration: none;
		font-size: 0.875rem;
	}
	
	.back-link a:hover {
		text-decoration: underline;
	}
</style>
