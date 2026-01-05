<script>
    import '../app.css';
    import Header from '$lib/components/Header.svelte';
    import ChatDrawer from '$lib/components/ChatDrawer.svelte';
</script>

<div class="min-h-screen bg-background text-foreground antialiased">
    <Header />
    
    <main>
        <slot />
    </main>
    
    <ChatDrawer />
</div>