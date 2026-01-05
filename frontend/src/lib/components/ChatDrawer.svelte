<script lang="ts">
    import { fly, fade } from 'svelte/transition';
    import { cubicOut } from 'svelte/easing';
    import { sendChatMessage } from '$lib/api';
    import type { ChatMessage } from '$lib/types';
    import { Send, User, X, MessageSquare, ExternalLink } from 'lucide-svelte';
    import { tick } from 'svelte';

    let isOpen = false;
    let messages: ChatMessage[] = [];
    let inputMessage = '';
    let isLoading = false;
    let conversationId: string | null = null;
    let chatContainer: HTMLElement;

    function generateId(): string {
        return Math.random().toString(36).substring(2, 15);
    }

    function toggleChat() {
        isOpen = !isOpen;
        if (isOpen) {
            scrollToBottom();
        }
    }

    async function scrollToBottom() {
        await tick();
        if (chatContainer) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    }

    async function handleSend() {
        if (!inputMessage.trim() || isLoading) return;

        const userMessage = inputMessage.trim();
        inputMessage = '';

        const userMsg: ChatMessage = {
            id: generateId(),
            role: 'user',
            content: userMessage,
            timestamp: new Date()
        };
        messages = [...messages, userMsg];
        scrollToBottom();
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
            console.error('API error:', err);
            // Show error in chat
            const errorMsg: ChatMessage = {
                id: generateId(),
                role: 'assistant',
                content: 'Unable to process request. Please check your connection and try again.',
                timestamp: new Date(),
                sources: []
            };
            messages = [...messages, errorMsg];
        } finally {
            isLoading = false;
            scrollToBottom();
        }
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            handleSend();
        }
    }

    function quickStart(query: string) {
        inputMessage = query;
        handleSend();
    }
</script>

<!-- Floating Toggle Button -->
<button
    on:click={toggleChat}
    class="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-2.5 bg-primary text-primary-foreground rounded shadow-lg hover:opacity-90 transition-all"
    aria-label="Toggle assistant"
>
    {#if isOpen}
        <X class="w-4 h-4" />
        <span class="text-sm font-medium">Close</span>
    {:else}
        <MessageSquare class="w-4 h-4" />
        <span class="text-sm font-medium">AI Assistant</span>
    {/if}
</button>

<!-- Drawer -->
{#if isOpen}
    <!-- Backdrop -->
    <button
        type="button"
        transition:fade={{ duration: 150 }}
        class="fixed inset-0 bg-foreground/10 backdrop-blur-sm z-40"
        on:click={toggleChat}
        aria-label="Close chat"
    ></button>

    <!-- Panel -->
    <div
        transition:fly={{ x: 400, duration: 250, easing: cubicOut }}
        class="fixed top-0 right-0 h-full w-full sm:w-[400px] bg-white shadow-xl z-50 border-l border-border flex flex-col"
    >
        <!-- Header -->
        <header class="flex items-center justify-between px-5 py-4 border-b border-border">
            <div>
                <h2 class="text-sm font-semibold text-foreground">AI Assistant</h2>
                <p class="text-xs text-muted-foreground">Retrieval-augmented generation</p>
            </div>
            <button 
                on:click={toggleChat} 
                class="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors"
            >
                <X class="w-4 h-4" />
            </button>
        </header>

        <!-- Messages -->
        <div 
            bind:this={chatContainer}
            class="flex-1 overflow-y-auto p-5 space-y-5 bg-muted/20"
        >
            {#if messages.length === 0}
                <!-- Empty State -->
                <div class="h-full flex flex-col items-center justify-center text-center px-4">
                    <div class="w-10 h-10 bg-white rounded border border-border flex items-center justify-center mb-4">
                        <MessageSquare class="w-5 h-5 text-muted-foreground" />
                    </div>
                    <h3 class="text-base font-semibold text-foreground mb-2">
                        How can I help?
                    </h3>
                    <p class="text-sm text-muted-foreground mb-6">
                        Ask about datasets, formats, or specific environmental measurements.
                    </p>
                    <div class="w-full space-y-2">
                        <button 
                            class="w-full text-left text-sm px-4 py-3 bg-white border border-border rounded hover:border-primary/30 transition-colors"
                            on:click={() => quickStart('Show me hydrology datasets')}
                        >
                            Show me hydrology datasets
                        </button>
                        <button 
                            class="w-full text-left text-sm px-4 py-3 bg-white border border-border rounded hover:border-primary/30 transition-colors"
                            on:click={() => quickStart('Land cover data for UK')}
                        >
                            Land cover data for UK
                        </button>
                    </div>
                </div>
            {:else}
                {#each messages as message}
                    <div class={`flex gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}>
                        <!-- Avatar -->
                        <div class={`
                            w-7 h-7 rounded flex items-center justify-center shrink-0 text-xs font-medium
                            ${message.role === 'user' 
                                ? 'bg-primary text-primary-foreground' 
                                : 'bg-white border border-border text-muted-foreground'}
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
                                rounded px-4 py-2.5 text-sm leading-relaxed
                                ${message.role === 'user' 
                                    ? 'bg-primary text-primary-foreground' 
                                    : 'bg-white border border-border text-foreground'}
                            `}>
                                {@html message.content.replace(/\n/g, '<br>')}
                            </div>
                            
                            <!-- Sources -->
                            {#if message.sources && message.sources.length > 0}
                                <div class="mt-2 p-3 bg-white border border-border rounded w-full">
                                    <div class="section-header mb-2">References</div>
                                    <ul class="space-y-1">
                                        {#each message.sources as source}
                                            <li>
                                                <a 
                                                    href="/datasets/{source.id}" 
                                                    class="flex items-center justify-between p-1.5 text-xs hover:bg-muted rounded transition-colors group"
                                                >
                                                    <span class="text-foreground group-hover:text-primary truncate mr-2">
                                                        {source.title}
                                                    </span>
                                                    <div class="flex items-center gap-1.5 shrink-0">
                                                        <span class="text-muted-foreground font-mono">
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
                        <div class="w-7 h-7 rounded bg-white border border-border flex items-center justify-center text-xs text-muted-foreground">
                            A
                        </div>
                        <div class="bg-white border border-border rounded px-4 py-3 flex items-center gap-1.5">
                            <span class="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-pulse"></span>
                            <span class="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-pulse delay-75"></span>
                            <span class="w-1.5 h-1.5 bg-muted-foreground rounded-full animate-pulse delay-150"></span>
                        </div>
                    </div>
                {/if}
            {/if}
        </div>

        <!-- Input -->
        <div class="p-4 border-t border-border bg-white">
            <div class="flex items-center gap-2">
                <div class="flex-1 border border-border rounded bg-white focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/10 transition-all">
                    <input
                        type="text"
                        bind:value={inputMessage}
                        on:keydown={handleKeydown}
                        placeholder="Ask a question..."
                        disabled={isLoading}
                        class="w-full bg-transparent border-0 focus:ring-0 py-2.5 px-3 text-sm text-foreground placeholder:text-muted-foreground"
                    />
                </div>
                
                <button 
                    class="p-2.5 rounded bg-primary text-primary-foreground disabled:opacity-50 hover:opacity-90 transition-opacity"
                    on:click={handleSend} 
                    disabled={isLoading || !inputMessage.trim()}
                    aria-label="Send"
                >
                    <Send class="w-4 h-4" />
                </button>
            </div>
        </div>
    </div>
{/if}
