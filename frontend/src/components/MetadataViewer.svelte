<script lang="ts">
	import type { Metadata } from '$lib/types';
	import { formatDate } from '$lib/utils';
	import { Building2, Mail, Globe, Calendar, FileText, Hash } from 'lucide-svelte';
	
	export let metadata: Metadata;

    // Helper for grid items
    const InfoItem = {
        title: '',
        value: '',
        icon: null
    };
</script>

<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
    <!-- Section: Identification -->
    <div class="space-y-4">
        <h3 class="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
            <FileText class="w-4 h-4 text-primary" />
            Identification
        </h3>
        <div class="bg-slate-50 rounded-xl p-4 space-y-3 border border-slate-100">
            <div>
                <span class="text-xs font-medium text-slate-500 block mb-1">Topic Category</span>
                <span class="text-sm text-slate-800">{metadata.topic_category || 'N/A'}</span>
            </div>
            <div>
                <span class="text-xs font-medium text-slate-500 block mb-1">Language</span>
                <span class="text-sm text-slate-800">{metadata.dataset_language || 'English'}</span>
            </div>
            <div>
                <span class="text-xs font-medium text-slate-500 block mb-1">Metadata Date</span>
                <span class="text-sm text-slate-800">{metadata.metadata_date ? formatDate(metadata.metadata_date) : 'N/A'}</span>
            </div>
        </div>
    </div>

    <!-- Section: Contact -->
    <div class="space-y-4">
        <h3 class="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
            <Building2 class="w-4 h-4 text-primary" />
            Contact
        </h3>
        <div class="bg-slate-50 rounded-xl p-4 space-y-3 border border-slate-100">
            <div>
                <span class="text-xs font-medium text-slate-500 block mb-1">Organization</span>
                <span class="text-sm text-slate-800 font-medium">{metadata.contact_organization || 'N/A'}</span>
            </div>
            {#if metadata.contact_email}
                <div>
                    <span class="text-xs font-medium text-slate-500 block mb-1">Email</span>
                    <a href="mailto:{metadata.contact_email}" class="text-sm text-primary hover:underline flex items-center gap-1.5">
                        <Mail class="w-3 h-3" />
                        {metadata.contact_email}
                    </a>
                </div>
            {/if}
        </div>
    </div>

    <!-- Section: Temporal -->
    {#if metadata.temporal_extent_start || metadata.temporal_extent_end}
        <div class="space-y-4 md:col-span-2">
            <h3 class="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <Calendar class="w-4 h-4 text-primary" />
                Temporal Extent
            </h3>
            <div class="flex items-center gap-4 bg-slate-50 rounded-xl p-4 border border-slate-100">
                <div class="flex-1">
                    <span class="text-xs font-medium text-slate-500 block mb-1">Start Date</span>
                    <span class="text-sm font-mono text-slate-800 bg-white px-2 py-1 rounded border border-slate-200">
                        {metadata.temporal_extent_start ? formatDate(metadata.temporal_extent_start) : 'Start'}
                    </span>
                </div>
                <div class="text-slate-300">→</div>
                <div class="flex-1">
                    <span class="text-xs font-medium text-slate-500 block mb-1">End Date</span>
                    <span class="text-sm font-mono text-slate-800 bg-white px-2 py-1 rounded border border-slate-200">
                        {metadata.temporal_extent_end ? formatDate(metadata.temporal_extent_end) : 'Present'}
                    </span>
                </div>
            </div>
        </div>
    {/if}

    <!-- Section: Keywords -->
	{#if metadata.keywords && metadata.keywords.length > 0}
        <div class="space-y-4 md:col-span-2">
            <h3 class="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <Hash class="w-4 h-4 text-primary" />
                Keywords
            </h3>
            <div class="flex flex-wrap gap-2">
				{#each metadata.keywords as keyword}
					<span class="inline-flex items-center px-3 py-1.5 rounded-full bg-white border border-slate-200 text-slate-600 text-xs font-medium hover:border-primary/30 hover:text-primary transition-colors cursor-default shadow-sm">
						{keyword}
					</span>
				{/each}
			</div>
		</div>
	{/if}
</div>