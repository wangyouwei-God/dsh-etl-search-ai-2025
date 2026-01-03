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

<div class="chat-panel">
	<!-- Header -->
	<header class="panel-header">
		<div class="header-title">
			<span class="title-icon">
				<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
					<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
				</svg>
			</span>
			<div>
				<h1>Dataset Query</h1>
				<p>Environmental Research Data</p>
			</div>
		</div>
		{#if messages.length > 0}
			<button class="btn-secondary" on:click={clearConversation}>
				Clear
			</button>
		{/if}
	</header>

	<!-- Messages Area -->
	<main class="messages-scroll">
		{#if messages.length === 0}
			<div class="empty-view">
				<div class="empty-icon-wrapper">
					<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round">
						<circle cx="11" cy="11" r="8"/>
						<path d="m21 21-4.35-4.35"/>
					</svg>
				</div>
				<h2>Explore Datasets</h2>
				<p>Ask questions about environmental research data from the UK Centre for Ecology and Hydrology.</p>
				
				<div class="suggestions">
					<button class="suggestion-pill" on:click={() => setQuery('What land cover datasets are available?')}>
						Land Cover
					</button>
					<button class="suggestion-pill" on:click={() => setQuery('Show climate monitoring data')}>
						Climate Data
					</button>
					<button class="suggestion-pill" on:click={() => setQuery('Biodiversity survey datasets')}>
						Biodiversity
					</button>
				</div>
			</div>
		{:else}
			<div class="messages-list">
				{#each messages as message}
					<div class="message-row {message.role}">
						<div class="message-bubble">
							<div class="message-content">
								{@html message.content.replace(/\n/g, '<br>')}
							</div>
							
							{#if message.sources && message.sources.length > 0}
								<div class="sources-card">
									<span class="sources-label">Related Datasets</span>
									<div class="sources-items">
										{#each message.sources as source}
											<a href="/datasets/{source.id}" class="source-item">
												<span class="source-name">{source.title}</span>
												<span class="source-match">{formatScore(source.relevance_score)}</span>
											</a>
										{/each}
									</div>
								</div>
							{/if}
						</div>
					</div>
				{/each}

				{#if isLoading}
					<div class="message-row assistant">
						<div class="message-bubble">
							<div class="typing-dots">
								<span></span>
								<span></span>
								<span></span>
							</div>
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</main>

	<!-- Error -->
	{#if error}
		<div class="error-strip">
			{error}
		</div>
	{/if}

	<!-- Input -->
	<footer class="input-bar">
		<div class="input-field">
			<textarea
				bind:value={inputMessage}
				on:keydown={handleKeydown}
				placeholder="Ask a question..."
				disabled={isLoading}
				rows="1"
			></textarea>
			<button 
				class="btn-send" 
				on:click={handleSend} 
				disabled={isLoading || !inputMessage.trim()}
			>
				<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
					<path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
				</svg>
			</button>
		</div>
	</footer>
</div>

<style>
	/* === Base === */
	.chat-panel {
		display: flex;
		flex-direction: column;
		height: 640px;
		max-height: 85vh;
		background: rgba(255, 255, 255, 0.72);
		backdrop-filter: blur(20px);
		-webkit-backdrop-filter: blur(20px);
		border: 1px solid rgba(0, 0, 0, 0.08);
		border-radius: 16px;
		box-shadow: 
			0 0 0 0.5px rgba(0, 0, 0, 0.05),
			0 2px 8px rgba(0, 0, 0, 0.04),
			0 8px 24px rgba(0, 0, 0, 0.06);
		overflow: hidden;
		font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
	}

	/* === Header === */
	.panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 16px 20px;
		background: rgba(255, 255, 255, 0.6);
		border-bottom: 1px solid rgba(0, 0, 0, 0.06);
	}

	.header-title {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.title-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 36px;
		height: 36px;
		background: linear-gradient(135deg, #007AFF 0%, #5856D6 100%);
		border-radius: 10px;
		color: white;
	}

	.header-title h1 {
		margin: 0;
		font-size: 15px;
		font-weight: 600;
		color: #1d1d1f;
		letter-spacing: -0.01em;
	}

	.header-title p {
		margin: 1px 0 0 0;
		font-size: 12px;
		color: #86868b;
		letter-spacing: 0.01em;
	}

	.btn-secondary {
		padding: 6px 14px;
		background: rgba(0, 0, 0, 0.04);
		border: none;
		border-radius: 8px;
		font-size: 13px;
		font-weight: 500;
		color: #1d1d1f;
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.btn-secondary:hover {
		background: rgba(0, 0, 0, 0.08);
	}

	/* === Messages Area === */
	.messages-scroll {
		flex: 1;
		overflow-y: auto;
		padding: 24px 20px;
	}

	/* === Empty State === */
	.empty-view {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 100%;
		text-align: center;
		padding: 20px;
	}

	.empty-icon-wrapper {
		width: 72px;
		height: 72px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: linear-gradient(135deg, rgba(0, 122, 255, 0.1) 0%, rgba(88, 86, 214, 0.1) 100%);
		border-radius: 20px;
		color: #007AFF;
		margin-bottom: 20px;
	}

	.empty-view h2 {
		margin: 0 0 8px 0;
		font-size: 22px;
		font-weight: 600;
		color: #1d1d1f;
		letter-spacing: -0.02em;
	}

	.empty-view p {
		margin: 0 0 28px 0;
		max-width: 320px;
		font-size: 14px;
		line-height: 1.5;
		color: #86868b;
	}

	.suggestions {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		justify-content: center;
	}

	.suggestion-pill {
		padding: 10px 18px;
		background: rgba(0, 0, 0, 0.03);
		border: 1px solid rgba(0, 0, 0, 0.06);
		border-radius: 20px;
		font-size: 13px;
		font-weight: 500;
		color: #1d1d1f;
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.suggestion-pill:hover {
		background: rgba(0, 122, 255, 0.08);
		border-color: rgba(0, 122, 255, 0.2);
		color: #007AFF;
	}

	/* === Messages === */
	.messages-list {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	.message-row {
		display: flex;
	}

	.message-row.user {
		justify-content: flex-end;
	}

	.message-row.assistant {
		justify-content: flex-start;
	}

	.message-bubble {
		max-width: 85%;
		padding: 12px 16px;
		border-radius: 18px;
	}

	.message-row.user .message-bubble {
		background: linear-gradient(135deg, #007AFF 0%, #5856D6 100%);
		border-bottom-right-radius: 6px;
		color: white;
	}

	.message-row.assistant .message-bubble {
		background: rgba(0, 0, 0, 0.04);
		border-bottom-left-radius: 6px;
		color: #1d1d1f;
	}

	.message-content {
		font-size: 14px;
		line-height: 1.55;
	}

	/* === Sources === */
	.sources-card {
		margin-top: 14px;
		padding-top: 12px;
		border-top: 1px solid rgba(0, 0, 0, 0.06);
	}

	.sources-label {
		display: block;
		margin-bottom: 10px;
		font-size: 11px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: #86868b;
	}

	.sources-items {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.source-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 10px 12px;
		background: rgba(255, 255, 255, 0.8);
		border: 1px solid rgba(0, 0, 0, 0.06);
		border-radius: 10px;
		text-decoration: none;
		transition: all 0.15s ease;
	}

	.source-item:hover {
		background: white;
		border-color: rgba(0, 122, 255, 0.3);
		box-shadow: 0 2px 8px rgba(0, 122, 255, 0.1);
	}

	.source-name {
		font-size: 13px;
		font-weight: 500;
		color: #1d1d1f;
	}

	.source-match {
		font-size: 12px;
		color: #86868b;
	}

	/* === Typing === */
	.typing-dots {
		display: flex;
		gap: 5px;
		padding: 4px 0;
	}

	.typing-dots span {
		width: 7px;
		height: 7px;
		background: #86868b;
		border-radius: 50%;
		animation: pulse 1.4s infinite;
	}

	.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
	.typing-dots span:nth-child(3) { animation-delay: 0.4s; }

	@keyframes pulse {
		0%, 100% { opacity: 0.3; transform: scale(0.85); }
		50% { opacity: 1; transform: scale(1); }
	}

	/* === Error === */
	.error-strip {
		padding: 10px 20px;
		background: #FFF2F2;
		font-size: 13px;
		color: #FF3B30;
	}

	/* === Input === */
	.input-bar {
		padding: 12px 16px 16px;
		background: rgba(255, 255, 255, 0.6);
		border-top: 1px solid rgba(0, 0, 0, 0.06);
	}

	.input-field {
		display: flex;
		align-items: flex-end;
		gap: 10px;
		padding: 10px 12px;
		background: white;
		border: 1px solid rgba(0, 0, 0, 0.1);
		border-radius: 22px;
		box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
		transition: all 0.2s ease;
	}

	.input-field:focus-within {
		border-color: #007AFF;
		box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.12);
	}

	.input-field textarea {
		flex: 1;
		border: none;
		background: transparent;
		font-family: inherit;
		font-size: 14px;
		line-height: 1.4;
		resize: none;
		outline: none;
		color: #1d1d1f;
	}

	.input-field textarea::placeholder {
		color: #86868b;
	}

	.btn-send {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 34px;
		height: 34px;
		background: linear-gradient(135deg, #007AFF 0%, #5856D6 100%);
		border: none;
		border-radius: 50%;
		color: white;
		cursor: pointer;
		transition: all 0.2s ease;
		flex-shrink: 0;
	}

	.btn-send:hover:not(:disabled) {
		transform: scale(1.05);
		box-shadow: 0 4px 12px rgba(0, 122, 255, 0.3);
	}

	.btn-send:disabled {
		background: #e5e5ea;
		color: #aeaeb2;
		cursor: not-allowed;
	}
</style>
