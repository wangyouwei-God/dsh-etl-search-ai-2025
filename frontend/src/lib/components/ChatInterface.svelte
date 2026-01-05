<script lang="ts">
    import { sendChatMessage } from '$lib/api';
    import type { ChatMessage } from '$lib/types';
    import { Send, User, RotateCcw, ExternalLink } from 'lucide-svelte';

    let messages: ChatMessage[] = [];
    let inputMessage = '';
    let isLoading = false;
    let error = '';
    let conversationId: string | null = null;
    let textarea: HTMLTextAreaElement;
    let messagesContainer: HTMLElement;

    function generateId(): string {
        return Math.random().toString(36).substring(2, 15);
    }

    function scrollToBottom() {
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    async function handleSend() {
        if (!inputMessage.trim() || isLoading) return;

        const userMessage = inputMessage.trim();
        inputMessage = '';
        error = '';
        
        if (textarea) textarea.style.height = 'auto';

        const userMsg: ChatMessage = {
            id: generateId(),
            role: 'user',
            content: userMessage,
            timestamp: new Date()
        };
        messages = [...messages, userMsg];
        isLoading = true;
        
        setTimeout(scrollToBottom, 50);

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
            setTimeout(scrollToBottom, 50);
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
    
    function autoResize() {
        if (textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
        }
    }

    function clearConversation() {
        messages = [];
        conversationId = null;
        error = '';
    }

    function setQuery(text: string) {
        inputMessage = text;
        if (textarea) textarea.focus();
    }

    // Suggested queries
    const suggestions = [
        'What land cover datasets are available?',
        'Find hydrological monitoring data',
        'Datasets about butterfly populations',
        'Climate data for Scotland'
    ];
</script>

<div class="flex flex-col h-[600px] max-h-[80vh] bg-white rounded border border-border overflow-hidden">
    <!-- Header -->
    <header class="flex items-center justify-between px-5 py-4 border-b border-border bg-muted/30">
        <div>
            <h2 class="text-sm font-semibold text-foreground">AI Assistant</h2>
            <p class="text-xs text-muted-foreground">Semantic search with retrieval-augmented generation</p>
        </div>
        {#if messages.length > 0}
            <button 
                class="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors"
                on:click={clearConversation}
                title="New conversation"
            >
                <RotateCcw class="w-4 h-4" />
            </button>
        {/if}
    </header>

    <!-- Messages -->
    <main 
        bind:this={messagesContainer}
        class="flex-1 overflow-y-auto p-5 space-y-5 bg-white"
    >
        {#if messages.length === 0}
            <!-- Empty State -->
            <div class="h-full flex flex-col items-center justify-center text-center px-6">
                <h3 class="text-lg font-semibold text-foreground mb-2">
                    Dataset Discovery Assistant
                </h3>
                <p class="text-sm text-muted-foreground max-w-md mb-6">
                    Ask questions about environmental datasets in natural language. 
                    The assistant will search across 200+ datasets and provide relevant answers with source citations.
                </p>
                
                <div class="w-full max-w-md space-y-2">
                    <div class="section-header text-left mb-2">Suggested queries</div>
                    {#each suggestions as query}
                        <button 
                            class="w-full text-left px-4 py-3 text-sm bg-muted/30 border border-border rounded hover:border-primary/30 hover:bg-muted/50 transition-colors"
                            on:click={() => setQuery(query)}
                        >
                            {query}
                        </button>
                    {/each}
                </div>
            </div>
        {:else}
            <!-- Message List -->
            {#each messages as message}
                <div class={`flex gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}>
                    <!-- Avatar -->
                    <div class={`
                        w-7 h-7 rounded flex items-center justify-center shrink-0 text-xs font-medium
                        ${message.role === 'user' 
                            ? 'bg-primary text-primary-foreground' 
                            : 'bg-muted text-muted-foreground border border-border'}
                    `}>
                        {#if message.role === 'user'}
                            <User class="w-3.5 h-3.5" />
                        {:else}
                            A
                        {/if}
                    </div>

                    <!-- Content -->
                    <div class={`flex flex-col max-w-[85%] ${message.role === 'user' ? 'items-end' : 'items-start'}`}>
                        <div class={`
                            rounded px-4 py-3 text-sm leading-relaxed
                            ${message.role === 'user' 
                                ? 'bg-primary text-primary-foreground' 
                                : 'bg-muted/50 text-foreground border border-border'}
                        `}>
                            {@html message.content.replace(/\n/g, '<br>')}
                        </div>
                        
                        <!-- Sources -->
                        {#if message.sources && message.sources.length > 0}
                            <div class="mt-2 p-3 bg-muted/30 rounded border border-border w-full">
                                <div class="section-header mb-2">Referenced Datasets</div>
                                <ul class="space-y-1.5">
                                    {#each message.sources as source}
                                        <li>
                                            <a 
                                                href="/datasets/{source.id}" 
                                                class="flex items-center justify-between p-2 text-sm hover:bg-white rounded transition-colors group"
                                            >
                                                <span class="text-foreground group-hover:text-primary truncate mr-2">
                                                    {source.title}
                                                </span>
                                                <div class="flex items-center gap-2 shrink-0">
                                                    <span class="text-xs text-muted-foreground font-mono">
                                                        {Math.round(source.relevance_score * 100)}%
                                                    </span>
                                                    <ExternalLink class="w-3 h-3 text-muted-foreground" />
                                                </div>
                                            </a>
                                        </li>
                                    {/each}
                                </ul>
                            </div>
                        {/if}
                    </div>
                </div>
            {/each}

            {#if isLoading}
                <div class="flex gap-3">
                    <div class="w-7 h-7 rounded bg-muted border border-border flex items-center justify-center text-xs font-medium text-muted-foreground">
                        A
                    </div>
                    <div class="bg-muted/50 border border-border rounded px-4 py-3 flex items-center gap-1.5">
                        <span class="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-pulse"></span>
                        <span class="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-pulse delay-75"></span>
                        <span class="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-pulse delay-150"></span>
                    </div>
                </div>
            {/if}
        {/if}
    </main>

    <!-- Input -->
    <div class="p-4 border-t border-border bg-muted/20">
        {#if error}
            <div class="mb-3 px-3 py-2 bg-destructive/5 border border-destructive/20 rounded text-xs text-destructive flex items-center justify-between">
                <span>{error}</span>
                <button on:click={() => error = ''} class="font-bold hover:opacity-70">&times;</button>
            </div>
        {/if}
        
        <div class="flex items-end gap-2">
            <div class="flex-1 border border-border rounded bg-white focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/10 transition-all">
                <textarea
                    bind:this={textarea}
                    bind:value={inputMessage}
                    on:keydown={handleKeydown}
                    on:input={autoResize}
                    placeholder="Ask a question about datasets..."
                    disabled={isLoading}
                    rows="1"
                    class="w-full bg-transparent border-0 focus:ring-0 resize-none py-2.5 px-3 text-sm text-foreground placeholder:text-muted-foreground"
                ></textarea>
            </div>
            
            <button 
                class="p-2.5 rounded bg-primary text-primary-foreground disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90 transition-opacity"
                on:click={handleSend} 
                disabled={isLoading || !inputMessage.trim()}
                aria-label="Send message"
            >
                <Send class="w-4 h-4" />
            </button>
        </div>
        
        <p class="text-center text-xs text-muted-foreground mt-2">
            Responses are generated using RAG and may require verification.
        </p>
    </div>
</div>