<script lang="ts">
	import { sendChatMessage } from '$lib/api';
	import type { ChatMessage, ChatSource } from '$lib/types';

	let messages: ChatMessage[] = [];
	let inputMessage = '';
	let isLoading = false;
	let error = '';
	let conversationId: string | null = null;

	function generateId(): string {
		return Math.random().toString(36).substring(2, 15);
	}

	async function handleSend() {
		if (!inputMessage.trim() || isLoading) return;

		const userMessage = inputMessage.trim();
		inputMessage = '';
		error = '';

		const userMsg: ChatMessage = {
			id: generateId(),
			role: 'user',
			content: userMessage,
			timestamp: new Date()
		};
		messages = [...messages, userMsg];
		isLoading = true;

		try {
			const response = await sendChatMessage(userMessage, conversationId || undefined);
			conversationId = response.conversation_id;

			const assistantMsg: ChatMessage = {
				id: generateId(),
				role: 'assistant',
				content: response.answer,
				timestamp: new Date(),
				sources: response.sources
			};
			messages = [...messages, assistantMsg];
		} catch (err) {
			error = err instanceof Error ? err.message : 'Request failed';
		} finally {
			isLoading = false;
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			handleSend();
		}
	}

	function clearConversation() {
		messages = [];
		conversationId = null;
		error = '';
	}

	function formatScore(score: number): string {
		return `${Math.round(score * 100)}%`;
	}

	function setQuery(text: string) {
		inputMessage = text;
	}
</script>

<div class="query-panel">
	<header class="panel-header">
		<div class="header-brand">
			<div class="brand-mark"></div>
			<div class="brand-text">
				<h1>Dataset Query</h1>
				<span>UK Centre for Ecology and Hydrology</span>
			</div>
		</div>
		{#if messages.length > 0}
			<button class="btn-secondary" on:click={clearConversation}>New Query</button>
		{/if}
	</header>

	<main class="content-area">
		{#if messages.length === 0}
			<div class="intro">
				<h2>Search Environmental Research Data</h2>
				<p>
					Enter a natural language query to search across curated datasets 
					from the UK's leading environmental research institution.
				</p>
				<div class="suggestions">
					<span class="suggestions-label">Suggested queries</span>
					<div class="suggestion-buttons">
						<button on:click={() => setQuery('What land cover datasets are available?')}>
							Land cover datasets
						</button>
						<button on:click={() => setQuery('Climate monitoring data for UK')}>
							Climate monitoring
						</button>
						<button on:click={() => setQuery('Biodiversity survey data')}>
							Biodiversity surveys
						</button>
					</div>
				</div>
			</div>
		{:else}
			<div class="conversation">
				{#each messages as message}
					<article class="turn {message.role}">
						<header class="turn-header">
							<span class="turn-type">{message.role === 'user' ? 'Query' : 'Response'}</span>
						</header>
						<div class="turn-body">
							{@html message.content.replace(/\n/g, '<br>')}
						</div>
						
						{#if message.sources && message.sources.length > 0}
							<aside class="sources-panel">
								<h4>Related Datasets</h4>
								<ul>
									{#each message.sources as source}
										<li>
											<a href="/datasets/{source.id}">{source.title}</a>
											<span class="relevance">{formatScore(source.relevance_score)} relevance</span>
										</li>
									{/each}
								</ul>
							</aside>
						{/if}
					</article>
				{/each}

				{#if isLoading}
					<article class="turn assistant">
						<header class="turn-header">
							<span class="turn-type">Response</span>
						</header>
						<div class="turn-body loading">
							<span class="loading-text">Processing your query</span>
							<span class="loading-dots"><span></span><span></span><span></span></span>
						</div>
					</article>
				{/if}
			</div>
		{/if}
	</main>

	{#if error}
		<div class="error-bar">{error}</div>
	{/if}

	<footer class="input-area">
		<div class="input-wrapper">
			<textarea
				bind:value={inputMessage}
				on:keydown={handleKeydown}
				placeholder="Enter your query..."
				disabled={isLoading}
				rows="2"
			></textarea>
		</div>
		<button 
			class="btn-primary" 
			on:click={handleSend} 
			disabled={isLoading || !inputMessage.trim()}
		>
			{isLoading ? 'Processing...' : 'Submit'}
		</button>
	</footer>
</div>

<style>
	.query-panel {
		display: flex;
		flex-direction: column;
		height: 620px;
		max-height: 82vh;
		background: #ffffff;
		border-radius: 8px;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08), 0 4px 12px rgba(0, 0, 0, 0.05);
		overflow: hidden;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
	}

	/* Header */
	.panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 18px 24px;
		background: #fafafa;
		border-bottom: 1px solid #eaeaea;
	}

	.header-brand {
		display: flex;
		align-items: center;
		gap: 14px;
	}

	.brand-mark {
		width: 10px;
		height: 32px;
		background: #1a1a1a;
		border-radius: 2px;
	}

	.brand-text h1 {
		margin: 0;
		font-size: 17px;
		font-weight: 600;
		color: #1a1a1a;
		letter-spacing: -0.02em;
	}

	.brand-text span {
		font-size: 12px;
		color: #888;
		letter-spacing: 0.01em;
	}

	.btn-secondary {
		padding: 8px 16px;
		background: #fff;
		border: 1px solid #d0d0d0;
		border-radius: 6px;
		font-size: 13px;
		font-weight: 500;
		color: #444;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.btn-secondary:hover {
		background: #f5f5f5;
		border-color: #1a1a1a;
		color: #1a1a1a;
	}

	/* Content */
	.content-area {
		flex: 1;
		overflow-y: auto;
		padding: 32px 28px;
	}

	/* Intro */
	.intro {
		max-width: 480px;
	}

	.intro h2 {
		margin: 0 0 12px 0;
		font-size: 22px;
		font-weight: 600;
		color: #1a1a1a;
		letter-spacing: -0.02em;
	}

	.intro p {
		margin: 0 0 28px 0;
		font-size: 15px;
		line-height: 1.65;
		color: #555;
	}

	.suggestions {
		padding-top: 20px;
		border-top: 1px solid #eee;
	}

	.suggestions-label {
		display: block;
		margin-bottom: 12px;
		font-size: 11px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: #999;
	}

	.suggestion-buttons {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}

	.suggestion-buttons button {
		padding: 9px 16px;
		background: #fff;
		border: 1px solid #ddd;
		border-radius: 6px;
		font-size: 13px;
		color: #444;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.suggestion-buttons button:hover {
		background: #fafafa;
		border-color: #1a1a1a;
		color: #1a1a1a;
	}

	/* Conversation */
	.conversation {
		display: flex;
		flex-direction: column;
		gap: 28px;
	}

	.turn {
		padding-bottom: 24px;
		border-bottom: 1px solid #f0f0f0;
	}

	.turn:last-child {
		border-bottom: none;
		padding-bottom: 0;
	}

	.turn-header {
		margin-bottom: 10px;
	}

	.turn-type {
		font-size: 11px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: #aaa;
	}

	.turn.user .turn-type {
		color: #1a1a1a;
	}

	.turn-body {
		font-size: 15px;
		line-height: 1.7;
		color: #333;
	}

	.turn.user .turn-body {
		color: #1a1a1a;
		font-weight: 500;
	}

	.turn-body.loading {
		display: flex;
		align-items: center;
		gap: 8px;
		color: #999;
	}

	.loading-text {
		font-style: italic;
	}

	.loading-dots {
		display: flex;
		gap: 3px;
	}

	.loading-dots span {
		width: 4px;
		height: 4px;
		background: #999;
		border-radius: 50%;
		animation: dot-pulse 1.2s infinite;
	}

	.loading-dots span:nth-child(2) { animation-delay: 0.15s; }
	.loading-dots span:nth-child(3) { animation-delay: 0.3s; }

	@keyframes dot-pulse {
		0%, 100% { opacity: 0.3; }
		50% { opacity: 1; }
	}

	/* Sources */
	.sources-panel {
		margin-top: 20px;
		padding: 18px 20px;
		background: #fafafa;
		border-radius: 6px;
	}

	.sources-panel h4 {
		margin: 0 0 14px 0;
		font-size: 11px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: #888;
	}

	.sources-panel ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.sources-panel li {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		padding: 10px 0;
		border-bottom: 1px solid #eee;
	}

	.sources-panel li:last-child {
		border-bottom: none;
		padding-bottom: 0;
	}

	.sources-panel a {
		font-size: 14px;
		font-weight: 500;
		color: #1a1a1a;
		text-decoration: none;
		transition: color 0.15s ease;
	}

	.sources-panel a:hover {
		color: #555;
	}

	.sources-panel .relevance {
		font-size: 12px;
		color: #999;
	}

	/* Error */
	.error-bar {
		padding: 12px 24px;
		background: #fff8f8;
		border-top: 1px solid #ffe0e0;
		font-size: 13px;
		color: #b00;
	}

	/* Input */
	.input-area {
		display: flex;
		gap: 12px;
		padding: 18px 24px;
		background: #fafafa;
		border-top: 1px solid #eaeaea;
	}

	.input-wrapper {
		flex: 1;
	}

	.input-wrapper textarea {
		width: 100%;
		padding: 12px 14px;
		background: #fff;
		border: 1px solid #d0d0d0;
		border-radius: 6px;
		font-family: inherit;
		font-size: 14px;
		line-height: 1.5;
		resize: none;
		transition: border-color 0.15s ease;
	}

	.input-wrapper textarea:focus {
		outline: none;
		border-color: #1a1a1a;
	}

	.input-wrapper textarea::placeholder {
		color: #aaa;
	}

	.btn-primary {
		padding: 12px 24px;
		background: #1a1a1a;
		border: none;
		border-radius: 6px;
		font-size: 14px;
		font-weight: 500;
		color: #fff;
		cursor: pointer;
		transition: all 0.15s ease;
		align-self: flex-end;
	}

	.btn-primary:hover:not(:disabled) {
		background: #333;
	}

	.btn-primary:disabled {
		background: #ccc;
		cursor: not-allowed;
	}
</style>
