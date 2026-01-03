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
	<div class="chat-header">
		<h2>Dataset Assistant</h2>
		<p>Ask questions about environmental datasets</p>
		{#if messages.length > 0}
			<button class="clear-btn" on:click={clearConversation}>Clear Chat</button>
		{/if}
	</div>

	<div class="messages-container">
		{#if messages.length === 0}
			<div class="welcome-message">
				<div class="welcome-icon">💬</div>
				<h3>Welcome to the Dataset Assistant</h3>
				<p>I can help you find and understand environmental datasets. Try asking:</p>
				<ul class="suggestions">
					<li>
						<button on:click={() => (inputMessage = 'What datasets do you have about land cover?')}
							>What datasets do you have about land cover?</button
						>
					</li>
					<li>
						<button
							on:click={() => (inputMessage = 'Tell me about climate change research data')}
							>Tell me about climate change research data</button
						>
					</li>
					<li>
						<button on:click={() => (inputMessage = 'What biodiversity datasets are available?')}
							>What biodiversity datasets are available?</button
						>
					</li>
				</ul>
			</div>
		{:else}
			{#each messages as message}
				<div class="message {message.role}">
					<div class="message-avatar">
						{message.role === 'user' ? '👤' : '🤖'}
					</div>
					<div class="message-content">
						<div class="message-text">{@html message.content.replace(/\n/g, '<br>')}</div>

						{#if message.sources && message.sources.length > 0}
							<div class="sources">
								<strong>Sources:</strong>
								<ul>
									{#each message.sources as source}
										<li>
											<a href="/datasets/{source.id}">{source.title}</a>
											<span class="relevance">({formatScore(source.relevance_score)})</span>
										</li>
									{/each}
								</ul>
							</div>
						{/if}
					</div>
				</div>
			{/each}

			{#if isLoading}
				<div class="message assistant">
					<div class="message-avatar">🤖</div>
					<div class="message-content">
						<div class="typing-indicator">
							<span></span>
							<span></span>
							<span></span>
						</div>
					</div>
				</div>
			{/if}
		{/if}
	</div>

	{#if error}
		<div class="error-message">{error}</div>
	{/if}

	<div class="input-container">
		<textarea
			bind:value={inputMessage}
			on:keydown={handleKeydown}
			placeholder="Ask about datasets..."
			disabled={isLoading}
			rows="1"
		></textarea>
		<button class="send-btn" on:click={handleSend} disabled={isLoading || !inputMessage.trim()}>
			{isLoading ? '...' : '➤'}
		</button>
	</div>
</div>

<style>
	.chat-container {
		display: flex;
		flex-direction: column;
		height: 600px;
		max-height: 80vh;
		background: #ffffff;
		border-radius: 12px;
		box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
		overflow: hidden;
	}

	.chat-header {
		padding: 16px 20px;
		background: linear-gradient(135deg, #2563eb, #1d4ed8);
		color: white;
		position: relative;
	}

	.chat-header h2 {
		margin: 0 0 4px 0;
		font-size: 1.25rem;
	}

	.chat-header p {
		margin: 0;
		opacity: 0.9;
		font-size: 0.875rem;
	}

	.clear-btn {
		position: absolute;
		top: 16px;
		right: 16px;
		background: rgba(255, 255, 255, 0.2);
		border: none;
		color: white;
		padding: 6px 12px;
		border-radius: 6px;
		cursor: pointer;
		font-size: 0.75rem;
	}

	.clear-btn:hover {
		background: rgba(255, 255, 255, 0.3);
	}

	.messages-container {
		flex: 1;
		overflow-y: auto;
		padding: 20px;
		background: #f8fafc;
	}

	.welcome-message {
		text-align: center;
		padding: 40px 20px;
	}

	.welcome-icon {
		font-size: 3rem;
		margin-bottom: 16px;
	}

	.welcome-message h3 {
		margin: 0 0 8px 0;
		color: #1e293b;
	}

	.welcome-message p {
		color: #64748b;
		margin-bottom: 20px;
	}

	.suggestions {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.suggestions li {
		margin-bottom: 8px;
	}

	.suggestions button {
		background: white;
		border: 1px solid #e2e8f0;
		padding: 10px 16px;
		border-radius: 8px;
		cursor: pointer;
		color: #2563eb;
		transition: all 0.2s;
		width: 100%;
		max-width: 350px;
	}

	.suggestions button:hover {
		background: #eff6ff;
		border-color: #2563eb;
	}

	.message {
		display: flex;
		gap: 12px;
		margin-bottom: 16px;
	}

	.message-avatar {
		width: 36px;
		height: 36px;
		border-radius: 50%;
		background: #e2e8f0;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 1.25rem;
		flex-shrink: 0;
	}

	.message.assistant .message-avatar {
		background: #dbeafe;
	}

	.message-content {
		flex: 1;
		background: white;
		padding: 12px 16px;
		border-radius: 12px;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
		max-width: 85%;
	}

	.message.user .message-content {
		background: #2563eb;
		color: white;
		margin-left: auto;
	}

	.message-text {
		line-height: 1.5;
	}

	.sources {
		margin-top: 12px;
		padding-top: 12px;
		border-top: 1px solid #e2e8f0;
		font-size: 0.875rem;
	}

	.sources ul {
		margin: 8px 0 0 0;
		padding-left: 20px;
	}

	.sources li {
		margin-bottom: 4px;
	}

	.sources a {
		color: #2563eb;
		text-decoration: none;
	}

	.sources a:hover {
		text-decoration: underline;
	}

	.relevance {
		color: #64748b;
		font-size: 0.75rem;
	}

	.typing-indicator {
		display: flex;
		gap: 4px;
		padding: 8px 0;
	}

	.typing-indicator span {
		width: 8px;
		height: 8px;
		background: #94a3b8;
		border-radius: 50%;
		animation: typing 1.4s infinite;
	}

	.typing-indicator span:nth-child(2) {
		animation-delay: 0.2s;
	}

	.typing-indicator span:nth-child(3) {
		animation-delay: 0.4s;
	}

	@keyframes typing {
		0%,
		100% {
			opacity: 0.3;
		}
		50% {
			opacity: 1;
		}
	}

	.error-message {
		padding: 12px 20px;
		background: #fef2f2;
		color: #dc2626;
		font-size: 0.875rem;
	}

	.input-container {
		display: flex;
		gap: 12px;
		padding: 16px 20px;
		background: white;
		border-top: 1px solid #e2e8f0;
	}

	.input-container textarea {
		flex: 1;
		padding: 12px 16px;
		border: 1px solid #e2e8f0;
		border-radius: 8px;
		resize: none;
		font-family: inherit;
		font-size: 0.95rem;
		line-height: 1.4;
	}

	.input-container textarea:focus {
		outline: none;
		border-color: #2563eb;
		box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
	}

	.send-btn {
		padding: 12px 20px;
		background: #2563eb;
		color: white;
		border: none;
		border-radius: 8px;
		font-size: 1.25rem;
		cursor: pointer;
		transition: background 0.2s;
	}

	.send-btn:hover:not(:disabled) {
		background: #1d4ed8;
	}

	.send-btn:disabled {
		background: #94a3b8;
		cursor: not-allowed;
	}
</style>
