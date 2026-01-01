<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { getDataset, APIError } from '$lib/api';
	import type { Dataset } from '$lib/types';
	import { formatDate } from '$lib/utils';
	import { ArrowLeft, MapPin, Calendar, Mail, Tag, ExternalLink, Loader2 } from 'lucide-svelte';

	let dataset: Dataset | null = null;
	let isLoading = true;
	let error: string | null = null;

	onMount(async () => {
		const id = $page.params.id;
		try {
			dataset = await getDataset(id);
		} catch (e) {
			if (e instanceof APIError) {
				error = e.message;
			} else {
				error = 'Failed to load dataset';
			}
		} finally {
			isLoading = false;
		}
	});
</script>

<svelte:head>
	<title>{dataset?.title || 'Loading...'} | Dataset Search</title>
</svelte:head>

<div class="max-w-4xl mx-auto space-y-6">
	<!-- Back Button -->
	<a
		href="/"
		class="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
	>
		<ArrowLeft class="w-4 h-4" />
		Back to search
	</a>

	{#if isLoading}
		<div class="flex items-center justify-center py-16">
			<Loader2 class="w-8 h-8 animate-spin text-primary" />
		</div>
	{:else if error}
		<div class="bg-destructive/10 border border-destructive/30 rounded-lg p-6">
			<h2 class="text-xl font-semibold text-destructive mb-2">Error Loading Dataset</h2>
			<p class="text-destructive/90">{error}</p>
		</div>
	{:else if dataset}
		<!-- Dataset Header -->
		<div class="bg-white border border-border rounded-lg p-8 space-y-6">
			<div>
				<h1 class="text-3xl font-bold text-foreground mb-4">{dataset.title}</h1>
				<div class="flex flex-wrap gap-4 text-sm text-muted-foreground">
					<div class="flex items-center gap-1">
						<Calendar class="w-4 h-4" />
						Updated: {formatDate(dataset.last_updated)}
					</div>
					{#if dataset.metadata?.contact_email}
						<div class="flex items-center gap-1">
							<Mail class="w-4 h-4" />
							{dataset.metadata.contact_email}
						</div>
					{/if}
				</div>
			</div>

			<!-- Abstract -->
			<div>
				<h2 class="text-xl font-semibold text-foreground mb-3">Abstract</h2>
				<p class="text-muted-foreground leading-relaxed whitespace-pre-wrap">
					{dataset.abstract}
				</p>
			</div>

			<!-- Metadata -->
			{#if dataset.metadata}
				<!-- Keywords -->
				{#if dataset.metadata.keywords && dataset.metadata.keywords.length > 0}
					<div>
						<h2 class="text-xl font-semibold text-foreground mb-3">Keywords</h2>
						<div class="flex flex-wrap gap-2">
							{#each dataset.metadata.keywords as keyword}
								<span class="inline-flex items-center gap-1 px-3 py-1 bg-secondary text-secondary-foreground rounded-full text-sm">
									<Tag class="w-3 h-3" />
									{keyword}
								</span>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Geographic Extent -->
				{#if dataset.metadata.bounding_box}
					{@const bbox = dataset.metadata.bounding_box}
					<div>
						<h2 class="text-xl font-semibold text-foreground mb-3">Geographic Extent</h2>
						<div class="grid grid-cols-2 gap-4 bg-secondary/50 p-4 rounded-lg">
							<div>
								<div class="text-sm text-muted-foreground">West Longitude</div>
								<div class="font-medium">{bbox.west_longitude}°</div>
							</div>
							<div>
								<div class="text-sm text-muted-foreground">East Longitude</div>
								<div class="font-medium">{bbox.east_longitude}°</div>
							</div>
							<div>
								<div class="text-sm text-muted-foreground">South Latitude</div>
								<div class="font-medium">{bbox.south_latitude}°</div>
							</div>
							<div>
								<div class="text-sm text-muted-foreground">North Latitude</div>
								<div class="font-medium">{bbox.north_latitude}°</div>
							</div>
						</div>
					</div>
				{/if}

				<!-- Temporal Extent -->
				{#if dataset.metadata.temporal_extent_start && dataset.metadata.temporal_extent_end}
					<div>
						<h2 class="text-xl font-semibold text-foreground mb-3">Temporal Coverage</h2>
						<div class="flex items-center gap-4 bg-secondary/50 p-4 rounded-lg">
							<div class="flex-1">
								<div class="text-sm text-muted-foreground">Start Date</div>
								<div class="font-medium">{formatDate(dataset.metadata.temporal_extent_start)}</div>
							</div>
							<div class="text-muted-foreground">→</div>
							<div class="flex-1">
								<div class="text-sm text-muted-foreground">End Date</div>
								<div class="font-medium">{formatDate(dataset.metadata.temporal_extent_end)}</div>
							</div>
						</div>
					</div>
				{/if}

				<!-- Additional Information -->
				<div class="grid grid-cols-2 gap-4">
					{#if dataset.metadata.dataset_language}
						<div>
							<div class="text-sm text-muted-foreground">Language</div>
							<div class="font-medium">{dataset.metadata.dataset_language}</div>
						</div>
					{/if}
					{#if dataset.metadata.topic_category}
						<div>
							<div class="text-sm text-muted-foreground">Topic Category</div>
							<div class="font-medium">{dataset.metadata.topic_category}</div>
						</div>
					{/if}
				</div>
			{/if}

			<!-- Source Link -->
			{#if dataset.metadata_url}
				<div class="pt-4 border-t border-border">
					<a
						href={dataset.metadata_url}
						target="_blank"
						rel="noopener noreferrer"
						class="inline-flex items-center gap-2 text-primary hover:text-primary/80 transition-colors"
					>
						<ExternalLink class="w-4 h-4" />
						View original metadata
					</a>
				</div>
			{/if}
		</div>
	{/if}
</div>
