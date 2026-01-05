<script lang="ts">
    import ChatInterface from '$lib/components/ChatInterface.svelte';
</script>

<svelte:head>
    <title>AI Assistant | Dataset Search and Discovery</title>
</svelte:head>

<div class="max-w-3xl mx-auto px-4 py-8">
    <div class="mb-6 text-center">
        <h1 class="text-xl font-semibold text-foreground mb-2">Research Assistant</h1>
        <p class="text-sm text-muted-foreground">
            Natural language queries powered by retrieval-augmented generation
        </p>
    </div>
    
    <ChatInterface />
</div>
