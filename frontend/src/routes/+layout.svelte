<script>
	import '../app.css';
	import { Database } from 'lucide-svelte';
</script>

<div class="min-h-screen bg-gradient-to-b from-background to-secondary/20">
	<header class="border-b border-border bg-white/50 backdrop-blur-sm sticky top-0 z-10">
		<div class="container mx-auto px-4 py-4">
			<div class="flex items-center gap-3">
				<Database class="w-8 h-8 text-primary" />
				<div>
					<h1 class="text-2xl font-bold text-foreground">Dataset Search & Discovery</h1>
					<p class="text-sm text-muted-foreground">University of Manchester</p>
				</div>
			</div>
		</div>
	</header>

	<main class="container mx-auto px-4 py-8">
		<slot />
	</main>

	<footer class="border-t border-border mt-16 py-6 bg-white/30">
		<div class="container mx-auto px-4 text-center text-sm text-muted-foreground">
			<p>Powered by semantic search with sentence-transformers and ChromaDB</p>
		</div>
	</footer>
</div>
