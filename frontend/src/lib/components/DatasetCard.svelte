<script lang="ts">
	import type { SearchResult } from '$lib/types';
	import { MapPin, Calendar, Tag, TrendingUp } from 'lucide-svelte';
	import { truncate, formatScore } from '$lib/utils';

	export let dataset: SearchResult;
</script>

<div class="bg-white border border-border rounded-lg p-6 hover:shadow-lg transition-shadow duration-200">
	<div class="flex justify-between items-start mb-3">
		<h3 class="text-xl font-semibold text-foreground pr-4">{dataset.title}</h3>
		<div class="flex items-center gap-1 bg-primary/10 text-primary px-3 py-1 rounded-full text-sm font-medium">
			<TrendingUp class="w-4 h-4" />
			{formatScore(dataset.score)}
		</div>
	</div>

	<p class="text-muted-foreground mb-4 leading-relaxed">
		{truncate(dataset.abstract, 250)}
	</p>

	<div class="flex flex-wrap gap-3 mb-4">
		{#if dataset.keywords && dataset.keywords.length > 0}
			<div class="flex items-center gap-1 text-sm text-muted-foreground">
				<Tag class="w-4 h-4" />
				<span>{dataset.keywords.join(', ')}</span>
			</div>
		{/if}

		{#if dataset.has_geo_extent && dataset.center_lat && dataset.center_lon}
			<div class="flex items-center gap-1 text-sm text-muted-foreground">
				<MapPin class="w-4 h-4" />
				<span>{dataset.center_lat.toFixed(2)}°N, {dataset.center_lon.toFixed(2)}°E</span>
			</div>
		{/if}

		{#if dataset.has_temporal_extent}
			<div class="flex items-center gap-1 text-sm text-muted-foreground">
				<Calendar class="w-4 h-4" />
				<span>Temporal data</span>
			</div>
		{/if}
	</div>

	<a
		href="/datasets/{dataset.id}"
		class="inline-flex items-center justify-center px-4 py-2 text-sm font-medium
			text-primary-foreground bg-primary rounded-md hover:bg-primary/90
			focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2
			transition-colors duration-200"
	>
		View Details
	</a>
</div>
