<script lang="ts">
	import type { Dataset } from '$lib/types';
	import { formatDate } from '$lib/utils';
	import { MapPin, Calendar, FileText } from 'lucide-svelte';
    import { createEventDispatcher } from 'svelte';

	export let dataset: Dataset;
	export let score: number | undefined = undefined;

    const dispatch = createEventDispatcher<{ open: Dataset }>();

	function getScoreColor(score: number) {
		if (score >= 0.8) return 'bg-green-500';
		if (score >= 0.6) return 'bg-blue-500';
		return 'bg-gray-400';
	}

    function handleOpen(e: Event) {
        e.preventDefault();
        dispatch('open', dataset);
    }
</script>

<article class="flex flex-col p-6 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow">
	<div class="flex justify-between items-start gap-4">
        <!-- Title -->
		<h3 class="text-lg font-semibold text-gray-900 leading-snug">
			<a href="/datasets/{dataset.id}" on:click={handleOpen} class="hover:text-blue-600 hover:underline">
				{dataset.title}
			</a>
		</h3>
        
        <!-- Semantic Score -->
		{#if score !== undefined}
            <div class="shrink-0 flex flex-col items-end gap-1" title={`Similarity: ${score.toFixed(2)}`}>
                <span class="text-xs font-medium text-gray-500">{Math.round(score * 100)}% Match</span>
                <div class="w-24 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div class={`h-full ${getScoreColor(score)}`} style="width: {score * 100}%"></div>
                </div>
            </div>
		{/if}
	</div>

	<!-- Abstract -->
	<p class="mt-3 text-sm text-gray-600 line-clamp-2 leading-relaxed">
		{dataset.abstract}
	</p>

    <!-- Metadata Footer -->
	<div class="mt-4 flex flex-wrap items-center gap-4 text-xs text-gray-500">
        <!-- Date -->
		<div class="flex items-center gap-1.5">
			<Calendar class="w-3.5 h-3.5" />
			<span>Updated {formatDate(dataset.last_updated)}</span>
		</div>

        <!-- Geospatial -->
		{#if dataset.metadata?.bounding_box}
			<div class="flex items-center gap-1.5">
				<MapPin class="w-3.5 h-3.5" />
				<span>Geospatial</span>
			</div>
		{/if}

        <!-- Type -->
        <div class="flex items-center gap-1.5">
            <FileText class="w-3.5 h-3.5" />
            <span>Dataset</span>
        </div>
	</div>
</article>