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
		<h1>Dataset Query</h1>
		{#if messages.length > 0}
			<button class="btn-text" on:click={clearConversation}>Clear</button>
		{/if}
	</header>

	<main class="content-area">
		{#if messages.length === 0}
			<div class="intro">
				<h2>Query Environmental Datasets</h2>
				<p>
					Enter a natural language query to search across research datasets 
					from the UK Centre for Ecology and Hydrology catalogue.
				</p>
				<div class="example-queries">
					<span class="label">Example queries:</span>
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
		{:else}
			<div class="conversation">
				{#each messages as message}
					<div class="turn {message.role}">
						<div class="turn-label">{message.role === 'user' ? 'Query' : 'Response'}</div>
						<div class="turn-content">
							{@html message.content.replace(/\n/g, '<br>')}
						</div>
						
						{#if message.sources && message.sources.length > 0}
							<div class="sources">
								<div class="sources-header">Related Datasets ({message.sources.length})</div>
								<ul>
									{#each message.sources as source}
										<li>
											<a href="/datasets/{source.id}">{source.title}</a>
											<span class="match">Relevance: {formatScore(source.relevance_score)}</span>
										</li>
									{/each}
								</ul>
							</div>
						{/if}
					</div>
				{/each}

				{#if isLoading}
					<div class="turn assistant">
						<div class="turn-label">Response</div>
						<div class="turn-content loading">
							Processing query...
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</main>

	{#if error}
		<div class="error-bar">{error}</div>
	{/if}

	<footer class="input-area">
		<label for="query-input" class="sr-only">Enter query</label>
		<textarea
			id="query-input"
			bind:value={inputMessage}
			on:keydown={handleKeydown}
			placeholder="Enter your query..."
			disabled={isLoading}
			rows="2"
		></textarea>
		<button 
			class="btn-submit" 
			on:click={handleSend} 
			disabled={isLoading || !inputMessage.trim()}
		>
			{isLoading ? 'Processing...' : 'Submit Query'}
		</button>
	</footer>
</div>

<style>
	.query-panel {
		display: flex;
		flex-direction: column;
		height: 600px;
		max-height: 80vh;
		background: #fff;
		border: 1px solid #d0d0d0;
		font-family: 'Georgia', 'Times New Roman', serif;
	}

	/* Header */
	.panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 14px 20px;
		border-bottom: 1px solid #d0d0d0;
		background: #fafafa;
	}

	.panel-header h1 {
		margin: 0;
		font-size: 16px;
		font-weight: 600;
		color: #000;
		letter-spacing: -0.01em;
	}

	.btn-text {
		padding: 4px 10px;
		background: none;
		border: 1px solid #999;
		font-family: -apple-system, BlinkMacSystemFont, sans-serif;
		font-size: 12px;
		color: #666;
		cursor: pointer;
	}

	.btn-text:hover {
		background: #f0f0f0;
		color: #000;
		border-color: #000;
	}

	/* Content */
	.content-area {
		flex: 1;
		overflow-y: auto;
		padding: 24px;
	}

	/* Intro */
	.intro {
		max-width: 520px;
	}

	.intro h2 {
		margin: 0 0 12px 0;
		font-size: 20px;
		font-weight: 600;
		color: #000;
	}

	.intro p {
		margin: 0 0 24px 0;
		font-size: 14px;
		line-height: 1.7;
		color: #444;
	}

	.example-queries {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		align-items: center;
	}

	.example-queries .label {
		font-family: -apple-system, BlinkMacSystemFont, sans-serif;
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: #888;
		margin-right: 4px;
	}

	.example-queries button {
		padding: 6px 12px;
		background: #fff;
		border: 1px solid #ccc;
		font-family: -apple-system, BlinkMacSystemFont, sans-serif;
		font-size: 12px;
		color: #333;
		cursor: pointer;
	}

	.example-queries button:hover {
		background: #f5f5f5;
		border-color: #000;
	}

	/* Conversation */
	.conversation {
		display: flex;
		flex-direction: column;
		gap: 24px;
	}

	.turn {
		padding-bottom: 20px;
		border-bottom: 1px solid #e5e5e5;
	}

	.turn:last-child {
		border-bottom: none;
	}

	.turn-label {
		font-family: -apple-system, BlinkMacSystemFont, sans-serif;
		font-size: 11px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: #888;
		margin-bottom: 8px;
	}

	.turn.user .turn-label {
		color: #000;
	}

	.turn-content {
		font-size: 15px;
		line-height: 1.7;
		color: #1a1a1a;
	}

	.turn.user .turn-content {
		font-style: italic;
		color: #333;
	}

	.turn-content.loading {
		color: #888;
		font-style: italic;
	}

	/* Sources */
	.sources {
		margin-top: 16px;
		padding: 14px 16px;
		background: #f8f8f8;
		border: 1px solid #e0e0e0;
	}

	.sources-header {
		font-family: -apple-system, BlinkMacSystemFont, sans-serif;
		font-size: 11px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: #666;
		margin-bottom: 10px;
	}

	.sources ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.sources li {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		padding: 8px 0;
		border-bottom: 1px solid #e8e8e8;
		font-family: -apple-system, BlinkMacSystemFont, sans-serif;
	}

	.sources li:last-child {
		border-bottom: none;
		padding-bottom: 0;
	}

	.sources a {
		font-size: 13px;
		color: #000;
		text-decoration: none;
	}

	.sources a:hover {
		text-decoration: underline;
	}

	.sources .match {
		font-size: 11px;
		color: #888;
	}

	/* Error */
	.error-bar {
		padding: 10px 20px;
		background: #fff0f0;
		border-top: 1px solid #ffcccc;
		font-family: -apple-system, BlinkMacSystemFont, sans-serif;
		font-size: 13px;
		color: #c00;
	}

	/* Input */
	.input-area {
		display: flex;
		gap: 12px;
		padding: 16px 20px;
		background: #fafafa;
		border-top: 1px solid #d0d0d0;
	}

	.sr-only {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		border: 0;
	}

	.input-area textarea {
		flex: 1;
		padding: 10px 12px;
		background: #fff;
		border: 1px solid #ccc;
		font-family: -apple-system, BlinkMacSystemFont, sans-serif;
		font-size: 14px;
		line-height: 1.4;
		resize: none;
	}

	.input-area textarea:focus {
		outline: none;
		border-color: #000;
	}

	.input-area textarea::placeholder {
		color: #999;
	}

	.btn-submit {
		padding: 10px 20px;
		background: #000;
		border: none;
		font-family: -apple-system, BlinkMacSystemFont, sans-serif;
		font-size: 13px;
		font-weight: 500;
		color: #fff;
		cursor: pointer;
		white-space: nowrap;
	}

	.btn-submit:hover:not(:disabled) {
		background: #333;
	}

	.btn-submit:disabled {
		background: #ccc;
		cursor: not-allowed;
	}
</style>
