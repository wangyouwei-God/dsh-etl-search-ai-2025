<script lang="ts">
	import { Search } from 'lucide-svelte';
	import { createEventDispatcher } from 'svelte';

	export let value = '';
	export let placeholder = 'Search datasets...';
	export let isLoading = false;

	const dispatch = createEventDispatcher<{ search: string }>();

	function handleSubmit(e: Event) {
		e.preventDefault();
		if (value.trim()) {
			dispatch('search', value.trim());
		}
	}
</script>

<form on:submit={handleSubmit} class="w-full max-w-3xl mx-auto">
	<div class="relative">
		<div class="absolute inset-y-0 left-0 flex items-center pl-4 pointer-events-none">
			<Search class="w-5 h-5 text-muted-foreground" />
		</div>
		<input
			type="text"
			bind:value
			{placeholder}
			disabled={isLoading}
			class="w-full pl-12 pr-4 py-4 text-lg border-2 border-border rounded-lg
				focus:outline-none focus:ring-2 focus:ring-ring focus:border-primary
				disabled:opacity-50 disabled:cursor-not-allowed
				transition-all duration-200"
		/>
		{#if isLoading}
			<div class="absolute inset-y-0 right-0 flex items-center pr-4">
				<div class="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
			</div>
		{/if}
	</div>
</form>
