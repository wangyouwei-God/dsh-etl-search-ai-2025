<script lang="ts">
	import { sendChatMessage } from '$lib/api';
	import type { ChatMessage, ChatSource } from '$lib/types';

	// State
	let messages: ChatMessage[] = [];
	let inputMessage = '';
	let isLoading = false;
	let error = '';
	let conversationId: string | null = null;

	// Generate unique ID
	function generateId(): string {
		return Math.random().toString(36).substring(2, 15);
	}

	// Send message
	async function handleSend() {
		if (!inputMessage.trim() || isLoading) return;

		const userMessage = inputMessage.trim();
		inputMessage = '';
		error = '';

		// Add user message
		const userMsg: ChatMessage = {
			id: generateId(),
			role: 'user',
			content: userMessage,
			timestamp: new Date()
		};
		messages = [...messages, userMsg];

		// Show loading
		isLoading = true;

		try {
			const response = await sendChatMessage(userMessage, conversationId || undefined);

			// Store conversation ID
			conversationId = response.conversation_id;

			// Add assistant message
			const assistantMsg: ChatMessage = {
				id: generateId(),
				role: 'assistant',
				content: response.answer,
				timestamp: new Date(),
				sources: response.sources
			};
			messages = [...messages, assistantMsg];
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to send message';
		} finally {
			isLoading = false;
		}
	}

	// Handle Enter key
	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			handleSend();
		}
	}

	// Clear conversation
	function clearConversation() {
		messages = [];
		conversationId = null;
		error = '';
	}

	// Format relevance score
	function formatScore(score: number): string {
		return `${Math.round(score * 100)}%`;
	}
</script>

<div class="chat-container">
	<header class="chat-header">
		<div class="header-content">
			<div class="header-icon">
				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
					<path d="M20 6L9 17l-5-5" />
				</svg>
			</div>
			<div class="header-text">
				<h1>Dataset Discovery</h1>
				<p>Environmental research data query interface</p>
			</div>
		</div>
		{#if messages.length > 0}
			<button class="btn-clear" on:click={clearConversation}>
				New Session
			</button>
		{/if}
	</header>

	<main class="messages-area">
		{#if messages.length === 0}
			<div class="empty-state">
				<div class="empty-icon">
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
						<circle cx="11" cy="11" r="8" />
						<path d="m21 21-4.35-4.35" />
					</svg>
				</div>
				<h2>Query Environmental Datasets</h2>
				<p>
					Search across curated research datasets from the UK Centre for Ecology and Hydrology.
					Enter your query below or select a suggested topic.
				</p>
				<div class="suggested-queries">
					<button
						class="query-chip"
						on:click={() => (inputMessage = 'What datasets are available for land cover analysis?')}
					>
						Land cover analysis
					</button>
					<button
						class="query-chip"
						on:click={() => (inputMessage = 'Show me climate and weather datasets')}
					>
						Climate data
					</button>
					<button
						class="query-chip"
						on:click={() => (inputMessage = 'What biodiversity monitoring data exists?')}
					>
						Biodiversity monitoring
					</button>
				</div>
			</div>
		{:else}
			<div class="message-list">
				{#each messages as message}
					<article class="message {message.role}">
						<div class="message-indicator">
							{#if message.role === 'user'}
								<span class="indicator-user">Q</span>
							{:else}
								<span class="indicator-system">A</span>
							{/if}
						</div>
						<div class="message-body">
							<div class="message-text">{@html message.content.replace(/\n/g, '<br>')}</div>

							{#if message.sources && message.sources.length > 0}
								<div class="sources-panel">
									<h4>Related Datasets</h4>
									<ul class="sources-list">
										{#each message.sources as source}
											<li>
												<a href="/datasets/{source.id}" class="source-link">
													<span class="source-title">{source.title}</span>
													<span class="source-score">{formatScore(source.relevance_score)} match</span>
												</a>
											</li>
										{/each}
									</ul>
								</div>
							{/if}
						</div>
					</article>
				{/each}

				{#if isLoading}
					<article class="message assistant">
						<div class="message-indicator">
							<span class="indicator-system">A</span>
						</div>
						<div class="message-body">
							<div class="loading-indicator">
								<span></span>
								<span></span>
								<span></span>
							</div>
						</div>
					</article>
				{/if}
			</div>
		{/if}
	</main>

	{#if error}
		<div class="error-banner">
			<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="error-icon">
				<circle cx="12" cy="12" r="10" />
				<line x1="12" y1="8" x2="12" y2="12" />
				<line x1="12" y1="16" x2="12.01" y2="16" />
			</svg>
			<span>{error}</span>
		</div>
	{/if}

	<footer class="input-area">
		<div class="input-wrapper">
			<textarea
				bind:value={inputMessage}
				on:keydown={handleKeydown}
				placeholder="Enter your query..."
				disabled={isLoading}
				rows="1"
			></textarea>
			<button 
				class="btn-submit" 
				on:click={handleSend} 
				disabled={isLoading || !inputMessage.trim()}
				aria-label="Submit query"
			>
				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M5 12h14M12 5l7 7-7 7" />
				</svg>
			</button>
		</div>
	</footer>
</div>

<style>
	.chat-container {
		display: flex;
		flex-direction: column;
		height: 600px;
		max-height: 80vh;
		background: #ffffff;
		border: 1px solid #e5e7eb;
		border-radius: 8px;
		overflow: hidden;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
	}

	/* Header */
	.chat-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 16px 24px;
		background: #fafafa;
		border-bottom: 1px solid #e5e7eb;
	}

	.header-content {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.header-icon {
		width: 32px;
		height: 32px;
		background: #1a1a2e;
		border-radius: 6px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.header-icon svg {
		width: 18px;
		height: 18px;
		color: #ffffff;
	}

	.header-text h1 {
		margin: 0;
		font-size: 1rem;
		font-weight: 600;
		color: #1a1a2e;
		letter-spacing: -0.01em;
	}

	.header-text p {
		margin: 2px 0 0 0;
		font-size: 0.75rem;
		color: #6b7280;
		letter-spacing: 0.01em;
	}

	.btn-clear {
		padding: 8px 14px;
		background: transparent;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 0.8125rem;
		font-weight: 500;
		color: #4b5563;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.btn-clear:hover {
		background: #f3f4f6;
		border-color: #9ca3af;
	}

	/* Messages Area */
	.messages-area {
		flex: 1;
		overflow-y: auto;
		padding: 24px;
		background: #ffffff;
	}

	/* Empty State */
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 100%;
		text-align: center;
		padding: 40px 20px;
	}

	.empty-icon {
		width: 48px;
		height: 48px;
		margin-bottom: 20px;
		color: #9ca3af;
	}

	.empty-icon svg {
		width: 100%;
		height: 100%;
	}

	.empty-state h2 {
		margin: 0 0 8px 0;
		font-size: 1.25rem;
		font-weight: 600;
		color: #1a1a2e;
	}

	.empty-state p {
		margin: 0 0 24px 0;
		max-width: 400px;
		font-size: 0.875rem;
		line-height: 1.6;
		color: #6b7280;
	}

	.suggested-queries {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		justify-content: center;
	}

	.query-chip {
		padding: 8px 16px;
		background: #f9fafb;
		border: 1px solid #e5e7eb;
		border-radius: 20px;
		font-size: 0.8125rem;
		color: #374151;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.query-chip:hover {
		background: #f3f4f6;
		border-color: #1a1a2e;
		color: #1a1a2e;
	}

	/* Message List */
	.message-list {
		display: flex;
		flex-direction: column;
		gap: 20px;
	}

	.message {
		display: flex;
		gap: 12px;
	}

	.message-indicator {
		flex-shrink: 0;
	}

	.message-indicator span {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		border-radius: 4px;
		font-size: 0.75rem;
		font-weight: 600;
	}

	.indicator-user {
		background: #1a1a2e;
		color: #ffffff;
	}

	.indicator-system {
		background: #e5e7eb;
		color: #374151;
	}

	.message-body {
		flex: 1;
		min-width: 0;
	}

	.message-text {
		font-size: 0.9375rem;
		line-height: 1.65;
		color: #1f2937;
	}

	.message.user .message-text {
		color: #1a1a2e;
		font-weight: 500;
	}

	/* Sources Panel */
	.sources-panel {
		margin-top: 16px;
		padding: 14px 16px;
		background: #f9fafb;
		border: 1px solid #e5e7eb;
		border-radius: 6px;
	}

	.sources-panel h4 {
		margin: 0 0 10px 0;
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: #6b7280;
	}

	.sources-list {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.sources-list li {
		margin-bottom: 6px;
	}

	.sources-list li:last-child {
		margin-bottom: 0;
	}

	.source-link {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 8px 10px;
		background: #ffffff;
		border: 1px solid #e5e7eb;
		border-radius: 4px;
		text-decoration: none;
		transition: all 0.15s ease;
	}

	.source-link:hover {
		border-color: #1a1a2e;
	}

	.source-title {
		font-size: 0.8125rem;
		color: #1a1a2e;
		font-weight: 500;
	}

	.source-score {
		font-size: 0.75rem;
		color: #6b7280;
	}

	/* Loading Indicator */
	.loading-indicator {
		display: flex;
		gap: 4px;
		padding: 4px 0;
	}

	.loading-indicator span {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: #9ca3af;
		animation: pulse 1.2s infinite;
	}

	.loading-indicator span:nth-child(2) {
		animation-delay: 0.15s;
	}

	.loading-indicator span:nth-child(3) {
		animation-delay: 0.3s;
	}

	@keyframes pulse {
		0%, 100% { opacity: 0.3; }
		50% { opacity: 1; }
	}

	/* Error Banner */
	.error-banner {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 12px 24px;
		background: #fef2f2;
		border-top: 1px solid #fecaca;
		font-size: 0.8125rem;
		color: #991b1b;
	}

	.error-icon {
		width: 16px;
		height: 16px;
		flex-shrink: 0;
	}

	/* Input Area */
	.input-area {
		padding: 16px 24px;
		background: #fafafa;
		border-top: 1px solid #e5e7eb;
	}

	.input-wrapper {
		display: flex;
		gap: 10px;
		align-items: flex-end;
	}

	.input-wrapper textarea {
		flex: 1;
		padding: 12px 14px;
		background: #ffffff;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-family: inherit;
		font-size: 0.9375rem;
		line-height: 1.4;
		resize: none;
		transition: border-color 0.15s ease;
	}

	.input-wrapper textarea:focus {
		outline: none;
		border-color: #1a1a2e;
	}

	.input-wrapper textarea::placeholder {
		color: #9ca3af;
	}

	.btn-submit {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 42px;
		height: 42px;
		background: #1a1a2e;
		border: none;
		border-radius: 6px;
		cursor: pointer;
		transition: background 0.15s ease;
	}

	.btn-submit svg {
		width: 18px;
		height: 18px;
		color: #ffffff;
	}

	.btn-submit:hover:not(:disabled) {
		background: #2d2d44;
	}

	.btn-submit:disabled {
		background: #d1d5db;
		cursor: not-allowed;
	}
</style>
