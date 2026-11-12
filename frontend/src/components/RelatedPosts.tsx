/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from "@tanstack/react-query"
import { getRelatedPosts } from "@/services/blog-api"
import BlogCard from "@/components/BlogCard"

interface RelatedPostsProps {
  slug: string
}

export default function RelatedPosts({ slug }: RelatedPostsProps): React.ReactElement | null {
  const { data: posts } = useQuery({
    queryKey: ["blog", "related", slug],
    queryFn: () => getRelatedPosts(slug),
  })

  if (!posts || posts.length === 0) return null

  return (
    <section aria-labelledby="related-posts-heading" className="space-y-4">
      <h2 id="related-posts-heading" className="text-xl font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
        Related Posts
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {posts.map((post) => (
          <BlogCard key={post.id} post={post} />
        ))}
      </div>
    </section>
  )
}
